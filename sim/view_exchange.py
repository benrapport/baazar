#!/usr/bin/env python3
"""Financial exchange-style time series visualization.

Shows cumulative PnL equity curves for each agent and buyer surplus
over time, like a real trading dashboard.

Usage:
    python3 sim/view_exchange.py                              # latest run
    python3 sim/view_exchange.py --markets FILE --summary FILE
    python3 sim/view_exchange.py --top 10                     # show top 10 agents only
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
import numpy as np


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


# ── Time series reconstruction ────────────────────────────────────────

def build_timeseries(markets: list[dict], agent_costs: dict) -> dict:
    """Reconstruct cumulative PnL curves from market settlement events.

    Returns dict with:
        - agent_curves: {agent_id: [(market_idx, cumulative_pnl), ...]}
        - buyer_surplus: [(market_idx, cumulative_surplus)]
        - buyer_spend: [(market_idx, cumulative_spend)]
        - exchange_fees: [(market_idx, cumulative_fees)]
        - market_labels: [request_id, ...]
    """

    # Sort markets by close time
    markets_sorted = sorted(markets, key=lambda m: m.get("closed_at") or m["opened_at"])

    # Track state
    agent_cumulative_revenue: dict[str, float] = {}
    agent_cumulative_pnl: dict[str, list[tuple[int, float]]] = {}
    buyer_cumulative_surplus: list[tuple[int, float]] = []
    buyer_cumulative_spend: list[tuple[int, float]] = []
    exchange_cumulative_fees: list[tuple[int, float]] = []

    total_buyer_surplus = 0.0
    total_buyer_spend = 0.0
    total_exchange_fees = 0.0

    market_labels = []

    for idx, market in enumerate(markets_sorted):
        market_labels.append(market["request_id"][:12])
        max_price = market["max_price"]

        # Find settlement event
        settled = False
        for event in market.get("events", []):
            if event["type"] == "market_settled":
                d = event["data"]
                agent_id = d["agent_id"]
                price = d["price"]
                fee = d["exchange_fee"]
                buyer_charged = d["buyer_charged"]

                # Agent revenue
                if agent_id not in agent_cumulative_revenue:
                    agent_cumulative_revenue[agent_id] = 0.0
                    agent_cumulative_pnl[agent_id] = []
                agent_cumulative_revenue[agent_id] += price

                # Buyer surplus = what they were willing to pay - what they actually paid
                surplus = max_price - buyer_charged
                total_buyer_surplus += surplus
                total_buyer_spend += buyer_charged

                # Exchange fees
                total_exchange_fees += fee

                settled = True
                break

        # Record cumulative values for all tracked agents at this market
        for aid in agent_cumulative_pnl:
            cost = agent_costs.get(aid, 0)
            # Pro-rate cost: assume cost is spread evenly across all markets
            # Better: use actual cost, but we only have total at end
            pnl = agent_cumulative_revenue[aid]
            agent_cumulative_pnl[aid].append((idx, pnl))

        buyer_cumulative_surplus.append((idx, total_buyer_surplus))
        buyer_cumulative_spend.append((idx, total_buyer_spend))
        exchange_cumulative_fees.append((idx, total_exchange_fees))

    # Now subtract final costs to get true PnL curves
    # Since we only have total cost, distribute it proportionally across markets
    for aid in agent_cumulative_pnl:
        total_cost = agent_costs.get(aid, 0)
        points = agent_cumulative_pnl[aid]
        if not points:
            continue
        total_rev = agent_cumulative_revenue.get(aid, 0)
        # Proportional cost at each point
        adjusted = []
        for market_idx, cum_rev in points:
            if total_rev > 0:
                cost_at_point = total_cost * (cum_rev / total_rev)
            else:
                cost_at_point = total_cost * ((market_idx + 1) / len(points))
            adjusted.append((market_idx, cum_rev - cost_at_point))
        agent_cumulative_pnl[aid] = adjusted

    return {
        "agent_curves": agent_cumulative_pnl,
        "buyer_surplus": buyer_cumulative_surplus,
        "buyer_spend": buyer_cumulative_spend,
        "exchange_fees": exchange_cumulative_fees,
        "market_labels": market_labels,
        "num_markets": len(markets_sorted),
    }


# ── Rendering ─────────────────────────────────────────────────────────

# Color palette for agents — visually distinct
AGENT_COLORS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
    "#dcbeff", "#9A6324", "#fffac8", "#800000", "#aaffc3",
    "#808000", "#ffd8b1", "#000075", "#a9a9a9", "#000000",
    "#e6beff", "#1abc9c", "#e74c3c", "#2ecc71", "#3498db",
    "#9b59b6", "#34495e", "#f39c12", "#d35400", "#c0392b",
    "#27ae60", "#2980b9", "#8e44ad", "#2c3e50", "#f1c40f",
    "#e67e22", "#95a5a6", "#1abc9c", "#e74c3c", "#2ecc71",
    "#16a085", "#e74c3c", "#2ecc71", "#3498db", "#9b59b6",
    "#f39c12", "#d35400", "#c0392b", "#27ae60", "#2980b9",
]


def render_exchange_dashboard(ts: dict, output_dir: str = "sim_results",
                               top_n: int = 0) -> Path:
    """Render financial exchange-style dashboard."""

    agent_curves = ts["agent_curves"]
    num_markets = ts["num_markets"]

    # Optionally limit to top N agents by final PnL
    if top_n > 0 and len(agent_curves) > top_n:
        final_pnl = {
            aid: points[-1][1] if points else 0
            for aid, points in agent_curves.items()
        }
        top_agents = sorted(final_pnl, key=final_pnl.get, reverse=True)[:top_n]
        agent_curves = {aid: agent_curves[aid] for aid in top_agents}

    fig, axes = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={"height_ratios": [2, 1]})
    fig.suptitle("Exchange Simulation — Live Dashboard", fontsize=18, fontweight="bold",
                 color="#1a1a2e")
    fig.patch.set_facecolor("#0f0f23")

    # ── Top panel: Agent equity curves ────────────────────────────────
    ax1 = axes[0]
    ax1.set_facecolor("#1a1a2e")

    sorted_agents = sorted(
        agent_curves.items(),
        key=lambda x: x[1][-1][1] if x[1] else 0,
        reverse=True,
    )

    for i, (aid, points) in enumerate(sorted_agents):
        if not points:
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        color = AGENT_COLORS[i % len(AGENT_COLORS)]
        final_pnl = ys[-1] if ys else 0

        # Thicker line for top performers
        linewidth = 2.5 if i < 5 else 1.0
        alpha = 1.0 if i < 10 else 0.4

        ax1.plot(xs, ys, color=color, linewidth=linewidth, alpha=alpha)

        # Label the end of each line (top 10 only)
        if i < 10 and ys:
            ax1.annotate(
                f"{aid} (${final_pnl:.3f})",
                xy=(xs[-1], ys[-1]),
                fontsize=7,
                color=color,
                fontweight="bold" if i < 3 else "normal",
                ha="left",
                va="center",
            )

    ax1.axhline(y=0, color="#555", linewidth=0.8, linestyle="--")
    ax1.set_title("Agent Cumulative PnL (Equity Curves)", color="white", fontsize=14, pad=10)
    ax1.set_ylabel("Cumulative PnL (USD)", color="white", fontsize=11)
    ax1.tick_params(colors="white")
    ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter("$%.3f"))
    ax1.spines["bottom"].set_color("#333")
    ax1.spines["left"].set_color("#333")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.grid(True, alpha=0.15, color="white")

    # ── Bottom panel: Buyer surplus + exchange fees ───────────────────
    ax2 = axes[1]
    ax2.set_facecolor("#1a1a2e")

    # Buyer surplus
    if ts["buyer_surplus"]:
        xs = [p[0] for p in ts["buyer_surplus"]]
        ys_surplus = [p[1] for p in ts["buyer_surplus"]]
        ys_spend = [p[1] for p in ts["buyer_spend"]]
        ys_fees = [p[1] for p in ts["exchange_fees"]]

        ax2.fill_between(xs, ys_surplus, alpha=0.3, color="#2ecc71", label="Buyer Surplus")
        ax2.plot(xs, ys_surplus, color="#2ecc71", linewidth=2)

        ax2.plot(xs, ys_spend, color="#e74c3c", linewidth=2, label="Buyer Spend")
        ax2.plot(xs, ys_fees, color="#9b59b6", linewidth=2, label="Exchange Fees")

        # Annotate final values
        if ys_surplus:
            ax2.annotate(f"Surplus: ${ys_surplus[-1]:.3f}", xy=(xs[-1], ys_surplus[-1]),
                        fontsize=9, color="#2ecc71", fontweight="bold", ha="left")
        if ys_spend:
            ax2.annotate(f"Spend: ${ys_spend[-1]:.3f}", xy=(xs[-1], ys_spend[-1]),
                        fontsize=9, color="#e74c3c", fontweight="bold", ha="left")
        if ys_fees:
            ax2.annotate(f"Fees: ${ys_fees[-1]:.3f}", xy=(xs[-1], ys_fees[-1]),
                        fontsize=9, color="#9b59b6", fontweight="bold", ha="left")

    ax2.set_title("Buyer Surplus & Exchange Economics", color="white", fontsize=14, pad=10)
    ax2.set_xlabel(f"Market Sequence (1-{num_markets})", color="white", fontsize=11)
    ax2.set_ylabel("Cumulative USD", color="white", fontsize=11)
    ax2.tick_params(colors="white")
    ax2.yaxis.set_major_formatter(ticker.FormatStrFormatter("$%.3f"))
    ax2.spines["bottom"].set_color("#333")
    ax2.spines["left"].set_color("#333")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.grid(True, alpha=0.15, color="white")
    ax2.legend(facecolor="#1a1a2e", edgecolor="#333", labelcolor="white", fontsize=9)

    plt.tight_layout()

    output_path = Path(output_dir)
    chart_path = output_path / "exchange_dashboard.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return chart_path


# ── Bucketed PnL dashboard ────────────────────────────────────────────

def render_bucketed_dashboard(ts: dict, output_dir: str = "sim_results",
                                buckets: int = 5, top_n: int = 15) -> Path:
    """Render PnL at N evenly-spaced checkpoints, showing how agent
    economics evolve over the course of the simulation."""

    agent_curves = ts["agent_curves"]
    num_markets = ts["num_markets"]

    if not agent_curves or num_markets == 0:
        print("No data to render.")
        return None

    # Determine top agents by final PnL magnitude (winners + losers)
    final_pnl = {
        aid: points[-1][1] if points else 0
        for aid, points in agent_curves.items()
    }
    top_agents = sorted(final_pnl, key=lambda a: abs(final_pnl[a]), reverse=True)[:top_n]

    # Bucket boundaries (market indices)
    boundaries = [int(num_markets * (i + 1) / buckets) - 1 for i in range(buckets)]
    bucket_labels = [f"Market {b+1}\n({int(100*(b+1)/num_markets)}%)" for b in boundaries]

    # Sample PnL at each boundary for each agent
    # agent_curves[aid] = [(market_idx, cumulative_pnl), ...]
    def pnl_at(aid: str, market_idx: int) -> float:
        points = agent_curves.get(aid, [])
        if not points:
            return 0.0
        # Find the closest point at or before market_idx
        val = 0.0
        for idx, pnl in points:
            if idx <= market_idx:
                val = pnl
            else:
                break
        return val

    # Also sample buyer surplus at each bucket
    def series_at(series: list[tuple[int, float]], market_idx: int) -> float:
        val = 0.0
        for idx, v in series:
            if idx <= market_idx:
                val = v
            else:
                break
        return val

    # ── Build figure: 2 rows ──────────────────────────────────────────
    fig, axes = plt.subplots(2, 1, figsize=(18, 14), gridspec_kw={"height_ratios": [3, 1]})
    fig.suptitle(f"Exchange PnL — {buckets} Time Buckets ({num_markets} markets)",
                 fontsize=18, fontweight="bold", color="white")
    fig.patch.set_facecolor("#0f0f23")

    # ── Top: Agent PnL grouped bars at each bucket ────────────────────
    ax1 = axes[0]
    ax1.set_facecolor("#1a1a2e")

    n_agents = len(top_agents)
    bar_width = 0.8 / n_agents if n_agents > 0 else 0.1
    x_base = np.arange(buckets)

    # Sort agents by final PnL for consistent coloring
    top_agents_sorted = sorted(top_agents, key=lambda a: final_pnl[a], reverse=True)

    for i, aid in enumerate(top_agents_sorted):
        values = [pnl_at(aid, b) for b in boundaries]
        offset = (i - n_agents / 2) * bar_width + bar_width / 2
        color = AGENT_COLORS[i % len(AGENT_COLORS)]
        bars = ax1.bar(x_base + offset, values, bar_width, label=aid,
                       color=color, alpha=0.85, edgecolor="none")

    ax1.set_xticks(x_base)
    ax1.set_xticklabels(bucket_labels, color="white", fontsize=10)
    ax1.set_title("Agent Cumulative PnL at Each Checkpoint", color="white", fontsize=14, pad=10)
    ax1.set_ylabel("Cumulative PnL (USD)", color="white", fontsize=11)
    ax1.tick_params(colors="white")
    ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter("$%.3f"))
    ax1.axhline(y=0, color="#555", linewidth=0.8, linestyle="--")
    ax1.spines["bottom"].set_color("#333")
    ax1.spines["left"].set_color("#333")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.grid(True, alpha=0.1, color="white", axis="y")

    # Legend outside the plot
    ax1.legend(loc="upper left", fontsize=7, ncol=3,
               facecolor="#1a1a2e", edgecolor="#333", labelcolor="white")

    # ── Bottom: Buyer surplus + exchange fees at each bucket ──────────
    ax2 = axes[1]
    ax2.set_facecolor("#1a1a2e")

    surplus_vals = [series_at(ts["buyer_surplus"], b) for b in boundaries]
    spend_vals = [series_at(ts["buyer_spend"], b) for b in boundaries]
    fee_vals = [series_at(ts["exchange_fees"], b) for b in boundaries]

    width = 0.25
    ax2.bar(x_base - width, surplus_vals, width, label="Buyer Surplus", color="#2ecc71", alpha=0.85)
    ax2.bar(x_base, spend_vals, width, label="Buyer Spend", color="#e74c3c", alpha=0.85)
    ax2.bar(x_base + width, fee_vals, width, label="Exchange Fees", color="#9b59b6", alpha=0.85)

    ax2.set_xticks(x_base)
    ax2.set_xticklabels(bucket_labels, color="white", fontsize=10)
    ax2.set_title("Buyer Economics at Each Checkpoint", color="white", fontsize=14, pad=10)
    ax2.set_ylabel("Cumulative USD", color="white", fontsize=11)
    ax2.tick_params(colors="white")
    ax2.yaxis.set_major_formatter(ticker.FormatStrFormatter("$%.3f"))
    ax2.spines["bottom"].set_color("#333")
    ax2.spines["left"].set_color("#333")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.grid(True, alpha=0.1, color="white", axis="y")
    ax2.legend(facecolor="#1a1a2e", edgecolor="#333", labelcolor="white", fontsize=9)

    plt.tight_layout()

    output_path = Path(output_dir)
    chart_path = output_path / "bucketed_pnl.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return chart_path


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Financial exchange PnL dashboard")
    parser.add_argument("--markets", help="Markets JSONL file")
    parser.add_argument("--summary", help="Summary JSON file")
    parser.add_argument("--dir", default="sim_results", help="Output directory")
    parser.add_argument("--top", type=int, default=0, help="Show only top N agents")
    parser.add_argument("--buckets", type=int, default=5, help="Number of time buckets for bucketed view")
    args = parser.parse_args()

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
    agent_costs = summary.get("agent_costs_usd", {})

    print(f"Markets: {markets_path} ({len(markets)} markets)")
    print(f"Summary: {summary_path}")
    print(f"Agents with cost data: {len(agent_costs)}")

    ts = build_timeseries(markets, agent_costs)
    print(f"Agents with PnL curves: {len(ts['agent_curves'])}")

    chart_path = render_exchange_dashboard(ts, output_dir=args.dir, top_n=args.top)
    print(f"Equity curves saved to: {chart_path}")

    bucketed_path = render_bucketed_dashboard(ts, output_dir=args.dir, buckets=args.buckets,
                                                top_n=args.top or 15)
    if bucketed_path:
        print(f"Bucketed PnL saved to: {bucketed_path}")

    import subprocess
    subprocess.Popen(["open", str(chart_path)])
    if bucketed_path:
        subprocess.Popen(["open", str(bucketed_path)])


if __name__ == "__main__":
    main()
