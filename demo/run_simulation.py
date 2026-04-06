#!/usr/bin/env python3
"""Run a full exchange simulation and produce a JSON report.

Starts exchange + fleet, runs all markets, captures every event,
then generates an HTML visualization.

Usage:
    python demo/run_simulation.py                    # all 50 markets, 10 agents
    python demo/run_simulation.py --markets 10       # first 10 markets
    python demo/run_simulation.py --agents 50        # full 50-agent fleet
    python demo/run_simulation.py --shuffle          # randomize market order
"""

import argparse
import json
import os
import random
import signal
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

import httpx
from bazaar.client import Exchange
from agents.image_tool import get_best_option, estimate_thinking_cost
from demo.markets import MARKETS, TIER_INFO, RESET

PROCS: list[subprocess.Popen] = []


def cleanup():
    for p in PROCS:
        try:
            p.terminate()
            p.wait(timeout=3)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def start_exchange():
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "demo" / "run_exchange.py")],
        cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    PROCS.append(proc)
    for _ in range(30):
        try:
            if httpx.get("http://localhost:8000/status", timeout=2.0).status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Exchange did not start")


def start_fleet(n_agents: int):
    args = [sys.executable, str(ROOT / "demo" / "run_image_fleet.py")]
    if n_agents:
        args += ["--agents", str(n_agents)]
    proc = subprocess.Popen(args, cwd=str(ROOT),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    PROCS.append(proc)
    time.sleep(5)
    status = httpx.get("http://localhost:8000/status", timeout=5.0).json()
    return status.get("agents_registered", 0)


def load_strategies() -> dict:
    path = ROOT / "agents" / "strategies.json"
    if path.exists():
        with open(path) as f:
            return {s["id"]: s for s in json.load(f)}
    return {}


def estimate_agent_cost(agent_id: str, strategies: dict, max_price: float) -> float:
    s = strategies.get(agent_id, {})
    pref = s.get("economic_strategy", "balanced")
    option = get_best_option(max_price, prefer=pref)
    if not option:
        return 0.0
    return option["cost"] + estimate_thinking_cost(has_memory=True)


def run_market(ex: Exchange, market: dict, timeout: float) -> dict:
    """Run a single market and return the full result record."""
    record = {
        "market_id": market["id"],
        "tier": market["tier"],
        "prompt": market["prompt"],
        "max_price": market["max_price"],
        "min_quality": market["min_quality"],
        "criteria": market["criteria"],
        "start_time": time.time(),
    }

    try:
        result = ex.call(
            llm={"input": market["prompt"]},
            exchange={
                "max_price": market["max_price"],
                "timeout": timeout,
                "judge": {
                    "min_quality": market["min_quality"],
                    "criteria": market["criteria"],
                },
            },
        )
        record["elapsed"] = time.time() - record["start_time"]
        record["winner"] = result.agent_id
        record["score"] = result.score
        record["price"] = result.price
        record["latency_ms"] = result.latency_ms
        record["status"] = "settled"
    except TimeoutError:
        record["elapsed"] = time.time() - record["start_time"]
        record["status"] = "timeout"
    except Exception as e:
        record["elapsed"] = time.time() - record["start_time"]
        record["status"] = "error"
        record["error"] = str(e)

    return record


def fetch_market_details(request_ids: list[str]) -> dict:
    """Fetch full market logs from the exchange for all scored agents."""
    details = {}
    markets = httpx.get("http://localhost:8000/markets", timeout=10.0).json()
    for m in markets:
        rid = m["request_id"]
        try:
            mlog = httpx.get(f"http://localhost:8000/markets/{rid}", timeout=10.0).json()
            scored = {}
            for ev in mlog.get("events", []):
                if ev["type"] == "judge_completed":
                    d = ev.get("data", {})
                    scored[d.get("agent_id", "")] = {
                        "score": d.get("score", 0),
                        "feedback": d.get("feedback", ""),
                    }
            details[rid] = {
                "input": mlog.get("input", ""),
                "agents_invited": mlog.get("agents_invited", []),
                "winner": mlog.get("winner"),
                "scored": scored,
            }
        except Exception:
            pass
    return details


def main():
    parser = argparse.ArgumentParser(description="Run exchange simulation")
    parser.add_argument("--markets", type=int, default=None,
                        help="Number of markets to run (default: all)")
    parser.add_argument("--agents", type=int, default=10,
                        help="Number of agents in fleet (default: 10)")
    parser.add_argument("--timeout", type=float, default=90.0,
                        help="Timeout per market (default: 90s)")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="Seconds between markets (default: 2)")
    parser.add_argument("--shuffle", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default="sim_results",
                        help="Output directory (default: sim_results)")
    args = parser.parse_args()

    markets = list(MARKETS)
    if args.markets:
        markets = markets[:args.markets]
    if args.shuffle:
        random.seed(args.seed)
        random.shuffle(markets)

    strategies = load_strategies()

    print(f"{'=' * 70}")
    print(f"  BAZAAR EXCHANGE SIMULATION")
    print(f"{'=' * 70}")
    print(f"  Markets: {len(markets)} | Agents: {args.agents} | Timeout: {args.timeout}s")
    tier_counts = Counter(m["tier"] for m in markets)
    total_budget = sum(m["max_price"] for m in markets)
    print(f"  Tiers: {', '.join(f'{k}={v}' for k,v in sorted(tier_counts.items()))}")
    print(f"  Total buyer budget: ${total_budget:.2f}")
    print()

    # Start infrastructure
    print("[1/3] Starting exchange...")
    start_exchange()
    print("  Exchange ready")

    print(f"[2/3] Starting {args.agents}-agent fleet...")
    n = start_fleet(args.agents)
    print(f"  {n} agents registered")

    # Run markets
    print(f"[3/3] Running {len(markets)} markets...\n")
    ex = Exchange(api_key="demo")
    results = []

    for i, market in enumerate(markets, 1):
        tier = market["tier"]
        info = TIER_INFO.get(tier, {})
        color = info.get("color", "")
        label = info.get("label", tier.upper())
        prompt_short = market["prompt"][:45]

        print(f"  [{i:>2}/{len(markets)}] {color}{label:>8}{RESET} "
              f"${market['max_price']:.3f} q≥{market['min_quality']} │ {prompt_short}...")

        record = run_market(ex, market, args.timeout)
        results.append(record)

        if record["status"] == "settled":
            print(f"           → {record['winner'][:25]} "
                  f"│ {record['score']}/10 │ {record['elapsed']:.0f}s")
        elif record["status"] == "timeout":
            print(f"           → TIMEOUT — no agent met q≥{market['min_quality']}")
        else:
            print(f"           → ERROR: {record.get('error', '?')[:50]}")

        if i < len(markets):
            time.sleep(args.interval)

    # Fetch detailed market logs
    print("\nFetching market details...")
    market_details = fetch_market_details([])

    # Build agent PnL
    agent_pnl = defaultdict(lambda: {
        "wins": 0, "losses": 0, "timeouts": 0,
        "revenue": 0.0, "costs": 0.0, "scores": [],
        "tiers_won": set(), "tiers_lost": set(),
        "aesthetic": "", "economic_strategy": "",
    })

    for s_id, s in strategies.items():
        agent_pnl[s_id]["aesthetic"] = s.get("aesthetic", "")
        agent_pnl[s_id]["economic_strategy"] = s.get("economic_strategy", "")

    # Process results
    for r in results:
        if r["status"] != "settled":
            continue
        winner = r["winner"]
        price = r["price"]
        agent_pnl[winner]["wins"] += 1
        agent_pnl[winner]["revenue"] += price
        agent_pnl[winner]["tiers_won"].add(r["tier"])

    # Process detailed scores (all agents that were scored, not just winners)
    for rid, detail in market_details.items():
        for aid, score_data in detail.get("scored", {}).items():
            if aid in agent_pnl:
                agent_pnl[aid]["scores"].append(score_data["score"])
                cost = estimate_agent_cost(aid, strategies, 0.10)
                agent_pnl[aid]["costs"] += cost
                if aid != detail.get("winner"):
                    agent_pnl[aid]["losses"] += 1

    # Serialize
    report = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "n_markets": len(markets),
            "n_agents": args.agents,
            "total_buyer_budget": total_budget,
            "timeout": args.timeout,
        },
        "markets": results,
        "market_details": {
            rid: {**d, "scored": d["scored"]}
            for rid, d in market_details.items()
        },
        "agent_pnl": {
            aid: {
                **{k: v for k, v in pnl.items() if k not in ("tiers_won", "tiers_lost")},
                "tiers_won": list(pnl["tiers_won"]),
                "tiers_lost": list(pnl["tiers_lost"]),
                "pnl": pnl["revenue"] - pnl["costs"],
                "avg_score": (sum(pnl["scores"]) / len(pnl["scores"])
                             if pnl["scores"] else 0),
                "win_rate": (pnl["wins"] / (pnl["wins"] + pnl["losses"])
                            if (pnl["wins"] + pnl["losses"]) > 0 else 0),
            }
            for aid, pnl in agent_pnl.items()
            if pnl["scores"]  # only agents that were scored
        },
        "tier_summary": {},
    }

    # Tier summary
    for tier in ["penny", "budget", "stress", "mid", "premium", "creative"]:
        tier_results = [r for r in results if r["tier"] == tier]
        settled = [r for r in tier_results if r["status"] == "settled"]
        timeouts = [r for r in tier_results if r["status"] == "timeout"]
        report["tier_summary"][tier] = {
            "total": len(tier_results),
            "settled": len(settled),
            "timeouts": len(timeouts),
            "avg_score": (sum(r["score"] for r in settled) / len(settled)
                         if settled else 0),
            "avg_latency_s": (sum(r["elapsed"] for r in settled) / len(settled)
                             if settled else 0),
            "total_volume": sum(r["price"] for r in settled),
            "unique_winners": len(set(r["winner"] for r in settled)),
        }

    # Save
    out_dir = Path(args.output)
    out_dir.mkdir(exist_ok=True)
    json_path = out_dir / "simulation.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nResults saved to {json_path}")

    # Generate HTML report
    html_path = out_dir / "report.html"
    generate_html_report(report, html_path)
    print(f"HTML report: {html_path}")

    # Print summary
    settled = [r for r in results if r["status"] == "settled"]
    timeouts = [r for r in results if r["status"] == "timeout"]
    print(f"\n{'=' * 70}")
    print(f"  SIMULATION COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Settled: {len(settled)}/{len(results)} │ Timeouts: {len(timeouts)}")
    if settled:
        print(f"  Avg score: {sum(r['score'] for r in settled)/len(settled):.1f}/10")
        print(f"  Total volume: ${sum(r['price'] for r in settled):.2f}")
        wins = Counter(r["winner"] for r in settled)
        print(f"  Unique winners: {len(wins)}")
        print(f"\n  Top 5 agents:")
        for agent, count in wins.most_common(5):
            avgs = [r["score"] for r in settled if r["winner"] == agent]
            print(f"    {agent:<28} {count} wins, avg {sum(avgs)/len(avgs):.1f}/10")
    print(f"{'=' * 70}")
    print(f"\n  Open {html_path} in a browser to explore the results.")

    cleanup()


def generate_html_report(report: dict, path: Path):
    """Generate HTML dashboard — delegates to the improved mock_report template."""
    from demo.mock_report import generate_html
    generate_html(report, path)


def _generate_html_report_old(report: dict, path: Path):
    """Old report generator — kept for reference only."""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bazaar Exchange — Simulation Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
       background: #0a0a0f; color: #e0e0e0; padding: 20px; }}
h1 {{ color: #ffd700; font-size: 1.8em; margin-bottom: 5px; }}
h2 {{ color: #00bcd4; font-size: 1.3em; margin: 30px 0 15px; border-bottom: 1px solid #333; padding-bottom: 5px; }}
h3 {{ color: #aaa; font-size: 1em; margin: 20px 0 10px; }}
.subtitle {{ color: #888; font-size: 0.9em; margin-bottom: 20px; }}

.stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
               gap: 12px; margin: 20px 0; }}
.stat-card {{ background: #141420; border: 1px solid #2a2a3a; border-radius: 8px;
              padding: 15px; text-align: center; }}
.stat-value {{ font-size: 1.8em; font-weight: bold; color: #ffd700; }}
.stat-label {{ font-size: 0.75em; color: #888; margin-top: 4px; }}

.tier-bar {{ display: flex; gap: 8px; margin: 15px 0; flex-wrap: wrap; }}
.tier-chip {{ padding: 6px 14px; border-radius: 20px; font-size: 0.8em; font-weight: bold; }}
.tier-penny {{ background: #1a1a1a; color: #888; border: 1px solid #444; }}
.tier-budget {{ background: #0a2a0a; color: #4caf50; border: 1px solid #2e7d32; }}
.tier-stress {{ background: #2a1a0a; color: #ff9800; border: 1px solid #e65100; }}
.tier-mid {{ background: #2a2a0a; color: #ffeb3b; border: 1px solid #f9a825; }}
.tier-premium {{ background: #2a0a2a; color: #e040fb; border: 1px solid #7b1fa2; }}
.tier-creative {{ background: #0a2a2a; color: #26c6da; border: 1px solid #00838f; }}

table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.85em; }}
th {{ background: #1a1a2e; color: #888; text-align: left; padding: 8px 10px;
     font-weight: normal; text-transform: uppercase; font-size: 0.75em; letter-spacing: 1px; }}
td {{ padding: 7px 10px; border-bottom: 1px solid #1a1a2a; }}
tr:hover {{ background: #1a1a25; }}
.positive {{ color: #4caf50; }}
.negative {{ color: #f44336; }}
.neutral {{ color: #888; }}
.winner-badge {{ background: #2e7d32; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; }}
.timeout-badge {{ background: #8b0000; color: #fcc; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; }}

.market-card {{ background: #141420; border: 1px solid #2a2a3a; border-radius: 8px;
                padding: 15px; margin: 10px 0; }}
.market-card .prompt {{ color: #ccc; font-style: italic; margin: 8px 0; }}
.market-card .meta {{ display: flex; gap: 20px; font-size: 0.85em; color: #888; }}
.market-card .meta span {{ white-space: nowrap; }}
.scores-row {{ display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }}
.score-chip {{ padding: 3px 8px; border-radius: 4px; font-size: 0.75em; }}
.score-high {{ background: #1b5e20; color: #a5d6a7; }}
.score-mid {{ background: #4a3800; color: #ffe082; }}
.score-low {{ background: #4a0000; color: #ef9a9a; }}

.chart-container {{ background: #141420; border: 1px solid #2a2a3a; border-radius: 8px;
                    padding: 20px; margin: 15px 0; }}
.bar {{ display: flex; align-items: center; margin: 4px 0; }}
.bar-label {{ width: 200px; font-size: 0.8em; color: #aaa; text-align: right; padding-right: 10px;
              overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.bar-fill {{ height: 20px; border-radius: 3px; min-width: 2px; transition: width 0.3s; }}
.bar-value {{ font-size: 0.75em; color: #888; padding-left: 8px; white-space: nowrap; }}
</style>
</head>
<body>

<h1>BAZAAR EXCHANGE</h1>
<div class="subtitle">Simulation Report — {report['metadata']['timestamp']} — {report['metadata']['n_markets']} markets, {report['metadata']['n_agents']} agents</div>

<div class="stats-grid" id="stats-grid"></div>

<h2>TIER BREAKDOWN</h2>
<div class="tier-bar" id="tier-bar"></div>
<table id="tier-table"><thead><tr>
<th>Tier</th><th>Markets</th><th>Settled</th><th>Timeouts</th><th>Avg Score</th><th>Avg Latency</th><th>Volume</th><th>Winners</th>
</tr></thead><tbody></tbody></table>

<h2>AGENT PnL LEADERBOARD</h2>
<div class="chart-container" id="pnl-chart"></div>
<table id="agent-table"><thead><tr>
<th>#</th><th>Agent</th><th>Strategy</th><th>Aesthetic</th><th>W</th><th>L</th><th>Avg Score</th><th>Win Rate</th><th>Revenue</th><th>Costs</th><th>PnL</th>
</tr></thead><tbody></tbody></table>

<h2>MARKET-BY-MARKET RESULTS</h2>
<div id="markets-list"></div>

<h2>SCORE DISTRIBUTION BY TIER</h2>
<div class="chart-container" id="score-dist"></div>

<script>
const data = {json.dumps(report)};

// Stats grid
const meta = data.metadata;
const settled = data.markets.filter(m => m.status === 'settled');
const avgScore = settled.length ? (settled.reduce((s,m) => s + m.score, 0) / settled.length).toFixed(1) : '—';
const avgLatency = settled.length ? (settled.reduce((s,m) => s + m.elapsed, 0) / settled.length).toFixed(0) : '—';
const totalVol = settled.reduce((s,m) => s + m.price, 0);
const uniqueWinners = new Set(settled.map(m => m.winner)).size;
const timeouts = data.markets.filter(m => m.status === 'timeout').length;

const statsHtml = [
    ['Markets', meta.n_markets], ['Settled', settled.length], ['Timeouts', timeouts],
    ['Agents', meta.n_agents], ['Avg Score', avgScore + '/10'], ['Avg Latency', avgLatency + 's'],
    ['Volume', '$' + totalVol.toFixed(2)], ['Unique Winners', uniqueWinners],
    ['Buyer Budget', '$' + meta.total_buyer_budget.toFixed(2)],
].map(([l,v]) => `<div class="stat-card"><div class="stat-value">${{v}}</div><div class="stat-label">${{l}}</div></div>`).join('');
document.getElementById('stats-grid').innerHTML = statsHtml;

// Tier bar + table
const tierOrder = ['penny','budget','stress','mid','premium','creative'];
const tierBar = tierOrder.filter(t => data.tier_summary[t])
    .map(t => `<span class="tier-chip tier-${{t}}">${{t.toUpperCase()}} (${{data.tier_summary[t].total}})</span>`).join('');
document.getElementById('tier-bar').innerHTML = tierBar;

const tierRows = tierOrder.filter(t => data.tier_summary[t]).map(t => {{
    const s = data.tier_summary[t];
    return `<tr>
        <td><span class="tier-chip tier-${{t}}">${{t.toUpperCase()}}</span></td>
        <td>${{s.total}}</td><td>${{s.settled}}</td>
        <td class="${{s.timeouts ? 'negative' : ''}}">${{s.timeouts}}</td>
        <td>${{s.avg_score ? s.avg_score.toFixed(1) : '—'}}</td>
        <td>${{s.avg_latency_s ? s.avg_latency_s.toFixed(0) + 's' : '—'}}</td>
        <td>${{s.total_volume ? '$' + s.total_volume.toFixed(2) : '—'}}</td>
        <td>${{s.unique_winners}}</td></tr>`;
}}).join('');
document.querySelector('#tier-table tbody').innerHTML = tierRows;

// Agent PnL
const agents = Object.entries(data.agent_pnl)
    .map(([id, a]) => ({{ id, ...a }}))
    .sort((a, b) => b.pnl - a.pnl);

// PnL bar chart
const maxPnl = Math.max(...agents.map(a => Math.abs(a.pnl)), 0.01);
const pnlBars = agents.slice(0, 20).map(a => {{
    const w = Math.abs(a.pnl) / maxPnl * 100;
    const color = a.pnl >= 0 ? '#4caf50' : '#f44336';
    return `<div class="bar">
        <div class="bar-label">${{a.id}}</div>
        <div class="bar-fill" style="width:${{w}}%;background:${{color}}"></div>
        <div class="bar-value">${{a.pnl >= 0 ? '+' : ''}}$${{a.pnl.toFixed(4)}}</div>
    </div>`;
}}).join('');
document.getElementById('pnl-chart').innerHTML = pnlBars || '<div style="color:#666">No agent data</div>';

// Agent table
const agentRows = agents.map((a, i) => {{
    const pnlClass = a.pnl >= 0 ? 'positive' : 'negative';
    const pnlStr = (a.pnl >= 0 ? '+' : '') + '$' + a.pnl.toFixed(4);
    return `<tr>
        <td>${{i+1}}</td><td style="font-weight:bold">${{a.id}}</td>
        <td>${{a.economic_strategy}}</td><td>${{a.aesthetic}}</td>
        <td>${{a.wins}}</td><td>${{a.losses}}</td>
        <td>${{a.avg_score.toFixed(1)}}</td>
        <td>${{(a.win_rate * 100).toFixed(0)}}%</td>
        <td>$${{a.revenue.toFixed(4)}}</td>
        <td>$${{a.costs.toFixed(4)}}</td>
        <td class="${{pnlClass}}" style="font-weight:bold">${{pnlStr}}</td></tr>`;
}}).join('');
document.querySelector('#agent-table tbody').innerHTML = agentRows;

// Market cards
const marketCards = data.markets.map((m, i) => {{
    const tier = m.tier;
    let statusHtml = '';
    if (m.status === 'settled') {{
        statusHtml = `<span class="winner-badge">★ ${{m.winner}}</span> ${{m.score}}/10 in ${{m.elapsed.toFixed(0)}}s`;
    }} else if (m.status === 'timeout') {{
        statusHtml = `<span class="timeout-badge">TIMEOUT</span> No agent met q≥${{m.min_quality}}`;
    }} else {{
        statusHtml = `<span class="timeout-badge">ERROR</span> ${{m.error || '?'}}`;
    }}

    // Score chips from market details
    let scoresHtml = '';
    const details = Object.values(data.market_details).find(d => d.input && m.prompt.startsWith(d.input.substring(0, 30)));
    if (details && details.scored) {{
        const sorted = Object.entries(details.scored).sort((a,b) => b[1].score - a[1].score);
        scoresHtml = '<div class="scores-row">' + sorted.slice(0, 8).map(([aid, s]) => {{
            const cls = s.score >= 8 ? 'score-high' : (s.score >= 6 ? 'score-mid' : 'score-low');
            return `<span class="score-chip ${{cls}}" title="${{s.feedback}}">${{aid.substring(0,15)}} ${{s.score}}</span>`;
        }}).join('') + '</div>';
    }}

    return `<div class="market-card">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <span><span class="tier-chip tier-${{tier}}">${{tier.toUpperCase()}}</span>
            <strong style="margin-left:8px">${{m.market_id}}</strong></span>
            <span style="color:#888">$${{m.max_price.toFixed(3)}} │ q≥${{m.min_quality}}</span>
        </div>
        <div class="prompt">"${{m.prompt}}"</div>
        <div class="meta"><span>${{statusHtml}}</span></div>
        ${{scoresHtml}}
    </div>`;
}}).join('');
document.getElementById('markets-list').innerHTML = marketCards;

// Score distribution by tier
const scoreDist = {{}};
for (const [rid, detail] of Object.entries(data.market_details)) {{
    for (const [aid, s] of Object.entries(detail.scored)) {{
        const market = data.markets.find(m => detail.input && m.prompt.startsWith(detail.input.substring(0, 30)));
        const tier = market ? market.tier : 'unknown';
        if (!scoreDist[tier]) scoreDist[tier] = [];
        scoreDist[tier].push(s.score);
    }}
}}
const distHtml = tierOrder.filter(t => scoreDist[t]).map(t => {{
    const scores = scoreDist[t];
    const buckets = Array(10).fill(0);
    scores.forEach(s => buckets[Math.min(s, 10) - 1]++);
    const maxB = Math.max(...buckets, 1);
    const bars = buckets.map((c, i) => {{
        const h = (c / maxB * 60);
        const color = i >= 7 ? '#4caf50' : (i >= 5 ? '#ffeb3b' : '#f44336');
        return `<div style="display:inline-block;width:9%;text-align:center">
            <div style="height:60px;display:flex;align-items:flex-end;justify-content:center">
                <div style="width:70%;height:${{h}}px;background:${{color}};border-radius:2px 2px 0 0"></div>
            </div>
            <div style="font-size:0.7em;color:#666">${{i+1}}</div>
            <div style="font-size:0.65em;color:#444">${{c}}</div>
        </div>`;
    }}).join('');
    return `<h3><span class="tier-chip tier-${{t}}">${{t.toUpperCase()}}</span> (n=${{scores.length}}, avg=${{(scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1)}})</h3><div>${{bars}}</div>`;
}}).join('');
document.getElementById('score-dist').innerHTML = distHtml || '<div style="color:#666">No score data</div>';
</script>
</body>
</html>"""

    with open(path, "w") as f:
        f.write(html)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: (cleanup(), sys.exit(1)))
    signal.signal(signal.SIGTERM, lambda *_: (cleanup(), sys.exit(1)))
    try:
        main()
    except Exception as e:
        print(f"\nFATAL: {e}")
        cleanup()
        sys.exit(1)
