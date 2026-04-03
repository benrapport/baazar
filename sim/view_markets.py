#!/usr/bin/env python3
"""View market logs from a simulation run.

Usage:
    python3 sim/view_markets.py                          # latest markets file
    python3 sim/view_markets.py sim_results/markets_*.jsonl  # specific file
    python3 sim/view_markets.py --request req_abc123     # single market
    python3 sim/view_markets.py --summary                # one-line per market
"""

import argparse
import json
import sys
from pathlib import Path


def load_markets(path: Path) -> list[dict]:
    markets = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                markets.append(json.loads(line))
    return markets


def find_latest_markets_file(output_dir: str = "sim_results") -> Path | None:
    p = Path(output_dir)
    if not p.exists():
        return None
    files = sorted(p.glob("markets_*.jsonl"), key=lambda f: f.stat().st_mtime)
    return files[-1] if files else None


def format_time(ts: float, base: float) -> str:
    """Format timestamp as offset from market open."""
    delta_ms = (ts - base) * 1000
    return f"+{delta_ms:.0f}ms"


def print_market_detail(market: dict):
    rid = market["request_id"]
    opened = market["opened_at"]
    closed = market.get("closed_at")
    duration_ms = ((closed - opened) * 1000) if closed else 0

    print(f"\n{'=' * 80}")
    print(f"MARKET: {rid}")
    print(f"{'=' * 80}")
    print(f"  Input:        {market['input'][:100]}{'...' if len(market['input']) > 100 else ''}")
    print(f"  Max price:    ${market['max_price']:.4f}")
    print(f"  Min quality:  {market['min_quality']}/10")
    print(f"  Agents:       {', '.join(market['agents_invited'])}")
    print(f"  Winner:       {market.get('winner', 'none')}")
    print(f"  Duration:     {duration_ms:.0f}ms")

    print(f"\n  {'─' * 76}")
    print(f"  EVENT TIMELINE")
    print(f"  {'─' * 76}")

    for event in market.get("events", []):
        t = format_time(event["timestamp"], opened)
        etype = event["type"]
        data = event.get("data", {})

        if etype == "market_opened":
            print(f"  {t:>8s}  OPENED  timeout={data.get('timeout', '?')}s")

        elif etype == "broadcast_sent":
            status = data.get("status", "?")
            print(f"  {t:>8s}  BROADCAST → {data.get('agent_id', '?')}  ({status})")

        elif etype == "broadcast_failed":
            print(f"  {t:>8s}  BROADCAST FAILED → {data.get('agent_id', '?')}  error={data.get('error', '?')}")

        elif etype == "submission_received":
            agent = data.get("agent_id", "?")
            rev = data.get("revision", 0)
            rev_str = f" (rev {rev})" if rev > 0 else ""
            print(f"  {t:>8s}  SUBMISSION ← {agent}{rev_str}")

        elif etype == "submission_rejected":
            agent = data.get("agent_id", "?")
            reason = data.get("reason", "?")
            print(f"  {t:>8s}  REJECTED ← {agent}  reason={reason}")

        elif etype == "judge_started":
            agent = data.get("agent_id", "?")
            print(f"  {t:>8s}  JUDGING  {agent}")

        elif etype == "judge_completed":
            agent = data.get("agent_id", "?")
            score = data.get("score", "?")
            qualified = data.get("qualified", False)
            q_str = "QUALIFIED" if qualified else "NOT QUALIFIED"
            print(f"  {t:>8s}  SCORED  {agent}  {score}/10  [{q_str}]")

        elif etype == "judge_error":
            agent = data.get("agent_id", "?")
            print(f"  {t:>8s}  JUDGE ERROR  {agent}  {data.get('error', '?')}")

        elif etype == "winner_selected":
            agent = data.get("agent_id", "?")
            fill_price = data.get("fill_price", 0)
            score = data.get("score", "?")
            latency = data.get("latency_ms", 0)
            print(f"  {t:>8s}  WINNER  {agent}  ${fill_price:.4f}  score={score}/10  latency={latency:.0f}ms")

        elif etype == "market_settled":
            fill_price = data.get("fill_price", 0)
            fee = data.get("exchange_fee", 0)
            charged = data.get("buyer_charged", 0)
            print(f"  {t:>8s}  SETTLED  fill=${fill_price:.4f}  fee=${fee:.4f}  buyer_charged=${charged:.4f}")

        elif etype == "market_timeout":
            subs = data.get("submissions_received", 0)
            print(f"  {t:>8s}  TIMEOUT  {subs} submissions received, none qualified")

        else:
            print(f"  {t:>8s}  {etype}  {json.dumps(data)}")

    print()


def print_market_summary(market: dict):
    rid = market["request_id"]
    winner = market.get("winner", "none")
    n_events = len(market.get("events", []))
    submissions = [e for e in market.get("events", []) if e["type"] == "submission_received"]
    scores = [e for e in market.get("events", []) if e["type"] == "judge_completed"]

    opened = market["opened_at"]
    closed = market.get("closed_at")
    duration_ms = ((closed - opened) * 1000) if closed else 0

    fillers = ", ".join(
        b['data']['agent_id'] for b in submissions
    )

    print(f"  {rid}  winner={winner:20s}  {duration_ms:>6.0f}ms  submissions=[{fillers}]")


def main():
    parser = argparse.ArgumentParser(description="View market logs")
    parser.add_argument("file", nargs="?", help="Markets JSONL file")
    parser.add_argument("--dir", default="sim_results", help="Output directory")
    parser.add_argument("--request", "-r", help="Show only this request ID")
    parser.add_argument("--summary", "-s", action="store_true", help="One-line summary per market")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
    else:
        path = find_latest_markets_file(args.dir)

    if not path or not path.exists():
        print(f"No markets file found in {args.dir}/", file=sys.stderr)
        print("Run a simulation first, or specify a file path.", file=sys.stderr)
        sys.exit(1)

    markets = load_markets(path)
    print(f"Loaded {len(markets)} markets from {path}")

    if args.request:
        markets = [m for m in markets if m["request_id"] == args.request]
        if not markets:
            print(f"No market found with request_id={args.request}", file=sys.stderr)
            sys.exit(1)

    if args.summary:
        for m in markets:
            print_market_summary(m)
    else:
        for m in markets:
            print_market_detail(m)


if __name__ == "__main__":
    main()
