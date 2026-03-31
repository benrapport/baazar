#!/usr/bin/env python3
"""Submit tasks as a buyer through the exchange.

Run AFTER starting the exchange (run_exchange.py) and agents (seed_agents.py).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentx import Exchange

TASKS = [
    {"input": "What is 2+2?", "max_price": 0.02, "min_quality": 5},
    {"input": "Write a haiku about the ocean", "max_price": 0.05, "min_quality": 6},
    {"input": "Explain what an API is in 2 sentences", "max_price": 0.05, "min_quality": 7},
    {"input": "Write a Python function to check if a number is prime", "max_price": 0.08, "min_quality": 7},
    {"input": "List 5 pros and cons of remote work", "max_price": 0.06, "min_quality": 6},
    {"input": "Explain the difference between TCP and UDP", "max_price": 0.07, "min_quality": 7},
    {"input": "Write a short bedtime story about a robot", "max_price": 0.08, "min_quality": 7},
    {"input": "Implement binary search in Python with comments", "max_price": 0.10, "min_quality": 7},
    {"input": "Explain blockchain to a 10-year-old", "max_price": 0.06, "min_quality": 7},
    {"input": "Design a REST API schema for a todo-list app (just the endpoints)", "max_price": 0.12, "min_quality": 8},
]


def main():
    ex = Exchange(api_key="demo", server_url="http://localhost:8000")

    print("=" * 70)
    print("  AgentX Buyer — Submitting 10 tasks through the exchange")
    print("=" * 70)

    total_spent = 0.0
    total_saved = 0.0
    results = []

    for i, task in enumerate(TASKS, 1):
        print(f"\n{'─' * 70}")
        print(f"  Task {i}/{len(TASKS)}: {task['input'][:50]}...")
        print(f"  Max price: ${task['max_price']:.4f} | Min quality: {task['min_quality']}/10")

        start = time.time()
        try:
            result = ex.call(
                input=task["input"],
                max_price=task["max_price"],
                min_quality=task["min_quality"],
                timeout=30.0,
            )
            elapsed = time.time() - start
            saved = task["max_price"] - result.price
            total_spent += result.price
            total_saved += saved

            print(f"  Winner: {result.agent_id}")
            print(f"  Price:  ${result.price:.4f} (saved ${saved:.4f})")
            print(f"  Score:  {result.score}/10")
            print(f"  Time:   {elapsed:.1f}s")
            print(f"  Output: {result.output[:100]}...")
            results.append({"task": i, "agent": result.agent_id,
                           "price": result.price, "score": result.score})
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"task": i, "agent": None, "price": 0, "score": 0})

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Tasks completed: {sum(1 for r in results if r['agent'])}/{len(TASKS)}")
    print(f"  Total spent:     ${total_spent:.4f}")
    print(f"  Total saved:     ${total_saved:.4f} (vs max prices)")

    # Agent breakdown
    from collections import Counter
    wins = Counter(r["agent"] for r in results if r["agent"])
    print(f"\n  Agent wins:")
    for agent, count in wins.most_common():
        prices = [r["price"] for r in results if r["agent"] == agent]
        avg_price = sum(prices) / len(prices)
        print(f"    {agent}: {count} wins, avg ${avg_price:.4f}")


if __name__ == "__main__":
    main()
