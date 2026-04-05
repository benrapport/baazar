#!/usr/bin/env python3
"""Generate a mock simulation report with realistic data for visualization development.

No API calls, no exchange needed. Pure synthetic data.
Usage: python demo/mock_report.py [--output sim_results]
"""

import argparse
import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from demo.markets import MARKETS, TIER_INFO


# Agent archetypes with realistic performance profiles
MOCK_AGENTS = [
    {"id": "zen-space-editor", "aesthetic": "minimalist", "strategy": "budget",
     "base_score": 5.5, "speed": 0.85, "cost_per": 0.0103, "score_var": 1.5},
    {"id": "swiss-grid-stylist", "aesthetic": "minimalist", "strategy": "balanced",
     "base_score": 6.5, "speed": 0.70, "cost_per": 0.0213, "score_var": 1.2},
    {"id": "luxury-monolith", "aesthetic": "minimalist", "strategy": "premium",
     "base_score": 8.0, "speed": 0.45, "cost_per": 0.0813, "score_var": 1.0},
    {"id": "forensic-realism-lab", "aesthetic": "photorealistic", "strategy": "balanced",
     "base_score": 8.5, "speed": 0.55, "cost_per": 0.0213, "score_var": 0.8},
    {"id": "street-shooter-verite", "aesthetic": "documentary", "strategy": "balanced",
     "base_score": 7.0, "speed": 0.65, "cost_per": 0.0213, "score_var": 1.3},
    {"id": "cabinet-of-wonders", "aesthetic": "maximalist", "strategy": "premium",
     "base_score": 8.5, "speed": 0.40, "cost_per": 0.0813, "score_var": 0.9},
    {"id": "oil-atelier-master", "aesthetic": "painterly", "strategy": "premium",
     "base_score": 8.0, "speed": 0.35, "cost_per": 0.0813, "score_var": 1.1},
    {"id": "festival-collage-director", "aesthetic": "maximalist", "strategy": "balanced",
     "base_score": 7.5, "speed": 0.60, "cost_per": 0.0213, "score_var": 1.4},
    {"id": "sakuga-keyframe-director", "aesthetic": "anime", "strategy": "budget",
     "base_score": 6.0, "speed": 0.80, "cost_per": 0.0103, "score_var": 1.6},
    {"id": "lifestyle-catalog-eye", "aesthetic": "photorealistic", "strategy": "premium",
     "base_score": 8.8, "speed": 0.30, "cost_per": 0.0813, "score_var": 0.7},
]


def simulate_market(market: dict, agents: list[dict], rng: random.Random,
                    market_idx: int) -> dict:
    """Simulate one market round with scoring, revisions, winner selection."""
    max_price = market["max_price"]
    min_quality = market["min_quality"]
    tier = market["tier"]

    # Tier-based score bonus (creative/premium prompts reward better agents more)
    tier_bonus = {"penny": -1.0, "budget": -0.5, "stress": 0, "mid": 0.5,
                  "premium": 1.0, "creative": 0.5}
    bonus = tier_bonus.get(tier, 0)

    submissions = []
    for agent in agents:
        # Can this agent afford to participate?
        if agent["cost_per"] > max_price:
            continue

        # Generate score with variance + tier bonus for quality agents
        quality_bonus = bonus * (agent["base_score"] - 6) / 4  # better agents benefit more from hard prompts
        raw_score = agent["base_score"] + quality_bonus + rng.gauss(0, agent["score_var"])

        # Learning effect: slight improvement over time
        learning = min(0.5, market_idx * 0.015)
        raw_score += learning

        score = max(1, min(10, round(raw_score)))

        # Speed: lower = slower. Latency in ms
        base_latency = 15000 + (1 - agent["speed"]) * 25000
        latency = base_latency + rng.gauss(0, 3000)

        # Revision logic
        revisions = []
        current_score = score
        total_cost = agent["cost_per"]

        if current_score < min_quality and total_cost * 2 < max_price:
            # Attempt revision 1
            rev1_score = max(1, min(10, round(current_score + rng.gauss(1.0, 1.2))))
            total_cost += agent["cost_per"]
            latency += 18000 + rng.gauss(0, 2000)
            revisions.append({"revision": 1, "score": rev1_score,
                             "feedback": f"Improved from {current_score} but needs more detail"})
            current_score = rev1_score

            if current_score < min_quality and total_cost + agent["cost_per"] < max_price:
                # Attempt revision 2
                rev2_score = max(1, min(10, round(current_score + rng.gauss(0.8, 1.0))))
                total_cost += agent["cost_per"]
                latency += 18000 + rng.gauss(0, 2000)
                revisions.append({"revision": 2, "score": rev2_score,
                                 "feedback": f"Better detail, score improved to {rev2_score}"})
                current_score = rev2_score

        feedback_texts = [
            "Strong composition with good use of light and shadow",
            "Captures the mood well but could use more detail in foreground",
            "Excellent color palette and atmospheric depth",
            "Good attempt but missing key elements from the prompt",
            "Technically proficient, emotionally resonant",
            "Creative interpretation that exceeds the literal prompt",
            "Decent output but generic composition, needs more personality",
            "Outstanding detail work, particularly in textures",
            "The lighting is flat — needs more dramatic contrast",
            "Beautiful work that would stop someone scrolling",
        ]

        submissions.append({
            "agent_id": agent["id"],
            "score": current_score,
            "final_score": current_score,
            "initial_score": score,
            "latency_ms": max(5000, latency),
            "cost": total_cost,
            "revisions": revisions,
            "n_revisions": len(revisions),
            "feedback": rng.choice(feedback_texts),
            "qualified": current_score >= min_quality,
        })

    # Select winner: earliest qualifying submission
    qualified = [s for s in submissions if s["qualified"]]
    qualified.sort(key=lambda s: s["latency_ms"])

    result = {
        "market_id": market["id"],
        "tier": tier,
        "prompt": market["prompt"],
        "max_price": max_price,
        "min_quality": min_quality,
        "criteria": market["criteria"],
        "start_time": time.time() - (50 - market_idx) * 25,
        "submissions": submissions,
        "n_participants": len(submissions),
        "n_qualified": len(qualified),
    }

    if qualified:
        winner = qualified[0]
        result["status"] = "settled"
        result["winner"] = winner["agent_id"]
        result["score"] = winner["final_score"]
        result["price"] = max_price
        result["latency_ms"] = winner["latency_ms"]
        result["elapsed"] = winner["latency_ms"] / 1000
    else:
        result["status"] = "timeout"
        result["elapsed"] = 90.0

    return result


def build_report(markets: list[dict], results: list[dict],
                 agents: list[dict]) -> dict:
    """Assemble the full report from simulation results."""

    # Agent PnL
    agent_pnl = {}
    for agent in agents:
        agent_pnl[agent["id"]] = {
            "wins": 0, "losses": 0, "revenue": 0.0, "costs": 0.0,
            "scores": [], "initial_scores": [],
            "tiers_won": [], "tiers_lost": [],
            "aesthetic": agent["aesthetic"],
            "economic_strategy": agent["strategy"],
            "revisions_attempted": 0, "revisions_succeeded": 0,
        }

    for r in results:
        for sub in r.get("submissions", []):
            aid = sub["agent_id"]
            if aid not in agent_pnl:
                continue
            pnl = agent_pnl[aid]
            pnl["scores"].append(sub["final_score"])
            pnl["initial_scores"].append(sub["initial_score"])
            pnl["costs"] += sub["cost"]
            pnl["revisions_attempted"] += sub["n_revisions"]
            if sub["n_revisions"] > 0 and sub["qualified"] and sub["initial_score"] < r["min_quality"]:
                pnl["revisions_succeeded"] += 1

            if r.get("winner") == aid:
                pnl["wins"] += 1
                pnl["revenue"] += r["price"]
                if r["tier"] not in pnl["tiers_won"]:
                    pnl["tiers_won"].append(r["tier"])
            elif sub["qualified"]:
                pnl["losses"] += 1

    # Compute derived fields
    for aid, pnl in agent_pnl.items():
        pnl["pnl"] = pnl["revenue"] - pnl["costs"]
        pnl["avg_score"] = sum(pnl["scores"]) / len(pnl["scores"]) if pnl["scores"] else 0
        pnl["avg_initial_score"] = (sum(pnl["initial_scores"]) / len(pnl["initial_scores"])
                                    if pnl["initial_scores"] else 0)
        total_decided = pnl["wins"] + pnl["losses"]
        pnl["win_rate"] = pnl["wins"] / total_decided if total_decided > 0 else 0
        pnl["n_markets"] = len(pnl["scores"])

    # Tier summary
    tier_summary = {}
    for tier in ["penny", "budget", "stress", "mid", "premium", "creative"]:
        tier_results = [r for r in results if r["tier"] == tier]
        settled = [r for r in tier_results if r["status"] == "settled"]
        timeouts = [r for r in tier_results if r["status"] == "timeout"]
        all_scores = []
        for r in tier_results:
            for sub in r.get("submissions", []):
                all_scores.append(sub["final_score"])

        tier_summary[tier] = {
            "total": len(tier_results),
            "settled": len(settled),
            "timeouts": len(timeouts),
            "avg_score": sum(r["score"] for r in settled) / len(settled) if settled else 0,
            "avg_latency_s": sum(r["elapsed"] for r in settled) / len(settled) if settled else 0,
            "total_volume": sum(r["price"] for r in settled),
            "unique_winners": len(set(r["winner"] for r in settled)),
            "avg_participants": (sum(r["n_participants"] for r in tier_results) /
                                len(tier_results) if tier_results else 0),
            "avg_qualified": (sum(r["n_qualified"] for r in tier_results) /
                             len(tier_results) if tier_results else 0),
            "all_scores": all_scores,
            "quality_gap": 0,
        }
        # Quality gap: winner score - avg score
        if settled:
            for r in settled:
                winner_score = r["score"]
                all_sub_scores = [s["final_score"] for s in r.get("submissions", [])]
                avg_sub = sum(all_sub_scores) / len(all_sub_scores) if all_sub_scores else 0
                tier_summary[tier]["quality_gap"] += (winner_score - avg_sub)
            tier_summary[tier]["quality_gap"] /= len(settled)

    # Market details for the report
    market_details = {}
    for r in results:
        market_details[r["market_id"]] = {
            "input": r["prompt"],
            "scored": {s["agent_id"]: {"score": s["final_score"], "feedback": s["feedback"]}
                      for s in r.get("submissions", [])},
            "winner": r.get("winner"),
        }

    # Economics summary
    total_buyer_spend = sum(r["price"] for r in results if r["status"] == "settled")
    total_agent_costs = sum(pnl["costs"] for pnl in agent_pnl.values())
    total_agent_revenue = sum(pnl["revenue"] for pnl in agent_pnl.values())
    exchange_fees = total_buyer_spend * 0.015
    total_revisions = sum(pnl["revisions_attempted"] for pnl in agent_pnl.values())
    successful_revisions = sum(pnl["revisions_succeeded"] for pnl in agent_pnl.values())

    # Quality gap across all markets
    quality_gaps = []
    for r in results:
        if r["status"] == "settled" and r.get("submissions"):
            winner_score = r["score"]
            all_scores = [s["final_score"] for s in r["submissions"]]
            avg = sum(all_scores) / len(all_scores)
            quality_gaps.append(winner_score - avg)

    # Price-quality curve data
    price_quality = []
    for r in results:
        if r["status"] == "settled":
            price_quality.append({
                "price": r["max_price"], "score": r["score"],
                "tier": r["tier"], "market_id": r["market_id"],
            })

    # Cost absorption: total agent spend vs buyer payment
    cost_absorption = []
    for r in results:
        if r["status"] == "settled":
            agent_spend = sum(s["cost"] for s in r.get("submissions", []))
            cost_absorption.append({
                "market_id": r["market_id"], "tier": r["tier"],
                "buyer_paid": r["price"], "agents_spent": agent_spend,
                "ratio": agent_spend / r["price"] if r["price"] > 0 else 0,
            })

    return {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "n_markets": len(markets),
            "n_agents": len(agents),
            "total_buyer_budget": sum(m["max_price"] for m in markets),
            "timeout": 90.0,
            "is_mock": True,
        },
        "economics": {
            "total_buyer_spend": total_buyer_spend,
            "total_agent_costs": total_agent_costs,
            "total_agent_revenue": total_agent_revenue,
            "exchange_fees": exchange_fees,
            "total_revisions": total_revisions,
            "successful_revisions": successful_revisions,
            "avg_quality_gap": sum(quality_gaps) / len(quality_gaps) if quality_gaps else 0,
            "cost_absorption_ratio": (total_agent_costs / total_buyer_spend
                                      if total_buyer_spend > 0 else 0),
        },
        "markets": results,
        "market_details": market_details,
        "agent_pnl": agent_pnl,
        "tier_summary": tier_summary,
        "price_quality": price_quality,
        "cost_absorption": cost_absorption,
    }


def generate_html(report: dict, path: Path):
    """Generate widescreen dashboard HTML report."""

    mock_badge = ' <span class="mock">MOCK DATA</span>' if report['metadata'].get('is_mock') else ''
    report_json = json.dumps(report)

    # Use a plain template with simple replacements — no f-strings near JS
    html = _HTML_TEMPLATE.replace('__REPORT_JSON__', report_json)
    html = html.replace('__MOCK_BADGE__', mock_badge)
    html = html.replace('__TIMESTAMP__', report['metadata']['timestamp'])
    html = html.replace('__N_MARKETS__', str(report['metadata']['n_markets']))
    html = html.replace('__N_AGENTS__', str(report['metadata']['n_agents']))

    with open(path, "w") as f:
        f.write(html)


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Bazaar Exchange — Simulation Report</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'SF Mono','Fira Code',monospace;background:#0a0a0f;color:#e0e0e0;padding:12px 16px;font-size:13px}
h1{color:#ffd700;font-size:1.5em;display:inline}
.mock{background:#ff6f00;color:#fff;padding:2px 8px;border-radius:3px;font-size:.65em;vertical-align:middle}
.sub{color:#666;font-size:.8em;margin-left:12px}
.hdr{display:flex;align-items:baseline;gap:8px;margin-bottom:10px}
h2{color:#00bcd4;font-size:.95em;margin:0 0 6px;padding:4px 0;border-bottom:1px solid #222}
.note{color:#555;font-size:.72em;margin:-4px 0 4px}

/* Grid layouts */
.row{display:grid;gap:10px;margin-bottom:10px}
.r2{grid-template-columns:1fr 1fr}
.r3{grid-template-columns:1fr 1fr 1fr}
.r23{grid-template-columns:2fr 3fr}
.r32{grid-template-columns:3fr 2fr}
.box{background:#111118;border:1px solid #1e1e2e;border-radius:6px;padding:10px;overflow:hidden}

/* Stats strip */
.stats{display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap}
.st{background:#111118;border:1px solid #1e1e2e;border-radius:5px;padding:6px 12px;text-align:center;flex:1;min-width:90px}
.st .v{font-size:1.3em;font-weight:bold;color:#ffd700}
.st .l{font-size:.6em;color:#666;margin-top:1px}
.st .v.g{color:#4caf50}.st .v.r{color:#f44336}.st .v.b{color:#42a5f5}

/* Flow */
.flow{display:flex;align-items:center;justify-content:center;gap:6px;padding:8px}
.fb{background:#13131f;border:1px solid #282838;border-radius:6px;padding:8px 12px;text-align:center}
.fb .l{font-size:.6em;color:#666}.fb .v{font-size:1.1em;font-weight:bold;margin-top:2px}
.fa{color:#444;font-size:1.2em}

/* Bars */
.bar{display:flex;align-items:center;margin:2px 0}
.bl{width:140px;font-size:.7em;color:#888;text-align:right;padding-right:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0}
.bf{height:14px;border-radius:2px;min-width:1px}.bv{font-size:.65em;color:#666;padding-left:6px;white-space:nowrap}

/* Tables */
table{width:100%;border-collapse:collapse;font-size:.75em}
th{background:#12121e;color:#666;text-align:left;padding:4px 6px;font-weight:normal;text-transform:uppercase;font-size:.65em;letter-spacing:.5px}
td{padding:3px 6px;border-bottom:1px solid #151520}
tr:hover{background:#151520}
.p{color:#4caf50}.n{color:#f44336}

/* Chips */
.tc{padding:2px 7px;border-radius:10px;font-size:.65em;font-weight:bold;display:inline-block}
.tc-penny{background:#1a1a1a;color:#777;border:1px solid #333}
.tc-budget{background:#0a1f0a;color:#4caf50;border:1px solid #2e7d32}
.tc-stress{background:#1f140a;color:#ff9800;border:1px solid #e65100}
.tc-mid{background:#1f1f0a;color:#ffeb3b;border:1px solid #f9a825}
.tc-premium{background:#1f0a1f;color:#e040fb;border:1px solid #7b1fa2}
.tc-creative{background:#0a1f1f;color:#26c6da;border:1px solid #00838f}

.wb{background:#2e7d32;color:#fff;padding:1px 6px;border-radius:8px;font-size:.7em}
.rb{background:#1a237e;color:#90caf9;padding:1px 6px;border-radius:8px;font-size:.7em}
.sc{padding:1px 5px;border-radius:2px;font-size:.65em;display:inline-block;margin:1px}
.sh{background:#1b5e20;color:#a5d6a7}.sm{background:#3a2e00;color:#ffe082}.sl{background:#3a0000;color:#ef9a9a}

/* Scatter */
.scat{position:relative;height:200px}
.dot{position:absolute;width:8px;height:8px;border-radius:50%;cursor:pointer}
.dot:hover{transform:scale(2);z-index:10}
.ax{position:absolute;color:#444;font-size:.6em}

/* Market grid */
.mg{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:6px}
.mc{background:#111118;border:1px solid #1e1e2e;border-radius:5px;padding:8px;font-size:.78em}
.mc .pr{color:#aaa;font-style:italic;font-size:.85em;margin:3px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mc .sr{display:flex;gap:3px;flex-wrap:wrap;margin-top:4px}

/* Collapsible */
details>summary{cursor:pointer;color:#00bcd4;font-size:.9em;padding:4px 0}
details>summary:hover{color:#4dd0e1}
</style>
</head>
<body>
<div class="hdr"><h1>BAZAAR EXCHANGE__MOCK_BADGE__</h1><span class="sub">__TIMESTAMP__ — __N_MARKETS__ markets, __N_AGENTS__ agents</span></div>

<div class="stats" id="stats"></div>
<div class="box" style="margin-bottom:10px"><div class="flow" id="flow"></div></div>

<div class="row r3">
  <div class="box"><h2>QUALITY GAP</h2><div class="note">Winner vs avg score — exchange's value-add</div><div id="qgap" style="max-height:280px;overflow-y:auto"></div></div>
  <div class="box"><h2>PRICE-QUALITY FRONTIER</h2><div class="note">Each dot = settled market</div><div class="scat" id="scatter"></div></div>
  <div class="box"><h2>COST ABSORPTION</h2><div class="note">Agents spend Nx what buyer pays</div><div id="absorb" style="max-height:280px;overflow-y:auto"></div></div>
</div>

<div class="row r2">
  <div class="box">
    <h2>AGENT PnL LEADERBOARD</h2>
    <div id="pnl" style="margin-bottom:6px"></div>
    <div style="max-height:200px;overflow-y:auto"><table id="atbl"><thead><tr><th>#</th><th>Agent</th><th>Strat</th><th>W</th><th>L</th><th>W%</th><th>Avg</th><th>Rev</th><th>Costs</th><th>PnL</th></tr></thead><tbody></tbody></table></div>
  </div>
  <div>
    <div class="row r2" style="margin-bottom:10px">
      <div class="box"><h2>TIER BREAKDOWN</h2><div id="ttbl"></div></div>
      <div class="box"><h2>COMPETITIVE DEPTH</h2><div id="depth"></div></div>
    </div>
    <div class="box"><h2>REVISION ROI</h2><div class="note">Initial → revised score</div><div id="rev" style="max-height:180px;overflow-y:auto"></div></div>
  </div>
</div>

<div class="row r2">
  <div class="box"><h2>SCORE DISTRIBUTION BY TIER</h2><div id="sdist" style="display:flex;gap:12px;flex-wrap:wrap"></div></div>
  <div class="box">
    <details open><summary>MARKET-BY-MARKET RESULTS (__N_MARKETS__ markets)</summary>
    <div class="mg" id="mlist" style="margin-top:6px"></div>
    </details>
  </div>
</div>

<script>
const D=__REPORT_JSON__;
const E=D.economics,S=D.markets.filter(m=>m.status==='settled'),T=D.markets.filter(m=>m.status==='timeout');
const A=Object.entries(D.agent_pnl).map(([id,a])=>({id,...a})).sort((a,b)=>b.pnl-a.pnl);
const TO=['penny','budget','stress','mid','premium','creative'];
const TC={penny:'#888',budget:'#4caf50',stress:'#ff9800',mid:'#ffeb3b',premium:'#e040fb',creative:'#26c6da'};
const avg=S.length?(S.reduce((s,m)=>s+m.score,0)/S.length).toFixed(1):'—';

document.getElementById('stats').innerHTML=[
['Markets',D.metadata.n_markets,''],['Settled',S.length,'g'],['Timeouts',T.length,T.length?'r':''],
['Avg Score',avg+'/10',''],['Volume','$'+E.total_buyer_spend.toFixed(2),'g'],
['Agent Costs','$'+E.total_agent_costs.toFixed(2),'r'],['Fees','$'+E.exchange_fees.toFixed(2),'b'],
['Q.Gap','+'+E.avg_quality_gap.toFixed(1),'g'],['Revisions',E.total_revisions+'('+E.successful_revisions+'w)',''],
].map(([l,v,c])=>'<div class="st"><div class="v '+c+'">'+v+'</div><div class="l">'+l+'</div></div>').join('');

const ap=Math.max(0,E.total_agent_revenue-E.total_agent_costs),al=Math.max(0,E.total_agent_costs-E.total_agent_revenue);
document.getElementById('flow').innerHTML='<div class="fb"><div class="l">BUYER</div><div class="v" style="color:#ffd700">$'+E.total_buyer_spend.toFixed(2)+'</div></div><div class="fa">→</div><div class="fb"><div class="l">FEE 1.5%</div><div class="v" style="color:#42a5f5">$'+E.exchange_fees.toFixed(2)+'</div></div><div class="fa">→</div><div class="fb"><div class="l">WINNERS</div><div class="v" style="color:#4caf50">$'+E.total_agent_revenue.toFixed(2)+'</div></div><div class="fa">→</div><div class="fb"><div class="l">API COSTS</div><div class="v" style="color:#f44336">$'+E.total_agent_costs.toFixed(2)+'</div></div><div class="fa">→</div><div class="fb"><div class="l">NET '+(ap>0?'PROFIT':'LOSS')+'</div><div class="v" style="color:'+(ap>0?'#4caf50':'#f44336')+'">$'+Math.abs(ap||al).toFixed(2)+'</div></div>';

const qg=S.map(function(m){var sc=m.submissions.map(function(s){return s.final_score}),av=sc.reduce(function(a,b){return a+b},0)/sc.length;return{id:m.market_id,t:m.tier,w:m.score,a:av,g:m.score-av}}).sort(function(a,b){return b.g-a.g});
var mgx=Math.max.apply(null,qg.map(function(d){return Math.abs(d.g)}).concat([1]));
document.getElementById('qgap').innerHTML=qg.map(function(d){var w=Math.abs(d.g)/mgx*100,c=d.g>0?'#4caf50':'#f44336';return'<div class="bar"><div class="bl"><span class="tc tc-'+d.t+'">'+d.t+'</span> '+d.id+'</div><div class="bf" style="width:'+w+'%;background:'+c+'"></div><div class="bv"><b style="color:'+c+'">'+(d.g>0?'+':'')+d.g.toFixed(1)+'</b> (w'+d.w+' avg'+d.a.toFixed(1)+')</div></div>'}).join('');

var pcc=document.getElementById('scatter'),mpp=Math.max.apply(null,D.price_quality.map(function(d){return d.price}));
D.price_quality.forEach(function(d){var x=(d.price/mpp)*90+5,y=95-(d.score/10)*85,e=document.createElement('div');e.className='dot';e.style.cssText='left:'+x+'%;top:'+y+'%;background:'+(TC[d.tier]||'#888');e.title=d.market_id+': $'+d.price+' → '+d.score+'/10';pcc.appendChild(e)});

var ca=D.cost_absorption.sort(function(a,b){return b.ratio-a.ratio}),mrr=Math.max.apply(null,ca.map(function(d){return d.ratio}).concat([1]));
document.getElementById('absorb').innerHTML=ca.map(function(d){var w=d.ratio/mrr*100;return'<div class="bar"><div class="bl"><span class="tc tc-'+d.tier+'">'+d.tier+'</span> '+d.market_id+'</div><div class="bf" style="width:'+w+'%;background:#f44336"></div><div class="bv">'+d.ratio.toFixed(1)+'x</div></div>'}).join('');

var mpl=Math.max.apply(null,A.map(function(a){return Math.abs(a.pnl)}).concat([.01]));
document.getElementById('pnl').innerHTML=A.map(function(a){var w=Math.abs(a.pnl)/mpl*100,c=a.pnl>=0?'#4caf50':'#f44336';return'<div class="bar"><div class="bl">'+a.id+'</div><div class="bf" style="width:'+w+'%;background:'+c+'"></div><div class="bv">'+(a.pnl>=0?'+':'')+'$'+a.pnl.toFixed(3)+'</div></div>'}).join('');

document.querySelector('#atbl tbody').innerHTML=A.map(function(a,i){var c=a.pnl>=0?'p':'n';return'<tr><td>'+(i+1)+'</td><td><b>'+a.id+'</b></td><td>'+a.economic_strategy+'</td><td>'+a.wins+'</td><td>'+a.losses+'</td><td>'+(a.win_rate*100).toFixed(0)+'%</td><td>'+a.avg_score.toFixed(1)+'</td><td>'+a.revisions_attempted+'</td><td>$'+a.costs.toFixed(3)+'</td><td class="'+c+'"><b>'+(a.pnl>=0?'+':'')+'$'+a.pnl.toFixed(3)+'</b></td></tr>'}).join('');

document.getElementById('ttbl').innerHTML='<table><thead><tr><th>Tier</th><th>N</th><th>OK</th><th>Fail</th><th>Avg</th><th>Gap</th><th>Vol</th></tr></thead><tbody>'+TO.filter(function(t){return D.tier_summary[t]&&D.tier_summary[t].total>0}).map(function(t){var s=D.tier_summary[t];return'<tr><td><span class="tc tc-'+t+'">'+t+'</span></td><td>'+s.total+'</td><td>'+s.settled+'</td><td class="'+(s.timeouts?'n':'')+'">'+s.timeouts+'</td><td>'+(s.avg_score?s.avg_score.toFixed(1):'—')+'</td><td class="p">+'+s.quality_gap.toFixed(1)+'</td><td>$'+s.total_volume.toFixed(2)+'</td></tr>'}).join('')+'</tbody></table>';

document.getElementById('depth').innerHTML=TO.filter(function(t){return D.tier_summary[t]&&D.tier_summary[t].total>0}).map(function(t){var s=D.tier_summary[t];return'<div style="margin:4px 0"><span style="font-size:.7em;color:'+TC[t]+'">'+t.toUpperCase()+'</span><div class="bar"><div class="bl" style="width:50px">In</div><div class="bf" style="width:'+(s.avg_participants/10*100)+'%;background:#42a5f5;opacity:.5"></div><div class="bv">'+s.avg_participants.toFixed(1)+'</div></div><div class="bar"><div class="bl" style="width:50px">OK</div><div class="bf" style="width:'+(s.avg_qualified/10*100)+'%;background:#4caf50"></div><div class="bv">'+s.avg_qualified.toFixed(1)+'</div></div></div>'}).join('');

var rv=[];D.markets.forEach(function(m){m.submissions.forEach(function(s){if(s.n_revisions>0)rv.push({a:s.agent_id,m:m.market_id,t:m.tier,i:s.initial_score,f:s.final_score,n:s.n_revisions,q:s.qualified})})});
document.getElementById('rev').innerHTML=rv.length?rv.map(function(d){var c=d.q?'#4caf50':(d.f>d.i?'#ffeb3b':'#f44336');return'<div class="bar"><div class="bl">'+d.a.substring(0,18)+' '+d.m+'</div><div style="display:flex;gap:6px;align-items:center"><span style="color:#888">'+d.i+'</span><span style="color:#444">→'+d.n+'r→</span><span style="color:'+c+';font-weight:bold">'+d.f+'</span>'+(d.q?' <span class="rb">OK</span>':'')+'</div></div>'}).join(''):'<div style="color:#444">None</div>';

var sd={};D.markets.forEach(function(m){m.submissions.forEach(function(s){if(!sd[m.tier])sd[m.tier]=[];sd[m.tier].push(s.final_score)})});
document.getElementById('sdist').innerHTML=TO.filter(function(t){return sd[t]}).map(function(t){var sc=sd[t],bk=Array(10).fill(0);sc.forEach(function(s){bk[Math.min(s,10)-1]++});var mx=Math.max.apply(null,bk.concat([1]));return'<div style="flex:1;min-width:100px"><div style="font-size:.7em;color:'+TC[t]+'">'+t+' n='+sc.length+' avg='+(sc.reduce(function(a,b){return a+b},0)/sc.length).toFixed(1)+'</div><div style="display:flex;align-items:flex-end;height:50px;gap:1px">'+bk.map(function(c,i){var h=c/mx*50,cl=i>=7?'#4caf50':(i>=5?'#ffeb3b':'#f44336');return'<div style="flex:1;background:'+cl+';height:'+h+'px;border-radius:1px 1px 0 0" title="'+(i+1)+': '+c+'"></div>'}).join('')+'</div><div style="display:flex;font-size:.5em;color:#444">'+bk.map(function(_,i){return'<div style="flex:1;text-align:center">'+(i+1)+'</div>'}).join('')+'</div></div>'}).join('');

document.getElementById('mlist').innerHTML=D.markets.map(function(m){
var st='';
if(m.status==='settled'){var rs=m.submissions.filter(function(s){return s.n_revisions>0}),rn=rs.length?' <span class="rb">'+rs.reduce(function(s,r){return s+r.n_revisions},0)+'rev</span>':'';st='<span class="wb">★'+m.winner+'</span> '+m.score+'/10 '+m.elapsed.toFixed(0)+'s'+rn}else st='<span style="color:#f44336">TIMEOUT</span>';
var sc=(m.submissions||[]).sort(function(a,b){return b.final_score-a.final_score}).slice(0,6).map(function(s){var c=s.final_score>=8?'sh':(s.final_score>=6?'sm':'sl');return'<span class="sc '+c+'">'+s.agent_id.substring(0,12)+' '+s.final_score+(s.n_revisions?' r'+s.n_revisions:'')+'</span>'}).join('');
return'<div class="mc"><div style="display:flex;justify-content:space-between"><span><span class="tc tc-'+m.tier+'">'+m.tier+'</span> <b>'+m.market_id+'</b></span><span style="color:#555">$'+m.max_price.toFixed(3)+' q≥'+m.min_quality+'</span></div><div class="pr">'+m.prompt+'</div><div style="margin-top:3px">'+st+'</div><div class="sr">'+sc+'</div></div>'}).join('');
</script>
</body></html>"""



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="sim_results")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--markets", type=int, default=None)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    markets = list(MARKETS)
    if args.markets:
        markets = markets[:args.markets]
    rng.shuffle(markets)

    print(f"Generating mock simulation: {len(markets)} markets, {len(MOCK_AGENTS)} agents...")

    results = []
    for i, market in enumerate(markets):
        result = simulate_market(market, MOCK_AGENTS, rng, i)
        results.append(result)

    report = build_report(markets, results, MOCK_AGENTS)

    out_dir = Path(args.output)
    out_dir.mkdir(exist_ok=True)

    json_path = out_dir / "simulation.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)

    html_path = out_dir / "report.html"
    generate_html(report, html_path)

    settled = [r for r in results if r["status"] == "settled"]
    rev_count = sum(s["n_revisions"] for r in results for s in r.get("submissions", []))
    print(f"  Settled: {len(settled)}/{len(markets)}")
    print(f"  Revisions: {rev_count}")
    print(f"  Saved: {json_path}")
    print(f"  Report: {html_path}")


if __name__ == "__main__":
    main()
