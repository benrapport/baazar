#!/usr/bin/env python3
"""Auto-submit image generation tasks to the exchange on an interval.

Run alongside the exchange, fleet, and dashboard.
Usage: python demo/run_tasks.py [--tasks N] [--interval SECS] [--price USD]
"""

import argparse
import os
import sys
import time
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

from bazaar.client import Exchange

PROMPTS = [
    "A cat wearing a tiny crown sitting on a velvet throne",
    "A lighthouse at sunset with crashing waves",
    "A cozy cabin in snowy mountains with smoke from the chimney",
    "A futuristic city skyline at night with flying cars",
    "A dragon curled around a pile of gold coins in a cave",
    "An astronaut floating in space with Earth reflected in their visor",
    "A Japanese garden with a red bridge over a koi pond",
    "A steampunk airship flying through clouds at golden hour",
    "A wolf howling at a full moon on a snowy mountain peak",
    "A magical library with floating books and glowing orbs",
    "A pirate ship sailing through a storm with lightning",
    "An underwater city with bioluminescent buildings",
    "A medieval knight on horseback in a field of wildflowers",
    "A cozy coffee shop on a rainy day seen through a window",
    "A phoenix rising from flames against a starry sky",
    "A treehouse village connected by rope bridges in a rainforest",
    "A vintage car parked on Route 66 at sunset",
    "An ancient Egyptian temple with golden light streaming in",
    "A robot artist painting a landscape on an easel",
    "A northern lights display over a frozen lake with cabin",
]


def main():
    parser = argparse.ArgumentParser(description="Submit tasks to the exchange")
    parser.add_argument("--tasks", type=int, default=10,
                        help="Number of tasks to submit (default: 10)")
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Seconds between tasks (default: 5)")
    parser.add_argument("--price", type=float, default=0.10,
                        help="Max price per task in USD (default: 0.10)")
    parser.add_argument("--timeout", type=float, default=90.0,
                        help="Timeout per task in seconds (default: 90)")
    args = parser.parse_args()

    ex = Exchange(api_key="demo")
    prompts = PROMPTS[:args.tasks]

    print(f"Submitting {len(prompts)} image tasks at ${args.price}/task")
    print(f"Interval: {args.interval}s | Timeout: {args.timeout}s")
    print(f"Estimated cost: ~${args.price * len(prompts):.2f} buyer + agent API costs")
    print()

    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"[{i}/{len(prompts)}] {prompt[:50]}...")
        start = time.time()
        try:
            result = ex.call(
                llm={"input": prompt},
                exchange={
                    "max_price": args.price,
                    "timeout": args.timeout,
                    "judge": {
                        "min_quality": 3,
                        "criteria": [
                            "Accuracy: Does the image match the prompt?",
                            "Visual quality: Is the image clear and well-composed?",
                            "Style: Is the artistic interpretation compelling?",
                        ],
                    },
                },
            )
            elapsed = time.time() - start
            print(f"  → Winner: {result.agent_id} | Score: {result.score}/10 | {elapsed:.1f}s")
            results.append({
                "task": i, "prompt": prompt[:50],
                "winner": result.agent_id, "score": result.score,
                "price": result.price, "elapsed": elapsed,
            })
        except Exception as e:
            print(f"  → ERROR: {e}")
            results.append({"task": i, "prompt": prompt[:50], "error": str(e)})

        # Wait between tasks (except after the last one)
        if i < len(prompts):
            time.sleep(args.interval)

    # Summary
    wins = [r for r in results if "winner" in r]
    if wins:
        print(f"\n{'=' * 60}")
        print(f"  COMPLETED: {len(wins)}/{len(prompts)} tasks")
        avg_score = sum(r["score"] for r in wins) / len(wins)
        avg_time = sum(r["elapsed"] for r in wins) / len(wins)
        total_spent = sum(r["price"] for r in wins)
        print(f"  Avg score: {avg_score:.1f}/10 | Avg time: {avg_time:.1f}s")
        print(f"  Total spent: ${total_spent:.4f}")

        # Winner breakdown
        from collections import Counter
        win_counts = Counter(r["winner"] for r in wins)
        print(f"\n  Top agents:")
        for agent, count in win_counts.most_common(5):
            agent_wins = [r for r in wins if r["winner"] == agent]
            avg = sum(r["score"] for r in agent_wins) / len(agent_wins)
            print(f"    {agent}: {count} wins, avg {avg:.1f}/10")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
