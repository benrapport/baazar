#!/usr/bin/env python3
"""Fire buyer tasks at the exchange.

Terminal 3:
    python3 sim/run_buyer.py --tasks 10              # Quick pilot
    python3 sim/run_buyer.py --tasks 100             # Test run
    python3 sim/run_buyer.py --tasks 1000            # Full simulation
    python3 sim/run_buyer.py --tasks 50 --concurrent 10 --category code_generation
    python3 sim/run_buyer.py --tasks 100 --difficulty hard
"""

import os
import sys
import asyncio
import logging
import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load API key (needed if exchange is in-process, but buyer itself doesn't call LLMs)
for key_path in [
    Path.home() / ".config" / "keys" / "openai",
    ROOT / ".env",
]:
    if key_path.exists():
        if key_path.name == "openai":
            os.environ.setdefault("OPENAI_API_KEY", key_path.read_text().strip())
        else:
            for line in key_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

import httpx
from sim.tasks import load_task_bank, load_tasks_by_category, load_tasks_by_difficulty, Task
from sim.results import TaskResult, ResultsWriter, generate_summary, save_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def fire_tasks(
    tasks: list[Task],
    exchange_url: str,
    max_concurrent: int,
    output_dir: str,
) -> list[TaskResult]:
    """Fire all tasks at the exchange concurrently. Returns results."""

    # Check exchange is up
    try:
        async with httpx.AsyncClient() as c:
            resp = await c.get(f"{exchange_url}/status", timeout=3)
            status = resp.json()
            logger.info(
                f"Exchange OK — {status.get('agents_registered', 0)} agents registered, "
                f"{status.get('total_transactions', 0)} transactions so far"
            )
    except Exception as e:
        print(f"ERROR: Cannot reach exchange at {exchange_url}: {e}")
        print("Start the exchange first:  python3 sim/run_exchange.py")
        sys.exit(1)

    if status.get("agents_registered", 0) == 0:
        print("WARNING: No agents registered. Start sellers first:  python3 sim/run_sellers.py")
        print("Continuing anyway (tasks will timeout)...\n")

    # Set up results writer
    Path(output_dir).mkdir(exist_ok=True)
    writer = ResultsWriter(output_dir=output_dir)

    limits = httpx.Limits(max_connections=100, max_keepalive_connections=50)
    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[TaskResult] = []
    completed = 0
    start_time = time.time()

    async def call_one(client: httpx.AsyncClient, task: Task, idx: int) -> TaskResult:
        nonlocal completed
        async with semaphore:
            try:
                resp = await client.post(
                    f"{exchange_url}/call",
                    json={
                        "llm": {
                            "input": task.input,
                        },
                        "exchange": {
                            "max_price": task.max_price,
                            "judge": {
                                "min_quality": task.min_quality,
                                "criteria": task.quality_criteria or [],
                            },
                            "timeout": task.timeout,
                        },
                    },
                    headers={"Authorization": "Bearer demo"},
                    timeout=task.timeout + 15,
                )
                if resp.status_code == 200:
                    r = resp.json()
                    result = TaskResult(
                        task_id=task.task_id,
                        category=task.category,
                        difficulty=task.difficulty,
                        winner_agent=r.get("agent_id"),
                        winning_bid=r.get("price"),
                        score=r.get("score"),
                        latency_ms=r.get("latency_ms", 0),
                        output=r.get("output", ""),
                    )
                else:
                    result = TaskResult(
                        task_id=task.task_id,
                        category=task.category,
                        difficulty=task.difficulty,
                        error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    )
            except Exception as e:
                result = TaskResult(
                    task_id=task.task_id,
                    category=task.category,
                    difficulty=task.difficulty,
                    error=f"{type(e).__name__}: {e}",
                )

            writer.write(result)
            completed += 1

            # Progress
            if completed % max(1, len(tasks) // 20) == 0 or completed == len(tasks):
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (len(tasks) - completed) / rate if rate > 0 else 0
                wins = sum(1 for r in results if r.winner_agent)
                print(
                    f"  [{completed:4d}/{len(tasks)}] "
                    f"{rate:5.1f} tasks/s  "
                    f"ETA {eta:5.0f}s  "
                    f"wins={wins}"
                )

            return result

    async with httpx.AsyncClient(limits=limits, timeout=300) as client:
        coros = [call_one(client, task, i) for i, task in enumerate(tasks)]
        results = await asyncio.gather(*coros)

    results_path = writer.close()
    logger.info(f"Results saved to {results_path}")
    return list(results)


def print_summary(summary: dict):
    """Pretty-print the simulation summary."""
    print("\n" + "=" * 70)
    print("  SIMULATION RESULTS")
    print("=" * 70)

    total = summary.get("total_tasks", 0)
    done = summary.get("completed", 0)
    failed = summary.get("timed_out", 0)
    print(f"\n  Tasks: {done} completed, {failed} failed, {total} total")

    # Leaderboard
    lb = summary.get("agent_leaderboard", [])
    if lb:
        print(f"\n  {'Agent':<25s} {'Wins':>6s} {'Win%':>7s} {'Avg Bid':>10s} {'Avg Score':>10s}")
        print("  " + "-" * 60)
        for a in lb:
            print(
                f"  {a['agent']:<25s} "
                f"{a['wins']:>6d} "
                f"{a['win_rate']*100:>6.1f}% "
                f"${a['avg_bid']:>8.4f} "
                f"{a['avg_score']:>9.1f}"
            )

    # By difficulty
    by_diff = summary.get("by_difficulty", {})
    if by_diff:
        print(f"\n  {'Difficulty':<12s} {'Done':>6s} {'Avg Score':>10s} {'Avg Bid':>10s} {'Avg Latency':>12s}")
        print("  " + "-" * 52)
        for diff, stats in by_diff.items():
            print(
                f"  {diff:<12s} "
                f"{stats.get('completed', 0):>6d} "
                f"{stats.get('avg_score', 0):>9.1f} "
                f"${stats.get('avg_bid', 0):>8.4f} "
                f"{stats.get('avg_latency_ms', 0):>10.0f}ms"
            )

    # Economics
    econ = summary.get("economics", {})
    if econ:
        print(f"\n  Total volume:  ${econ.get('total_volume_usd', 0):.4f}")
        print(f"  Avg price:     ${econ.get('avg_price_usd', 0):.4f}")

    # Timing
    timing = summary.get("timing", {})
    if timing:
        print(f"\n  Total time:    {timing.get('total_seconds', 0):.1f}s")
        print(f"  Avg latency:   {timing.get('avg_latency_ms', 0):.0f}ms")
        print(f"  P95 latency:   {timing.get('p95_latency_ms', 0):.0f}ms")

    print("\n" + "=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Fire buyer tasks at the exchange",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--tasks", type=int, default=100, help="Number of tasks to fire")
    parser.add_argument("--concurrent", type=int, default=20, help="Max concurrent requests")
    parser.add_argument("--exchange", default="http://localhost:8000", help="Exchange URL")
    parser.add_argument("--output", default="sim_results", help="Output directory")
    parser.add_argument("--category", default=None, help="Filter to one category")
    parser.add_argument("--difficulty", default=None, help="Filter to one difficulty level")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle task order")
    args = parser.parse_args()

    # Load and filter tasks
    if args.category:
        tasks = load_tasks_by_category(args.category)
        print(f"Loaded {len(tasks)} tasks in category '{args.category}'")
    elif args.difficulty:
        tasks = load_tasks_by_difficulty(args.difficulty)
        print(f"Loaded {len(tasks)} tasks at difficulty '{args.difficulty}'")
    else:
        tasks = load_task_bank()
        print(f"Loaded {len(tasks)} tasks from full bank")

    if args.shuffle:
        import random
        random.shuffle(tasks)

    tasks = tasks[: args.tasks]
    print(f"Firing {len(tasks)} tasks at {args.exchange} (concurrency={args.concurrent})\n")

    # Fire
    results = asyncio.run(fire_tasks(tasks, args.exchange, args.concurrent, args.output))

    # Summary
    summary = generate_summary(results)
    summary_path = save_summary(summary, output_dir=args.output)
    print_summary(summary)
    print(f"Full results: {args.output}/")
    print(f"Summary JSON: {summary_path}")


if __name__ == "__main__":
    main()
