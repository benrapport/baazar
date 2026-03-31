#!/usr/bin/env python3
"""PnL visualization for exchange simulations.

Computes profit & loss for every participant (agents, exchange, buyer)
from market logs + summary data, then renders charts.

Usage:
    python3 sim/view_pnl.py                              # latest run
    python3 sim/view_pnl.py --markets FILE --summary FILE # specific files
    python3 sim/view_pnl.py --text                        # text-only, no charts
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


# ── Data loading ──────────────────────────────────────────────────────

def find_latest(pattern: str, output_dir: str = "sim_results") -> Path | None:
    p = Path(output_dir)
    if not p.exists():
        return None
    files = sorted(p.glob(pattern), key=lambda f: f.stat().st_mtime)
    return files[-1] if files else None


def load_markets(path: Path) -> list[dict]:
    markets = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                markets.append(json.loads(line))
    return markets


def load_summary(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


# ── PnL computation ──────────────────────────────────────────────────

def compute_pnl(markets: list[dict], summary: dict) -> dict:
    """Compute PnL for all participants from market logs + summary."""

    agent_costs = summary.get("agent_costs_usd", {})

    # Agent revenue: sum of winning bids from market_settled events
    agent_revenue: dict[str, float] = {}
    agent_wins: dict[str, int] = {}
    agent_tasks_bid: dict[str, int] = {}
    exchange_fees = 0.0
    buyer_total_charged = 0.0
    total_markets = len(markets)
    settled_markets = 0

    for market in markets:
        # Count bids per agent
        for event in market.get("events", []):
            if event["type"] == "bid_received":
                aid = event["data"]["agent_id"]
                agent_tasks_bid[aid] = agent_tasks_bid.get(aid, 0) + 1

            if event["type"] == "market_settled":
                d = event["data"]
                aid = d["agent_id"]
                agent_revenue[aid] = agent_revenue.get(aid, 0) + d["price"]
                agent_wins[aid] = agent_wins.get(aid, 0) + 1
                exchange_fees += d["exchange_fee"]
                buyer_total_charged += d["buyer_charged"]
                settled_markets += 1

    # All agent IDs (union of all sources)
    all_agents = sorted(
        set(agent_costs.keys()) | set(agent_revenue.keys()) | set(agent_tasks_bid.keys())
    )

    agents_pnl = []
    for aid in all_agents:
        revenue = agent_revenue.get(aid, 0)
        cost = agent_costs.get(aid, 0)
        profit = revenue - cost
        wins = agent_wins.get(aid, 0)
        bids = agent_tasks_bid.get(aid, 0)
        margin = (profit / revenue * 100) if revenue > 0 else 0

        agents_pnl.append({
            "agent_id": aid,
            "revenue": revenue,
            "cost": cost,
            "profit": profit,
            "margin_pct": margin,
            "wins": wins,
            "bids": bids,
            "win_rate": (wins / bids * 100) if bids > 0 else 0,
        })

    # Sort by profit descending
    agents_pnl.sort(key=lambda x: x["profit"], reverse=True)

    return {
        "agents": agents_pnl,
        "exchange": {
            "revenue": exchange_fees,
            "cost": 0,
            "profit": exchange_fees,
        },
        "buyer": {
            "total_charged": buyer_total_charged,
            "total_markets": total_markets,
            "settled_markets": settled_markets,
            "avg_price": buyer_total_charged / settled_markets if settled_markets else 0,
        },
        "totals": {
            "agent_revenue": sum(a["revenue"] for a in agents_pnl),
            "agent_cost": sum(a["cost"] for a in agents_pnl),
            "agent_profit": sum(a["profit"] for a in agents_pnl),
            "exchange_profit": exchange_fees,
            "buyer_spend": buyer_total_charged,
        },
    }


# ── Text rendering ────────────────────────────────────────────────────

def print_pnl(pnl: dict):
    agents = pnl["agents"]
    ex = pnl["exchange"]
    buyer = pnl["buyer"]
    totals = pnl["totals"]

    print("\n" + "=" * 90)
    print("PROFIT & LOSS REPORT")
    print("=" * 90)

    # Agent PnL table
    print(f"\n{'AGENT PnL':^90}")
    print("-" * 90)
    print(f"  {'Agent':<20s} {'Revenue':>10s} {'Cost':>10s} {'Profit':>10s} {'Margin':>8s} {'Wins':>6s} {'Bids':>6s} {'Win%':>7s}")
    print("-" * 90)
    for a in agents:
        profit_str = f"${a['profit']:.4f}"
        if a['profit'] < 0:
            profit_str = f"-${abs(a['profit']):.4f}"
        print(
            f"  {a['agent_id']:<20s} "
            f"${a['revenue']:>9.4f} "
            f"${a['cost']:>9.4f} "
            f"{profit_str:>10s} "
            f"{a['margin_pct']:>7.1f}% "
            f"{a['wins']:>5d} "
            f"{a['bids']:>5d} "
            f"{a['win_rate']:>6.1f}%"
        )
    print("-" * 90)
    total_profit_str = f"${totals['agent_profit']:.4f}"
    if totals['agent_profit'] < 0:
        total_profit_str = f"-${abs(totals['agent_profit']):.4f}"
    print(
        f"  {'TOTAL':<20s} "
        f"${totals['agent_revenue']:>9.4f} "
        f"${totals['agent_cost']:>9.4f} "
        f"{total_profit_str:>10s}"
    )

    # Exchange PnL
    print(f"\n{'EXCHANGE PnL':^90}")
    print("-" * 90)
    print(f"  Fee revenue:  ${ex['revenue']:.4f}")
    print(f"  Profit:       ${ex['profit']:.4f}")

    # Buyer summary
    print(f"\n{'BUYER SUMMARY':^90}")
    print("-" * 90)
    print(f"  Total spent:    ${buyer['total_charged']:.4f}")
    print(f"  Markets:        {buyer['settled_markets']}/{buyer['total_markets']} settled")
    print(f"  Avg price/task: ${buyer['avg_price']:.4f}")

    # Money flow summary
    print(f"\n{'MONEY FLOW':^90}")
    print("-" * 90)
    print(f"  Buyer pays:     ${buyer['total_charged']:.4f}")
    print(f"  → Agents earn:  ${totals['agent_revenue']:.4f}")
    print(f"  → Exchange fee: ${ex['revenue']:.4f}")
    print(f"  Agents spend on LLM APIs: ${totals['agent_cost']:.4f}")
    net_system = totals['agent_profit'] + ex['profit']
    print(f"  Net system profit: ${net_system:.4f}")
    print("=" * 90 + "\n")


# ── Chart rendering ───────────────────────────────────────────────────

def render_charts(pnl: dict, output_dir: str = "sim_results"):
    agents = pnl["agents"]
    ex = pnl["exchange"]
    buyer = pnl["buyer"]

    if not agents:
        print("No agent data to chart.")
        return None

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Exchange Simulation — PnL Dashboard", fontsize=16, fontweight="bold")

    # 1. Agent PnL waterfall (revenue, cost, profit)
    ax1 = axes[0, 0]
    agent_names = [a["agent_id"].replace("-agent", "") for a in agents]
    revenues = [a["revenue"] for a in agents]
    costs = [a["cost"] for a in agents]
    profits = [a["profit"] for a in agents]

    x = range(len(agent_names))
    width = 0.25
    bars_rev = ax1.bar([i - width for i in x], revenues, width, label="Revenue", color="#2ecc71")
    bars_cost = ax1.bar(x, costs, width, label="LLM Cost", color="#e74c3c")
    bars_profit = ax1.bar([i + width for i in x], profits, width, label="Profit",
                          color=["#3498db" if p >= 0 else "#e67e22" for p in profits])
    ax1.set_title("Agent PnL Breakdown")
    ax1.set_ylabel("USD")
    ax1.set_xticks(x)
    ax1.set_xticklabels(agent_names, rotation=30, ha="right")
    ax1.legend(fontsize=8)
    ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter("$%.4f"))
    ax1.axhline(y=0, color="black", linewidth=0.5)

    # 2. Win distribution pie
    ax2 = axes[0, 1]
    win_agents = [a for a in agents if a["wins"] > 0]
    if win_agents:
        labels = [a["agent_id"].replace("-agent", "") for a in win_agents]
        wins = [a["wins"] for a in win_agents]
        colors = plt.cm.Set2(range(len(win_agents)))
        wedges, texts, autotexts = ax2.pie(
            wins, labels=labels, autopct="%1.0f%%", colors=colors, startangle=90
        )
        for t in autotexts:
            t.set_fontsize(9)
        ax2.set_title(f"Win Distribution ({sum(wins)} markets)")
    else:
        ax2.text(0.5, 0.5, "No wins", ha="center", va="center", fontsize=14)
        ax2.set_title("Win Distribution")

    # 3. Money flow sankey-style horizontal bar
    ax3 = axes[1, 0]
    flow_labels = ["Buyer Spend", "Agent Revenue", "Exchange Fees", "Agent LLM Costs", "Agent Profit"]
    flow_values = [
        buyer["total_charged"],
        pnl["totals"]["agent_revenue"],
        ex["revenue"],
        pnl["totals"]["agent_cost"],
        pnl["totals"]["agent_profit"],
    ]
    flow_colors = ["#e74c3c", "#2ecc71", "#9b59b6", "#e67e22", "#3498db"]
    bars = ax3.barh(flow_labels, flow_values, color=flow_colors)
    ax3.set_title("Money Flow")
    ax3.set_xlabel("USD")
    ax3.xaxis.set_major_formatter(ticker.FormatStrFormatter("$%.4f"))
    for bar, val in zip(bars, flow_values):
        ax3.text(bar.get_width() + max(flow_values) * 0.02, bar.get_y() + bar.get_height() / 2,
                 f"${val:.4f}", va="center", fontsize=9)

    # 4. Margin & win rate comparison
    ax4 = axes[1, 1]
    margins = [a["margin_pct"] for a in agents]
    win_rates = [a["win_rate"] for a in agents]
    x = range(len(agent_names))
    ax4.bar([i - 0.2 for i in x], margins, 0.4, label="Profit Margin %", color="#3498db")
    ax4.bar([i + 0.2 for i in x], win_rates, 0.4, label="Win Rate %", color="#2ecc71")
    ax4.set_title("Margin vs Win Rate")
    ax4.set_ylabel("Percent")
    ax4.set_xticks(x)
    ax4.set_xticklabels(agent_names, rotation=30, ha="right")
    ax4.legend(fontsize=8)
    ax4.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f%%"))

    plt.tight_layout()

    output_path = Path(output_dir)
    chart_path = output_path / "pnl_dashboard.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return chart_path


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PnL visualization for exchange simulation")
    parser.add_argument("--markets", help="Markets JSONL file")
    parser.add_argument("--summary", help="Summary JSON file")
    parser.add_argument("--dir", default="sim_results", help="Output directory")
    parser.add_argument("--text", action="store_true", help="Text-only, no charts")
    args = parser.parse_args()

    # Find files
    markets_path = Path(args.markets) if args.markets else find_latest("markets_*.jsonl", args.dir)
    summary_path = Path(args.summary) if args.summary else find_latest("summary_*.json", args.dir)

    if not markets_path or not markets_path.exists():
        print("No markets file found. Run a simulation first.", file=sys.stderr)
        sys.exit(1)
    if not summary_path or not summary_path.exists():
        print("No summary file found. Run a simulation first.", file=sys.stderr)
        sys.exit(1)

    markets = load_markets(markets_path)
    summary = load_summary(summary_path)

    print(f"Markets: {markets_path} ({len(markets)} markets)")
    print(f"Summary: {summary_path}")

    pnl = compute_pnl(markets, summary)
    print_pnl(pnl)

    if not args.text:
        chart_path = render_charts(pnl, output_dir=args.dir)
        if chart_path:
            print(f"Dashboard saved to: {chart_path}")
            # Try to open it
            import subprocess
            subprocess.Popen(["open", str(chart_path)])


if __name__ == "__main__":
    main()
