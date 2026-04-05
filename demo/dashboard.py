#!/usr/bin/env python3
"""Real-time exchange dashboard — Bloomberg terminal for the AI agent marketplace.

Connects to the exchange SSE event stream and displays:
- Live ticker tape of market events
- Agent PnL leaderboard (revenue, estimated costs, profit)
- Market stats (volume, completed, avg score, avg latency)

Usage: python demo/dashboard.py [--url http://localhost:8000]
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load .env
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

import httpx
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agents.image_tool import get_best_option, estimate_thinking_cost


# ── Agent cost estimation ────────────────────────────────────────────

def _load_strategy_costs() -> dict[str, float]:
    """Load strategies and estimate per-task cost for each agent.

    Total cost = image generation + LLM thinking (prompt rewrite).
    """
    costs = {}
    strategies_path = ROOT / "agents" / "strategies.json"
    if strategies_path.exists():
        with open(strategies_path) as f:
            strategies = json.load(f)
        for s in strategies:
            option = get_best_option(0.10, prefer=s["economic_strategy"])
            thinking = estimate_thinking_cost(has_memory=True)  # assume memory active
            if option:
                costs[s["id"]] = option["cost"] + thinking
            else:
                costs[s["id"]] = 0.01  # fallback
    return costs


# ── State ────────────────────────────────────────────────────────────

class DashboardState:
    """Tracks all state for the TUI display."""

    def __init__(self):
        self.ticker: list[dict] = []  # Recent events (capped)
        self.agent_stats: dict[str, dict] = defaultdict(lambda: {
            "wins": 0, "losses": 0, "total_score": 0, "scored_count": 0,
            "revenue": 0.0, "tasks_seen": 0,
        })
        self.markets_completed = 0
        self.total_volume = 0.0
        self.exchange_revenue = 0.0
        self.total_latency_ms = 0.0
        self.agents_registered = 0
        self.active_games = 0
        self.start_time = time.time()
        self.agent_costs = _load_strategy_costs()
        self._lock = threading.Lock()

    def add_event(self, event: dict):
        with self._lock:
            self.ticker.append(event)
            if len(self.ticker) > 50:
                self.ticker = self.ticker[-50:]
            self._process_event(event)

    def _process_event(self, event: dict):
        etype = event.get("type", "")

        if etype == "agent_registered":
            self.agents_registered += 1

        elif etype == "task_submitted":
            self.active_games += 1
            n = event.get("agents", 0)
            for aid in list(self.agent_stats.keys())[:n]:
                self.agent_stats[aid]["tasks_seen"] += 1

        elif etype == "scored":
            aid = event.get("agent_id", "")
            score = event.get("score", 0)
            won = event.get("won", False)
            stats = self.agent_stats[aid]
            stats["total_score"] += score
            stats["scored_count"] += 1
            if won:
                stats["wins"] += 1
            else:
                stats["losses"] += 1

        elif etype == "winner":
            aid = event.get("agent_id", "")
            price = event.get("max_price", 0)
            latency = event.get("latency_ms", 0)
            self.agent_stats[aid]["revenue"] += price
            self.markets_completed += 1
            self.total_volume += price
            self.exchange_revenue += price * 0.015
            self.total_latency_ms += latency
            self.active_games = max(0, self.active_games - 1)

    def update_from_status(self, status: dict):
        with self._lock:
            self.agents_registered = status.get("agents_registered", self.agents_registered)

    def get_snapshot(self) -> dict:
        with self._lock:
            return {
                "ticker": list(self.ticker),
                "agents": dict(self.agent_stats),
                "markets": self.markets_completed,
                "volume": self.total_volume,
                "exchange_rev": self.exchange_revenue,
                "avg_latency": (self.total_latency_ms / self.markets_completed
                                if self.markets_completed else 0),
                "agents_registered": self.agents_registered,
                "active_games": self.active_games,
                "uptime": time.time() - self.start_time,
                "agent_costs": dict(self.agent_costs),
            }


# ── Rendering ────────────────────────────────────────────────────────

def _fmt_time(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


def _fmt_usd(v: float) -> str:
    return f"${v:.4f}" if v < 1 else f"${v:.2f}"


def render_ticker(events: list[dict], width: int = 80) -> Panel:
    """Render the live event ticker tape."""
    text = Text()

    for ev in events[-20:]:
        ts = _fmt_time(ev.get("timestamp", time.time()))
        etype = ev.get("type", "?")

        if etype == "task_submitted":
            task = ev.get("task", "")[:50]
            price = _fmt_usd(ev.get("max_price", 0))
            n = ev.get("agents", 0)
            text.append(f"  {ts} ", style="dim")
            text.append("NEW ", style="bold yellow")
            text.append(f'"{task}" {price} → {n} agents\n')

        elif etype == "submission":
            aid = ev.get("agent_id", "")[:25]
            text.append(f"  {ts} ", style="dim")
            text.append("SUB ", style="cyan")
            text.append(f"{aid}\n")

        elif etype == "scored":
            aid = ev.get("agent_id", "")[:25]
            score = ev.get("score", 0)
            won = ev.get("won", False)
            text.append(f"  {ts} ", style="dim")
            if won:
                text.append("WIN ", style="bold green")
                text.append(f"{aid} ", style="green")
                text.append(f"{score}/10", style="bold green")
            else:
                style = "red" if score < 6 else "white"
                text.append("SCR ", style="dim cyan")
                text.append(f"{aid} ", style=style)
                text.append(f"{score}/10", style=style)
            text.append("\n")

        elif etype == "winner":
            aid = ev.get("agent_id", "")[:25]
            score = ev.get("score", 0)
            price = _fmt_usd(ev.get("max_price", 0))
            latency = ev.get("latency_ms", 0) / 1000
            task = ev.get("task", "")[:40]
            text.append(f"  {ts} ", style="dim")
            text.append("★ SETTLED ", style="bold green")
            text.append(f"{aid} ", style="bold white")
            text.append(f"{score}/10 {price} ", style="green")
            text.append(f"{latency:.1f}s\n", style="dim")

        elif etype == "agent_registered":
            aid = ev.get("agent_id", "")[:30]
            text.append(f"  {ts} ", style="dim")
            text.append("REG ", style="dim green")
            text.append(f"{aid}\n", style="dim")

    if not events:
        text.append("  Waiting for events...", style="dim italic")

    return Panel(text, title="[bold]LIVE TICKER[/bold]", border_style="blue",
                 padding=(0, 1))


def render_leaderboard(agents: dict, agent_costs: dict) -> Panel:
    """Render the agent PnL leaderboard table."""
    table = Table(expand=True, box=None, padding=(0, 1))
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Agent", style="bold", max_width=28, no_wrap=True)
    table.add_column("W", justify="right", width=3)
    table.add_column("L", justify="right", width=3)
    table.add_column("Avg", justify="right", width=5)
    table.add_column("Revenue", justify="right", width=8)
    table.add_column("Costs", justify="right", width=8)
    table.add_column("PnL", justify="right", width=9)

    # Calculate PnL for each agent
    rows = []
    for aid, stats in agents.items():
        wins = stats["wins"]
        losses = stats["losses"]
        scored = stats["scored_count"]
        avg_score = stats["total_score"] / scored if scored else 0
        revenue = stats["revenue"]
        est_cost_per = agent_costs.get(aid, 0.01)
        total_cost = est_cost_per * scored  # every scored attempt had a cost
        pnl = revenue - total_cost
        rows.append((aid, wins, losses, avg_score, revenue, total_cost, pnl, scored))

    # Sort by PnL descending
    rows.sort(key=lambda r: r[6], reverse=True)

    for i, (aid, wins, losses, avg, rev, cost, pnl, scored) in enumerate(rows[:25], 1):
        pnl_style = "green" if pnl >= 0 else "red"
        pnl_str = f"+{_fmt_usd(pnl)}" if pnl >= 0 else f"-{_fmt_usd(abs(pnl))}"
        avg_style = "green" if avg >= 7 else ("yellow" if avg >= 5 else "red")

        table.add_row(
            str(i),
            aid[:28],
            str(wins),
            str(losses),
            f"[{avg_style}]{avg:.1f}[/{avg_style}]",
            _fmt_usd(rev),
            _fmt_usd(cost),
            f"[{pnl_style}]{pnl_str}[/{pnl_style}]",
        )

    remaining = len(rows) - 25
    if remaining > 0:
        table.add_row("", f"... +{remaining} more agents", "", "", "", "", "", "")

    return Panel(table, title="[bold]AGENT PnL LEADERBOARD[/bold]",
                 border_style="green", padding=(0, 0))


def render_stats(snap: dict) -> Panel:
    """Render the market stats bar."""
    markets = snap["markets"]
    volume = snap["volume"]
    rev = snap["exchange_rev"]
    avg_lat = snap["avg_latency"] / 1000 if snap["avg_latency"] else 0
    agents = snap["agents_registered"]
    active = snap["active_games"]
    uptime = snap["uptime"]

    mins = int(uptime // 60)
    secs = int(uptime % 60)

    parts = [
        f"[bold]Markets:[/bold] {markets}",
        f"[bold]Volume:[/bold] {_fmt_usd(volume)}",
        f"[bold]Fees:[/bold] {_fmt_usd(rev)}",
        f"[bold]Avg Latency:[/bold] {avg_lat:.1f}s",
        f"[bold]Agents:[/bold] {agents}",
        f"[bold]Active:[/bold] {active}",
        f"[bold]Uptime:[/bold] {mins:02d}:{secs:02d}",
    ]

    return Panel(
        "  │  ".join(parts),
        title="[bold]BAZAAR EXCHANGE[/bold]",
        border_style="yellow",
        padding=(0, 1),
    )


def build_display(snap: dict) -> Layout:
    """Build the full dashboard layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="stats", size=3),
        Layout(name="main"),
    )
    layout["main"].split_row(
        Layout(name="ticker", ratio=2),
        Layout(name="leaderboard", ratio=3),
    )

    layout["stats"].update(render_stats(snap))
    layout["ticker"].update(render_ticker(snap["ticker"]))
    layout["leaderboard"].update(render_leaderboard(snap["agents"], snap["agent_costs"]))

    return layout


# ── SSE listener ─────────────────────────────────────────────────────

def listen_sse(url: str, state: DashboardState, stop_event: threading.Event):
    """Connect to exchange SSE stream and update state."""
    while not stop_event.is_set():
        try:
            with httpx.Client(timeout=None) as client:
                with client.stream("GET", f"{url}/events") as resp:
                    for line in resp.iter_lines():
                        if stop_event.is_set():
                            break
                        if line.startswith("data: "):
                            try:
                                event = json.loads(line[6:])
                                state.add_event(event)
                            except json.JSONDecodeError:
                                pass
        except (httpx.ConnectError, httpx.RemoteProtocolError):
            time.sleep(2)
        except Exception:
            time.sleep(2)


def poll_status(url: str, state: DashboardState, stop_event: threading.Event):
    """Poll exchange /status every 5s for aggregate stats."""
    while not stop_event.is_set():
        try:
            resp = httpx.get(f"{url}/status", timeout=3.0)
            if resp.status_code == 200:
                state.update_from_status(resp.json())
        except Exception:
            pass
        stop_event.wait(5.0)


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Bazaar Exchange Dashboard")
    parser.add_argument("--url", default="http://localhost:8000",
                        help="Exchange URL (default: http://localhost:8000)")
    args = parser.parse_args()

    console = Console()
    state = DashboardState()
    stop = threading.Event()

    # Wait for exchange to be available
    console.print("[yellow]Connecting to exchange...[/yellow]")
    for _ in range(30):
        try:
            resp = httpx.get(f"{args.url}/status", timeout=2.0)
            if resp.status_code == 200:
                state.update_from_status(resp.json())
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        console.print("[red]Could not connect to exchange[/red]")
        sys.exit(1)

    # Start background threads
    sse_thread = threading.Thread(target=listen_sse, args=(args.url, state, stop),
                                  daemon=True)
    status_thread = threading.Thread(target=poll_status, args=(args.url, state, stop),
                                     daemon=True)
    sse_thread.start()
    status_thread.start()

    console.print("[green]Connected. Dashboard running.[/green]")
    time.sleep(0.5)

    try:
        with Live(build_display(state.get_snapshot()), console=console,
                   refresh_per_second=2, screen=True) as live:
            while True:
                snap = state.get_snapshot()
                live.update(build_display(snap))
                time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        console.print("\n[yellow]Dashboard stopped.[/yellow]")


if __name__ == "__main__":
    main()
