#!/usr/bin/env python3
"""Live simulation monitor — web UI on http://localhost:8888

Reads sim_results/ in real-time and serves a dashboard that auto-refreshes.

Usage:
    python3 sim/monitor.py
    python3 sim/monitor.py --port 9999
    python3 sim/monitor.py --dir sim_results
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

app = FastAPI(title="Bazaar Simulation Monitor")

# Configured at startup
SIM_DIR = Path("sim_results")


def _latest_file(pattern: str) -> Path | None:
    files = sorted(SIM_DIR.glob(pattern), key=lambda f: f.stat().st_mtime)
    return files[-1] if files else None


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except Exception:
        pass
    return rows


@app.get("/api/status")
async def api_status():
    results_file = _latest_file("results_*.jsonl")
    markets_file = _latest_file("markets_*.jsonl")

    if not results_file:
        return {"status": "waiting", "message": "No results file yet"}

    results = _read_jsonl(results_file)
    markets = _read_jsonl(markets_file) if markets_file else []

    total = len(results)
    wins = sum(1 for r in results if r.get("winner_agent") and not r.get("error"))
    timeouts = sum(1 for r in results if r.get("error") and ("Timeout" in r["error"] or "504" in r["error"]))
    errors = sum(1 for r in results if r.get("error") and "Timeout" not in r["error"] and "504" not in r["error"])

    # Agent leaderboard
    agent_wins = Counter()
    agent_revenue = Counter()
    agent_scores = {}
    for r in results:
        if r.get("winner_agent"):
            aid = r["winner_agent"]
            agent_wins[aid] += 1
            if r.get("fill_price") is not None:
                agent_revenue[aid] += r["fill_price"]
            if r.get("score") is not None:
                agent_scores.setdefault(aid, []).append(r["score"])

    leaderboard = []
    for aid, w in agent_wins.most_common(50):
        scores = agent_scores.get(aid, [])
        leaderboard.append({
            "agent": aid,
            "wins": w,
            "total_revenue": round(agent_revenue.get(aid, 0), 4),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        })

    # Category breakdown
    cat_stats = {}
    for r in results:
        cat = r.get("category", "unknown")
        if cat not in cat_stats:
            cat_stats[cat] = {"total": 0, "wins": 0, "timeouts": 0, "errors": 0}
        cat_stats[cat]["total"] += 1
        if r.get("winner_agent") and not r.get("error"):
            cat_stats[cat]["wins"] += 1
        elif r.get("error") and ("Timeout" in r["error"] or "504" in r["error"]):
            cat_stats[cat]["timeouts"] += 1
        elif r.get("error"):
            cat_stats[cat]["errors"] += 1

    # Difficulty breakdown
    diff_stats = {}
    for r in results:
        diff = r.get("difficulty", "unknown")
        if diff not in diff_stats:
            diff_stats[diff] = {"total": 0, "wins": 0, "timeouts": 0, "errors": 0}
        diff_stats[diff]["total"] += 1
        if r.get("winner_agent") and not r.get("error"):
            diff_stats[diff]["wins"] += 1
        elif r.get("error") and ("Timeout" in r["error"] or "504" in r["error"]):
            diff_stats[diff]["timeouts"] += 1
        elif r.get("error"):
            diff_stats[diff]["errors"] += 1

    # Error breakdown
    error_types = Counter()
    for r in results:
        if r.get("error"):
            err = r["error"][:80]
            error_types[err] += 1

    # Recent results (last 20)
    recent = []
    for r in results[-20:]:
        recent.append({
            "task_id": r.get("task_id", "?"),
            "category": r.get("category", "?"),
            "difficulty": r.get("difficulty", "?"),
            "winner": r.get("winner_agent", "—"),
            "price": r.get("fill_price"),
            "score": r.get("score"),
            "error": r.get("error", "")[:60] if r.get("error") else None,
        })
    recent.reverse()

    return {
        "status": "running",
        "results_file": str(results_file),
        "markets_file": str(markets_file) if markets_file else None,
        "total": total,
        "wins": wins,
        "timeouts": timeouts,
        "errors": errors,
        "win_rate": round(100 * wins / total, 1) if total else 0,
        "markets_logged": len(markets),
        "leaderboard": leaderboard,
        "categories": dict(sorted(cat_stats.items())),
        "difficulties": diff_stats,
        "error_types": dict(error_types.most_common(10)),
        "recent": recent,
        "updated_at": time.time(),
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Bazaar Simulation Monitor</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', Menlo, monospace;
         background: #0f0f23; color: #ccc; padding: 20px; }
  h1 { color: #fff; margin-bottom: 8px; font-size: 22px; }
  .subtitle { color: #666; font-size: 13px; margin-bottom: 20px; }
  .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
  .card { background: #1a1a2e; border-radius: 8px; padding: 16px; border: 1px solid #333; }
  .card .label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
  .card .value { font-size: 28px; font-weight: bold; color: #fff; margin-top: 4px; }
  .card .value.green { color: #2ecc71; }
  .card .value.red { color: #e74c3c; }
  .card .value.yellow { color: #f1c40f; }
  .card .value.blue { color: #3498db; }

  .section { margin-bottom: 20px; }
  .section h2 { font-size: 15px; color: #fff; margin-bottom: 8px; border-bottom: 1px solid #333; padding-bottom: 4px; }

  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { text-align: left; color: #888; font-weight: normal; text-transform: uppercase; letter-spacing: 1px;
       padding: 6px 8px; border-bottom: 1px solid #333; font-size: 10px; }
  td { padding: 5px 8px; border-bottom: 1px solid #1a1a2e; }
  tr:hover { background: #1a1a2e; }

  .bar { height: 16px; border-radius: 3px; display: inline-block; min-width: 2px; }
  .bar-wins { background: #2ecc71; }
  .bar-timeouts { background: #f1c40f; }
  .bar-errors { background: #e74c3c; }

  .progress-bar { width: 100%; height: 24px; background: #1a1a2e; border-radius: 6px; overflow: hidden;
                  margin-bottom: 16px; display: flex; }
  .progress-bar .seg { height: 100%; transition: width 0.5s; }
  .progress-bar .seg.wins { background: #2ecc71; }
  .progress-bar .seg.timeouts { background: #f1c40f; }
  .progress-bar .seg.errors { background: #e74c3c; }
  .progress-bar .seg.remaining { background: #333; }

  .badge { display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; }
  .badge.easy { background: #2ecc71; color: #000; }
  .badge.medium { background: #3498db; color: #fff; }
  .badge.hard { background: #e67e22; color: #fff; }
  .badge.extreme { background: #e74c3c; color: #fff; }

  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .three-col { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 12px; }

  .error-text { color: #e74c3c; font-size: 11px; }
  .winner-text { color: #2ecc71; }
  .mono { font-family: 'SF Mono', Menlo, monospace; }
  .pulse { animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
  .refreshing { color: #555; font-size: 11px; }
</style>
</head>
<body>
<h1>Bazaar Exchange — Simulation Monitor</h1>
<div class="subtitle" id="status-line">Connecting...</div>

<div id="progress-container"></div>

<div class="grid" id="cards"></div>

<div class="three-col">
  <div class="section card" id="leaderboard-section">
    <h2>Agent Leaderboard</h2>
    <table id="leaderboard"><thead><tr><th>Agent</th><th>Wins</th><th>Revenue</th><th>Avg Score</th></tr></thead><tbody></tbody></table>
  </div>
  <div class="section card" id="category-section">
    <h2>By Category</h2>
    <table id="categories"><thead><tr><th>Category</th><th>OK</th><th>Fail</th><th>Rate</th></tr></thead><tbody></tbody></table>
  </div>
  <div class="section card" id="errors-section">
    <h2>Top Errors</h2>
    <table id="errors"><thead><tr><th>Error</th><th>Count</th></tr></thead><tbody></tbody></table>
  </div>
</div>

<div class="section card" style="margin-top: 12px;">
  <h2>Recent Tasks</h2>
  <table id="recent"><thead><tr><th>Task</th><th>Category</th><th>Diff</th><th>Winner</th><th>Bid</th><th>Score</th><th>Error</th></tr></thead><tbody></tbody></table>
</div>

<script>
const TARGET = 4000;

async function refresh() {
  try {
    const res = await fetch('/api/status');
    const d = await res.json();
    if (d.status === 'waiting') {
      document.getElementById('status-line').textContent = 'Waiting for results...';
      return;
    }

    const pct = (100 * d.total / TARGET).toFixed(1);
    const elapsed = '';
    document.getElementById('status-line').innerHTML =
      `<span class="pulse">●</span> ${d.total} / ${TARGET} tasks (${pct}%) &nbsp;|&nbsp; ` +
      `File: ${d.results_file} &nbsp;|&nbsp; Markets logged: ${d.markets_logged}`;

    // Progress bar
    const wp = (100 * d.wins / TARGET).toFixed(2);
    const tp = (100 * d.timeouts / TARGET).toFixed(2);
    const ep = (100 * d.errors / TARGET).toFixed(2);
    const rp = Math.max(0, 100 - parseFloat(wp) - parseFloat(tp) - parseFloat(ep)).toFixed(2);
    document.getElementById('progress-container').innerHTML =
      `<div class="progress-bar">` +
      `<div class="seg wins" style="width:${wp}%" title="${d.wins} wins"></div>` +
      `<div class="seg timeouts" style="width:${tp}%" title="${d.timeouts} timeouts"></div>` +
      `<div class="seg errors" style="width:${ep}%" title="${d.errors} errors"></div>` +
      `<div class="seg remaining" style="width:${rp}%"></div>` +
      `</div>`;

    // Cards
    document.getElementById('cards').innerHTML =
      card('Completed', d.total, '') +
      card('Wins', d.wins, 'green') +
      card('Timeouts', d.timeouts, 'yellow') +
      card('Errors', d.errors, 'red');

    // Leaderboard
    const lb = document.querySelector('#leaderboard tbody');
    lb.innerHTML = d.leaderboard.map(a =>
      `<tr><td class="mono">${a.agent}</td><td>${a.wins}</td><td>$${a.total_revenue.toFixed(4)}</td><td>${a.avg_score}/10</td></tr>`
    ).join('');

    // Categories
    const ct = document.querySelector('#categories tbody');
    ct.innerHTML = Object.entries(d.categories).map(([cat, s]) => {
      const rate = s.total > 0 ? (100 * s.wins / s.total).toFixed(0) : 0;
      return `<tr><td>${cat}</td><td class="winner-text">${s.wins}</td><td class="error-text">${s.timeouts + s.errors}</td><td>${rate}%</td></tr>`;
    }).join('');

    // Errors
    const et = document.querySelector('#errors tbody');
    et.innerHTML = Object.entries(d.error_types).map(([err, count]) =>
      `<tr><td class="error-text" style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${err}</td><td>${count}</td></tr>`
    ).join('');

    // Recent
    const rc = document.querySelector('#recent tbody');
    rc.innerHTML = d.recent.map(r =>
      `<tr>` +
      `<td class="mono" style="font-size:11px">${r.task_id}</td>` +
      `<td>${r.category}</td>` +
      `<td><span class="badge ${r.difficulty}">${r.difficulty}</span></td>` +
      `<td class="${r.winner !== '—' ? 'winner-text' : ''}">${r.winner}</td>` +
      `<td>${r.price != null ? '$' + r.price.toFixed(4) : '—'}</td>` +
      `<td>${r.score != null ? r.score + '/10' : '—'}</td>` +
      `<td class="error-text" style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.error || ''}</td>` +
      `</tr>`
    ).join('');

  } catch(e) {
    document.getElementById('status-line').textContent = 'Error fetching status: ' + e.message;
  }
}

function card(label, value, cls) {
  return `<div class="card"><div class="label">${label}</div><div class="value ${cls}">${value}</div></div>`;
}

refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>"""


def main():
    global SIM_DIR

    # Add project root to path
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))

    parser = argparse.ArgumentParser(description="Live simulation monitor")
    parser.add_argument("--port", type=int, default=8888)
    parser.add_argument("--dir", default="sim_results")
    args = parser.parse_args()

    SIM_DIR = Path(args.dir)
    print(f"Monitoring: {SIM_DIR.resolve()}")
    print(f"Dashboard: http://localhost:{args.port}")

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
