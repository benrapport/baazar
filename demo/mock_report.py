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
    """Generate enhanced HTML report with economic visualizations."""

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bazaar Exchange — Simulation Report</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'SF Mono', 'Fira Code', monospace; background: #0a0a0f; color: #e0e0e0; padding: 20px; max-width: 1400px; margin: 0 auto; }
h1 { color: #ffd700; font-size: 1.8em; margin-bottom: 5px; }
h2 { color: #00bcd4; font-size: 1.3em; margin: 35px 0 15px; border-bottom: 1px solid #333; padding-bottom: 5px; }
.subtitle { color: #888; font-size: 0.9em; margin-bottom: 25px; }
.mock-badge { background: #ff6f00; color: white; padding: 3px 10px; border-radius: 4px; font-size: 0.75em; margin-left: 10px; }

.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 15px 0; }
.stat-card { background: #141420; border: 1px solid #2a2a3a; border-radius: 8px; padding: 12px; text-align: center; }
.stat-value { font-size: 1.6em; font-weight: bold; color: #ffd700; }
.stat-label { font-size: 0.7em; color: #888; margin-top: 3px; }
.stat-value.green { color: #4caf50; }
.stat-value.red { color: #f44336; }
.stat-value.blue { color: #42a5f5; }

.chart-box { background: #141420; border: 1px solid #2a2a3a; border-radius: 8px; padding: 20px; margin: 15px 0; }
.chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
@media (max-width: 900px) { .chart-row { grid-template-columns: 1fr; } }

.bar { display: flex; align-items: center; margin: 4px 0; }
.bar-label { width: 180px; font-size: 0.78em; color: #aaa; text-align: right; padding-right: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-fill { height: 18px; border-radius: 3px; min-width: 2px; }
.bar-value { font-size: 0.72em; color: #888; padding-left: 8px; white-space: nowrap; }

table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.82em; }
th { background: #1a1a2e; color: #888; text-align: left; padding: 8px 8px; font-weight: normal; text-transform: uppercase; font-size: 0.72em; letter-spacing: 1px; }
td { padding: 6px 8px; border-bottom: 1px solid #1a1a2a; }
tr:hover { background: #1a1a25; }
.pos { color: #4caf50; }
.neg { color: #f44336; }

.tier-chip { padding: 4px 10px; border-radius: 12px; font-size: 0.75em; font-weight: bold; display: inline-block; }
.tier-penny { background: #1a1a1a; color: #888; border: 1px solid #444; }
.tier-budget { background: #0a2a0a; color: #4caf50; border: 1px solid #2e7d32; }
.tier-stress { background: #2a1a0a; color: #ff9800; border: 1px solid #e65100; }
.tier-mid { background: #2a2a0a; color: #ffeb3b; border: 1px solid #f9a825; }
.tier-premium { background: #2a0a2a; color: #e040fb; border: 1px solid #7b1fa2; }
.tier-creative { background: #0a2a2a; color: #26c6da; border: 1px solid #00838f; }

.market-card { background: #141420; border: 1px solid #2a2a3a; border-radius: 8px; padding: 14px; margin: 8px 0; }
.market-card .prompt { color: #ccc; font-style: italic; margin: 6px 0; font-size: 0.9em; }
.scores-row { display: flex; gap: 5px; margin-top: 6px; flex-wrap: wrap; }
.score-chip { padding: 2px 7px; border-radius: 3px; font-size: 0.72em; }
.score-high { background: #1b5e20; color: #a5d6a7; }
.score-mid { background: #4a3800; color: #ffe082; }
.score-low { background: #4a0000; color: #ef9a9a; }
.winner-badge { background: #2e7d32; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.78em; }
.timeout-badge { background: #8b0000; color: #fcc; padding: 2px 8px; border-radius: 10px; font-size: 0.78em; }
.revision-badge { background: #1a237e; color: #90caf9; padding: 2px 8px; border-radius: 10px; font-size: 0.78em; }

.scatter-container { position: relative; height: 300px; margin: 10px 0; }
.scatter-dot { position: absolute; width: 10px; height: 10px; border-radius: 50%; cursor: pointer; transition: transform 0.2s; }
.scatter-dot:hover { transform: scale(2); z-index: 10; }
.scatter-axis { position: absolute; color: #555; font-size: 0.7em; }

.flow-diagram { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 20px; flex-wrap: wrap; }
.flow-block { background: #1a1a2e; border: 1px solid #333; border-radius: 8px; padding: 12px 16px; text-align: center; min-width: 120px; }
.flow-block .label { font-size: 0.7em; color: #888; }
.flow-block .value { font-size: 1.3em; font-weight: bold; margin-top: 4px; }
.flow-arrow { color: #555; font-size: 1.5em; }
</style>
</head>
<body>

<h1>BAZAAR EXCHANGE""" + (' <span class="mock-badge">MOCK DATA</span>' if report['metadata'].get('is_mock') else '') + """</h1>
<div class="subtitle">Simulation Report — """ + report['metadata']['timestamp'] + """ — """ + str(report['metadata']['n_markets']) + """ markets, """ + str(report['metadata']['n_agents']) + """ agents</div>

<div class="stats-grid" id="stats-grid"></div>

<h2>EXCHANGE VALUE: WHERE DOES THE MONEY GO?</h2>
<div class="chart-box">
<div class="flow-diagram" id="money-flow"></div>
</div>

<h2>QUALITY GAP: EXCHANGE vs DIRECT API CALL</h2>
<p style="color:#888;font-size:0.85em;margin:8px 0">Winner's score minus average score across all agents. The gap is the exchange's quality value-add — what competition buys you.</p>
<div class="chart-box" id="quality-gap-chart"></div>

<h2>PRICE-QUALITY FRONTIER</h2>
<p style="color:#888;font-size:0.85em;margin:8px 0">Each dot is a settled market. Higher price doesn't always mean higher quality — the market reveals the efficient frontier.</p>
<div class="chart-box"><div class="scatter-container" id="price-quality-scatter"></div></div>

<h2>COST ABSORPTION: BUYER PAYS ONCE, AGENTS PAY MANY TIMES</h2>
<p style="color:#888;font-size:0.85em;margin:8px 0">For every $1 the buyer pays, agents collectively spend $X on failed attempts. The exchange shifts retry cost from buyer to supply side.</p>
<div class="chart-box" id="cost-absorption-chart"></div>

<h2>REVISION ROI</h2>
<p style="color:#888;font-size:0.85em;margin:8px 0">Score improvement from revision attempts. Shows how feedback-driven iteration improves outcomes.</p>
<div class="chart-box" id="revision-chart"></div>

<h2>TIER BREAKDOWN</h2>
<div class="chart-row">
<div class="chart-box" id="tier-table-container"></div>
<div class="chart-box" id="tier-depth-chart"></div>
</div>

<h2>AGENT PnL LEADERBOARD</h2>
<div class="chart-box" id="pnl-chart"></div>
<table id="agent-table"><thead><tr>
<th>#</th><th>Agent</th><th>Strategy</th><th>Aesthetic</th><th>W</th><th>L</th><th>Win%</th><th>Avg Score</th><th>Revenue</th><th>Costs</th><th>PnL</th><th>Revisions</th>
</tr></thead><tbody></tbody></table>

<h2>MARKET-BY-MARKET RESULTS</h2>
<div id="markets-list"></div>

<h2>SCORE DISTRIBUTION BY TIER</h2>
<div class="chart-box" id="score-dist"></div>

<script>
const data = """ + json.dumps(report) + """;
const econ = data.economics;
const settled = data.markets.filter(m => m.status === 'settled');
const timeouts = data.markets.filter(m => m.status === 'timeout');
const agents = Object.entries(data.agent_pnl).map(([id, a]) => ({id, ...a})).sort((a,b) => b.pnl - a.pnl);
const tierOrder = ['penny','budget','stress','mid','premium','creative'];
const tierColors = {penny:'#888',budget:'#4caf50',stress:'#ff9800',mid:'#ffeb3b',premium:'#e040fb',creative:'#26c6da'};

// Stats grid
const avgScore = settled.length ? (settled.reduce((s,m)=>s+m.score,0)/settled.length).toFixed(1) : '—';
document.getElementById('stats-grid').innerHTML = [
    ['Markets', data.metadata.n_markets, ''],
    ['Settled', settled.length, 'green'],
    ['Timeouts', timeouts.length, timeouts.length ? 'red' : ''],
    ['Avg Score', avgScore+'/10', ''],
    ['Volume', '$'+econ.total_buyer_spend.toFixed(2), 'green'],
    ['Agent Costs', '$'+econ.total_agent_costs.toFixed(2), 'red'],
    ['Exchange Fees', '$'+econ.exchange_fees.toFixed(2), 'blue'],
    ['Quality Gap', '+'+econ.avg_quality_gap.toFixed(1)+' pts', 'green'],
    ['Revisions', econ.total_revisions+' ('+econ.successful_revisions+' won)', ''],
].map(([l,v,c])=>`<div class="stat-card"><div class="stat-value ${c}">${v}</div><div class="stat-label">${l}</div></div>`).join('');

// Money flow
const agentProfit = Math.max(0, econ.total_agent_revenue - econ.total_agent_costs);
const agentLoss = Math.max(0, econ.total_agent_costs - econ.total_agent_revenue);
document.getElementById('money-flow').innerHTML = `
    <div class="flow-block"><div class="label">BUYER PAYS</div><div class="value" style="color:#ffd700">$${econ.total_buyer_spend.toFixed(2)}</div></div>
    <div class="flow-arrow">→</div>
    <div class="flow-block"><div class="label">EXCHANGE FEE (1.5%)</div><div class="value" style="color:#42a5f5">$${econ.exchange_fees.toFixed(2)}</div></div>
    <div class="flow-arrow">→</div>
    <div class="flow-block"><div class="label">WINNING AGENTS</div><div class="value" style="color:#4caf50">$${econ.total_agent_revenue.toFixed(2)}</div></div>
    <div class="flow-arrow">→</div>
    <div class="flow-block"><div class="label">API COSTS (ALL AGENTS)</div><div class="value" style="color:#f44336">$${econ.total_agent_costs.toFixed(2)}</div></div>
    <div class="flow-arrow">→</div>
    <div class="flow-block"><div class="label">NET AGENT ${agentProfit > 0 ? 'PROFIT' : 'LOSS'}</div><div class="value" style="color:${agentProfit > 0 ? '#4caf50' : '#f44336'}">$${Math.abs(agentProfit || agentLoss).toFixed(2)}</div></div>
`;

// Quality gap chart per market
const qgData = settled.map(m => {
    const scores = m.submissions.map(s => s.final_score);
    const avg = scores.reduce((a,b)=>a+b,0)/scores.length;
    return { id: m.market_id, tier: m.tier, winner: m.score, avg: avg, gap: m.score - avg };
}).sort((a,b) => b.gap - a.gap);
const maxGap = Math.max(...qgData.map(d=>Math.abs(d.gap)), 1);
document.getElementById('quality-gap-chart').innerHTML = qgData.map(d => {
    const w = Math.abs(d.gap)/maxGap*100;
    const color = d.gap > 0 ? '#4caf50' : '#f44336';
    return `<div class="bar"><div class="bar-label"><span class="tier-chip tier-${d.tier}" style="font-size:0.65em;padding:2px 6px">${d.tier}</span> ${d.id}</div><div class="bar-fill" style="width:${w}%;background:${color}"></div><div class="bar-value">winner ${d.winner}/10 vs avg ${d.avg.toFixed(1)} = <strong style="color:${color}">${d.gap>0?'+':''}${d.gap.toFixed(1)}</strong></div></div>`;
}).join('');

// Price-quality scatter
const pqContainer = document.getElementById('price-quality-scatter');
const maxP = Math.max(...data.price_quality.map(d=>d.price));
data.price_quality.forEach(d => {
    const x = (d.price/maxP)*90 + 5;
    const y = 95 - (d.score/10)*85;
    const dot = document.createElement('div');
    dot.className = 'scatter-dot';
    dot.style.cssText = `left:${x}%;top:${y}%;background:${tierColors[d.tier]||'#888'}`;
    dot.title = `${d.market_id}: $${d.price} → ${d.score}/10 (${d.tier})`;
    pqContainer.appendChild(dot);
});
['$0','$'+maxP.toFixed(2)].forEach((l,i) => {
    const el = document.createElement('div');
    el.className='scatter-axis';
    el.style.cssText=`bottom:-18px;${i?'right':'left'}:5%`;
    el.textContent=l;
    pqContainer.appendChild(el);
});
[1,5,10].forEach(s => {
    const el = document.createElement('div');
    el.className='scatter-axis';
    el.style.cssText=`left:-25px;top:${95-s/10*85}%`;
    el.textContent=s;
    pqContainer.appendChild(el);
});

// Cost absorption
const caData = data.cost_absorption.sort((a,b) => b.ratio - a.ratio);
const maxRatio = Math.max(...caData.map(d=>d.ratio), 1);
document.getElementById('cost-absorption-chart').innerHTML = caData.map(d => {
    const w = d.ratio/maxRatio*100;
    return `<div class="bar"><div class="bar-label"><span class="tier-chip tier-${d.tier}" style="font-size:0.65em;padding:2px 6px">${d.tier}</span> ${d.market_id}</div><div class="bar-fill" style="width:${w}%;background:#f44336"></div><div class="bar-value">buyer $${d.buyer_paid.toFixed(3)} → agents spent $${d.agents_spent.toFixed(3)} (${d.ratio.toFixed(1)}x)</div></div>`;
}).join('');

// Revision chart
const revData = [];
data.markets.forEach(m => {
    m.submissions.forEach(s => {
        if (s.n_revisions > 0) {
            revData.push({agent: s.agent_id, market: m.market_id, tier: m.tier,
                initial: s.initial_score, final: s.final_score,
                n: s.n_revisions, qualified: s.qualified});
        }
    });
});
if (revData.length) {
    document.getElementById('revision-chart').innerHTML = revData.map(d => {
        const improved = d.final > d.initial;
        const color = d.qualified ? '#4caf50' : (improved ? '#ffeb3b' : '#f44336');
        return `<div class="bar"><div class="bar-label">${d.agent.substring(0,20)} (${d.market})</div><div style="display:flex;align-items:center;gap:8px"><span style="color:#888">${d.initial}/10</span><span style="color:#555">→${d.n}rev→</span><span style="color:${color};font-weight:bold">${d.final}/10</span>${d.qualified?'<span class="revision-badge">QUALIFIED</span>':''}</div></div>`;
    }).join('');
} else {
    document.getElementById('revision-chart').innerHTML = '<div style="color:#555">No revisions in this simulation</div>';
}

// Tier table + depth chart
const tierTableHtml = `<table><thead><tr><th>Tier</th><th>Mkts</th><th>OK</th><th>Fail</th><th>Avg Score</th><th>Q.Gap</th><th>Participants</th><th>Qualified</th><th>Volume</th></tr></thead><tbody>${
    tierOrder.filter(t=>data.tier_summary[t]&&data.tier_summary[t].total>0).map(t=>{
        const s=data.tier_summary[t];
        return `<tr><td><span class="tier-chip tier-${t}">${t.toUpperCase()}</span></td><td>${s.total}</td><td>${s.settled}</td><td class="${s.timeouts?'neg':''}">${s.timeouts}</td><td>${s.avg_score?s.avg_score.toFixed(1):'—'}</td><td class="pos">+${s.quality_gap.toFixed(1)}</td><td>${s.avg_participants.toFixed(1)}</td><td>${s.avg_qualified.toFixed(1)}</td><td>$${s.total_volume.toFixed(2)}</td></tr>`;
    }).join('')
}</tbody></table>`;
document.getElementById('tier-table-container').innerHTML = tierTableHtml;

// Tier depth: avg participants vs qualified
const depthHtml = tierOrder.filter(t=>data.tier_summary[t]&&data.tier_summary[t].total>0).map(t=>{
    const s=data.tier_summary[t];
    const pW = (s.avg_participants/10)*100;
    const qW = (s.avg_qualified/10)*100;
    return `<div style="margin:8px 0"><div style="font-size:0.8em;color:${tierColors[t]};margin-bottom:3px">${t.toUpperCase()}</div><div class="bar" style="margin:2px 0"><div class="bar-label" style="width:80px">Compete</div><div class="bar-fill" style="width:${pW}%;background:#42a5f5;opacity:0.5"></div><div class="bar-value">${s.avg_participants.toFixed(1)}</div></div><div class="bar" style="margin:2px 0"><div class="bar-label" style="width:80px">Qualify</div><div class="bar-fill" style="width:${qW}%;background:#4caf50"></div><div class="bar-value">${s.avg_qualified.toFixed(1)}</div></div></div>`;
}).join('');
document.getElementById('tier-depth-chart').innerHTML = '<h3 style="color:#888;margin-bottom:10px">COMPETITIVE DEPTH</h3>'+depthHtml;

// PnL chart + table
const maxPnl = Math.max(...agents.map(a=>Math.abs(a.pnl)),0.01);
document.getElementById('pnl-chart').innerHTML = agents.map(a=>{
    const w=Math.abs(a.pnl)/maxPnl*100;
    const c=a.pnl>=0?'#4caf50':'#f44336';
    return `<div class="bar"><div class="bar-label">${a.id}</div><div class="bar-fill" style="width:${w}%;background:${c}"></div><div class="bar-value">${a.pnl>=0?'+':''}$${a.pnl.toFixed(4)}</div></div>`;
}).join('');

document.querySelector('#agent-table tbody').innerHTML = agents.map((a,i)=>{
    const pc=a.pnl>=0?'pos':'neg';
    return `<tr><td>${i+1}</td><td style="font-weight:bold">${a.id}</td><td>${a.economic_strategy}</td><td>${a.aesthetic}</td><td>${a.wins}</td><td>${a.losses}</td><td>${(a.win_rate*100).toFixed(0)}%</td><td>${a.avg_score.toFixed(1)}</td><td>$${a.revenue.toFixed(3)}</td><td>$${a.costs.toFixed(3)}</td><td class="${pc}" style="font-weight:bold">${a.pnl>=0?'+':''}$${a.pnl.toFixed(3)}</td><td>${a.revisions_attempted} (${a.revisions_succeeded} won)</td></tr>`;
}).join('');

// Market cards
document.getElementById('markets-list').innerHTML = data.markets.map(m=>{
    let status='';
    if(m.status==='settled'){
        const revSubs=m.submissions.filter(s=>s.n_revisions>0);
        const revNote=revSubs.length?` <span class="revision-badge">${revSubs.reduce((s,r)=>s+r.n_revisions,0)} revisions</span>`:'';
        status=`<span class="winner-badge">★ ${m.winner}</span> ${m.score}/10 in ${m.elapsed.toFixed(0)}s${revNote}`;
    } else {
        status=`<span class="timeout-badge">TIMEOUT</span>`;
    }
    const scores=(m.submissions||[]).sort((a,b)=>b.final_score-a.final_score).slice(0,10).map(s=>{
        const cls=s.final_score>=8?'score-high':(s.final_score>=6?'score-mid':'score-low');
        const rev=s.n_revisions?` r${s.n_revisions}`:'';
        return `<span class="score-chip ${cls}" title="${s.feedback}">${s.agent_id.substring(0,15)} ${s.final_score}${rev}</span>`;
    }).join('');
    return `<div class="market-card"><div style="display:flex;justify-content:space-between"><span><span class="tier-chip tier-${m.tier}">${m.tier.toUpperCase()}</span> <strong>${m.market_id}</strong></span><span style="color:#888">$${m.max_price.toFixed(3)} q≥${m.min_quality} | ${m.n_participants} agents, ${m.n_qualified} qualified</span></div><div class="prompt">"${m.prompt}"</div><div style="margin-top:6px">${status}</div><div class="scores-row">${scores}</div></div>`;
}).join('');

// Score distribution
const scoreDist={};
data.markets.forEach(m=>{
    m.submissions.forEach(s=>{
        if(!scoreDist[m.tier])scoreDist[m.tier]=[];
        scoreDist[m.tier].push(s.final_score);
    });
});
document.getElementById('score-dist').innerHTML = tierOrder.filter(t=>scoreDist[t]).map(t=>{
    const scores=scoreDist[t];
    const buckets=Array(10).fill(0);
    scores.forEach(s=>buckets[Math.min(s,10)-1]++);
    const maxB=Math.max(...buckets,1);
    const bars=buckets.map((c,i)=>{
        const h=c/maxB*60;
        const color=i>=7?'#4caf50':(i>=5?'#ffeb3b':'#f44336');
        return `<div style="display:inline-block;width:9%;text-align:center"><div style="height:60px;display:flex;align-items:flex-end;justify-content:center"><div style="width:70%;height:${h}px;background:${color};border-radius:2px 2px 0 0"></div></div><div style="font-size:0.7em;color:#666">${i+1}</div><div style="font-size:0.65em;color:#444">${c}</div></div>`;
    }).join('');
    return `<h3 style="margin-top:15px"><span class="tier-chip tier-${t}">${t.toUpperCase()}</span> n=${scores.length}, avg=${(scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1)}</h3><div>${bars}</div>`;
}).join('');
</script>
</body>
</html>"""

    with open(path, "w") as f:
        f.write(html)


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
