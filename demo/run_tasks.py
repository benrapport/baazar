#!/usr/bin/env python3
"""Auto-submit image generation tasks to the exchange.

Tasks have varied prices, quality thresholds, criteria, and complexity
to create diverse competitive dynamics across the agent fleet.

Usage:
    python demo/run_tasks.py                    # default: 20 varied tasks
    python demo/run_tasks.py --tasks 10         # first 10 tasks
    python demo/run_tasks.py --mode uniform     # old mode: same price/quality
    python demo/run_tasks.py --mode stress      # rapid-fire low-bar tasks
"""

import argparse
import os
import random
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


# ── Task definitions ─────────────────────────────────────────────────
# Each task has: prompt, max_price, min_quality, criteria, tier label

TASKS_VARIED = [
    # ── PENNY TIER ($0.012-0.02, quality 4-5) ──────────────────────
    # Ultra-cheap — only gpt-image-1-mini ($0.009) fits. Most agents
    # must pass. Tests economic discipline.
    {
        "prompt": "A blue circle",
        "max_price": 0.012, "min_quality": 4, "tier": "penny",
        "criteria": ["Shows a blue circle"],
    },
    {
        "prompt": "A tree",
        "max_price": 0.015, "min_quality": 4, "tier": "penny",
        "criteria": ["Shows a tree"],
    },
    {
        "prompt": "A house with a red door",
        "max_price": 0.018, "min_quality": 5, "tier": "penny",
        "criteria": ["House with a red door visible"],
    },
    {
        "prompt": "A yellow star on a dark background",
        "max_price": 0.012, "min_quality": 4, "tier": "penny",
        "criteria": ["Yellow star shape on dark background"],
    },
    {
        "prompt": "A smiling face",
        "max_price": 0.015, "min_quality": 5, "tier": "penny",
        "criteria": ["A face that is smiling"],
    },

    # ── BUDGET TIER ($0.03-0.05, quality 5-6) ────────────────────────
    # Cheap tasks — budget agents should dominate
    {
        "prompt": "A red apple on a white table",
        "max_price": 0.03, "min_quality": 5, "tier": "budget",
        "criteria": ["Does the image show a red apple on a white table?"],
    },
    {
        "prompt": "A sunset over the ocean",
        "max_price": 0.04, "min_quality": 5, "tier": "budget",
        "criteria": ["Accuracy: Does it show a sunset over water?"],
    },
    {
        "prompt": "A happy golden retriever in a park",
        "max_price": 0.05, "min_quality": 5, "tier": "budget",
        "criteria": ["Shows a golden retriever in an outdoor setting"],
    },
    {
        "prompt": "A coffee cup with steam rising",
        "max_price": 0.04, "min_quality": 6, "tier": "budget",
        "criteria": ["Accuracy: Coffee cup with visible steam"],
    },
    {
        "prompt": "A mountain landscape with blue sky",
        "max_price": 0.03, "min_quality": 5, "tier": "budget",
        "criteria": ["Shows mountains under a blue sky"],
    },

    # ── MID TIER ($0.08-0.15, quality 7) ─────────────────────────────
    # Moderate quality bar — speed vs quality tension
    {
        "prompt": "A cat wearing a tiny crown sitting on a velvet throne, "
                  "with dramatic Renaissance lighting and rich fabric textures",
        "max_price": 0.10, "min_quality": 7, "tier": "mid",
        "criteria": [
            "Accuracy: Cat on throne with crown clearly visible",
            "Lighting: Renaissance-style dramatic chiaroscuro",
            "Texture: Velvet fabric looks realistic and rich",
        ],
    },
    {
        "prompt": "A Japanese garden in autumn with a red bridge over a koi "
                  "pond, falling maple leaves, and misty morning light",
        "max_price": 0.12, "min_quality": 7, "tier": "mid",
        "criteria": [
            "All elements present: bridge, koi, maple leaves, mist",
            "Composition: Balanced and serene",
            "Color palette: Autumn tones with warm-cool contrast",
        ],
    },
    {
        "prompt": "A steampunk airship with brass details flying through "
                  "clouds at golden hour, with a crew visible on deck",
        "max_price": 0.10, "min_quality": 7, "tier": "mid",
        "criteria": [
            "Steampunk aesthetic: brass, gears, Victorian engineering",
            "Golden hour lighting on the airship",
            "Crew members visible (even if small)",
        ],
    },
    {
        "prompt": "A cozy bookshop interior on a rainy evening, warm lamp "
                  "light, overflowing shelves, a cat sleeping on a stack of books",
        "max_price": 0.15, "min_quality": 7, "tier": "mid",
        "criteria": [
            "Interior scene with warm inviting atmosphere",
            "Bookshelves, lamp light, rain visible through window",
            "Cat sleeping on books (must be clearly a cat)",
        ],
    },
    {
        "prompt": "A wolf howling at a full moon on a snowy cliff edge, "
                  "northern lights visible in the sky behind",
        "max_price": 0.10, "min_quality": 7, "tier": "mid",
        "criteria": [
            "Wolf clearly howling at moon on cliff",
            "Snow environment with cold atmosphere",
            "Northern lights in the background sky",
        ],
    },

    # ── PREMIUM TIER ($0.20-0.50, quality 8-9) ──────────────────────
    # High bar — only excellent images pass. Budget agents will fail.
    {
        "prompt": "A photorealistic close-up portrait of an elderly fisherman "
                  "on his boat at dawn, weathered face with deep wrinkles, "
                  "salt-and-pepper beard, eyes reflecting the golden morning "
                  "light off the water, every pore and hair strand visible",
        "max_price": 0.30, "min_quality": 8, "tier": "premium",
        "criteria": [
            "Photorealism: Could be mistaken for a photograph",
            "Face detail: Wrinkles, pores, individual hairs visible",
            "Lighting: Golden dawn light reflected in eyes",
            "Emotional depth: Character and life story in the expression",
        ],
    },
    {
        "prompt": "An oil painting in the style of the Dutch Golden Age: "
                  "a still life with a silver goblet, ripe peaches, a half-peeled "
                  "lemon with spiral peel, purple grapes, and a butterfly perched "
                  "on a flower, all on a dark marble ledge with dramatic side lighting",
        "max_price": 0.35, "min_quality": 8, "tier": "premium",
        "criteria": [
            "Dutch Golden Age style: period-accurate technique",
            "All objects present and identifiable",
            "Dramatic chiaroscuro lighting from the side",
            "Texture mastery: metal, fruit skin, marble surface",
        ],
    },
    {
        "prompt": "A sprawling fantasy city built into the side of a massive "
                  "waterfall, with bridges spanning between towers, glowing "
                  "windows at dusk, flying creatures in the distance, and a "
                  "rainbow in the mist from the falls — highly detailed, "
                  "cinematic widescreen composition",
        "max_price": 0.40, "min_quality": 8, "tier": "premium",
        "criteria": [
            "Epic scale: city feels massive and detailed",
            "Waterfall integration: buildings built into/around falls",
            "Atmospheric depth: mist, dusk lighting, rainbow",
            "Cinematic composition: feels like a movie establishing shot",
        ],
    },
    {
        "prompt": "A hyperrealistic macro photograph of a single dewdrop on "
                  "a spider web at sunrise, with the entire garden reflected "
                  "upside-down inside the droplet, bokeh background of wildflowers",
        "max_price": 0.25, "min_quality": 9, "tier": "premium",
        "criteria": [
            "Macro realism: looks like a real macro photograph",
            "Reflection inside dewdrop must show garden inverted",
            "Spider web strands visible with water tension",
            "Bokeh background with correct depth of field",
        ],
    },
    {
        "prompt": "An architectural visualization of a futuristic museum at "
                  "night: parametric flowing white facade, floor-to-ceiling "
                  "glass revealing illuminated galleries inside, reflecting "
                  "pool in foreground mirroring the building, people as "
                  "silhouettes for scale",
        "max_price": 0.50, "min_quality": 8, "tier": "premium",
        "criteria": [
            "Architectural quality: could be a real visualization",
            "Parametric design: organic flowing forms, not boxy",
            "Night lighting: interior glow, exterior subtle",
            "Reflection pool with accurate building mirror",
            "Human silhouettes providing sense of scale",
        ],
    },

    # ── CREATIVE TIER ($0.10-0.20, quality 7-8, unusual criteria) ────
    # Tests artistic interpretation, not just accuracy
    {
        "prompt": "Visualize the feeling of nostalgia",
        "max_price": 0.15, "min_quality": 7, "tier": "creative",
        "criteria": [
            "Emotional resonance: Does it evoke nostalgia?",
            "Creative interpretation: Not literal, but metaphorical",
            "Artistic cohesion: Unified mood and palette",
        ],
    },
    {
        "prompt": "What silence looks like in a forest",
        "max_price": 0.12, "min_quality": 7, "tier": "creative",
        "criteria": [
            "Evokes silence and stillness, not just an empty forest",
            "Atmospheric quality: mist, soft light, absence",
            "Artistic interpretation beyond the literal",
        ],
    },
    {
        "prompt": "The last page of a story nobody finished",
        "max_price": 0.20, "min_quality": 8, "tier": "creative",
        "criteria": [
            "Narrative quality: tells a visual story",
            "Emotional weight: melancholy, incompleteness",
            "Creative risk: surprising interpretation rewarded",
        ],
    },
    {
        "prompt": "A color that doesn't exist yet",
        "max_price": 0.15, "min_quality": 7, "tier": "creative",
        "criteria": [
            "Creative audacity: genuinely attempts the impossible",
            "Visual impact: striking and memorable",
            "Not just a gradient or rainbow — needs concept",
        ],
    },
    {
        "prompt": "The opposite of a photograph",
        "max_price": 0.10, "min_quality": 7, "tier": "creative",
        "criteria": [
            "Conceptual depth: thoughtful interpretation",
            "Anti-photographic qualities: abstraction, distortion, impossibility",
            "Artistic merit as a standalone image",
        ],
    },
]


TIER_COLORS = {
    "penny": "\033[90m",     # gray
    "budget": "\033[32m",    # green
    "mid": "\033[33m",       # yellow
    "premium": "\033[35m",   # magenta
    "creative": "\033[36m",  # cyan
}
RESET = "\033[0m"


def main():
    parser = argparse.ArgumentParser(description="Submit tasks to the exchange")
    parser.add_argument("--tasks", type=int, default=25,
                        help="Number of tasks to submit (default: 25)")
    parser.add_argument("--interval", type=float, default=3.0,
                        help="Seconds between tasks (default: 3)")
    parser.add_argument("--timeout", type=float, default=90.0,
                        help="Timeout per task in seconds (default: 90)")
    parser.add_argument("--shuffle", action="store_true",
                        help="Randomize task order")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for shuffle (default: 42)")
    args = parser.parse_args()

    ex = Exchange(api_key="demo")
    tasks = TASKS_VARIED[:args.tasks]

    if args.shuffle:
        random.seed(args.seed)
        random.shuffle(tasks)

    total_budget = sum(t["max_price"] for t in tasks)
    tier_counts = {}
    for t in tasks:
        tier_counts[t["tier"]] = tier_counts.get(t["tier"], 0) + 1

    print(f"{'=' * 70}")
    print(f"  Bazaar Market Simulation — {len(tasks)} tasks")
    print(f"{'=' * 70}")
    print(f"  Total buyer budget: ${total_budget:.2f}")
    print(f"  Tiers: {', '.join(f'{k}={v}' for k,v in sorted(tier_counts.items()))}")
    print(f"  Interval: {args.interval}s | Timeout: {args.timeout}s")
    print()

    results = []
    for i, task in enumerate(tasks, 1):
        tier = task["tier"]
        color = TIER_COLORS.get(tier, "")
        prompt_short = task["prompt"][:55]
        min_q = task["min_quality"]

        print(f"[{i}/{len(tasks)}] {color}{tier.upper():>8}{RESET} "
              f"${task['max_price']:.2f} q≥{min_q} │ {prompt_short}...")

        start = time.time()
        try:
            result = ex.call(
                llm={"input": task["prompt"]},
                exchange={
                    "max_price": task["max_price"],
                    "timeout": args.timeout,
                    "judge": {
                        "min_quality": min_q,
                        "criteria": task["criteria"],
                    },
                },
            )
            elapsed = time.time() - start
            print(f"         → {color}Winner: {result.agent_id}{RESET} │ "
                  f"Score: {result.score}/10 │ {elapsed:.0f}s")
            results.append({
                "task": i, "tier": tier, "prompt": prompt_short,
                "winner": result.agent_id, "score": result.score,
                "price": result.price, "min_quality": min_q,
                "elapsed": elapsed,
            })
        except TimeoutError:
            elapsed = time.time() - start
            print(f"         → TIMEOUT ({elapsed:.0f}s) — no agent met q≥{min_q}")
            results.append({"task": i, "tier": tier, "prompt": prompt_short,
                           "timeout": True, "min_quality": min_q})
        except Exception as e:
            print(f"         → ERROR: {e}")
            results.append({"task": i, "tier": tier, "prompt": prompt_short,
                           "error": str(e)})

        if i < len(tasks):
            time.sleep(args.interval)

    # ── Summary ──────────────────────────────────────────────────────
    wins = [r for r in results if "winner" in r]
    timeouts = [r for r in results if r.get("timeout")]
    errors = [r for r in results if "error" in r]

    print(f"\n{'=' * 70}")
    print(f"  RESULTS")
    print(f"{'=' * 70}")
    print(f"  Completed: {len(wins)}/{len(tasks)} │ "
          f"Timeouts: {len(timeouts)} │ Errors: {len(errors)}")

    if wins:
        avg_score = sum(r["score"] for r in wins) / len(wins)
        avg_time = sum(r["elapsed"] for r in wins) / len(wins)
        total_spent = sum(r["price"] for r in wins)
        print(f"  Avg score: {avg_score:.1f}/10 │ Avg time: {avg_time:.0f}s │ "
              f"Total spent: ${total_spent:.2f}")

    # Per-tier breakdown
    print(f"\n  {'Tier':<10} {'Won':>4} {'Timeout':>8} {'Avg Score':>10} {'Avg Time':>9}")
    print(f"  {'─' * 45}")
    for tier in ["penny", "budget", "mid", "premium", "creative"]:
        tier_wins = [r for r in wins if r["tier"] == tier]
        tier_timeouts = [r for r in timeouts if r["tier"] == tier]
        tier_total = sum(1 for r in results if r["tier"] == tier)
        if tier_total == 0:
            continue
        avg_s = sum(r["score"] for r in tier_wins) / len(tier_wins) if tier_wins else 0
        avg_t = sum(r["elapsed"] for r in tier_wins) / len(tier_wins) if tier_wins else 0
        color = TIER_COLORS.get(tier, "")
        print(f"  {color}{tier:<10}{RESET} {len(tier_wins):>4} {len(tier_timeouts):>8} "
              f"{avg_s:>10.1f} {avg_t:>8.0f}s")

    # Agent leaderboard
    if wins:
        print(f"\n  {'Agent':<28} {'Wins':>5} {'Avg':>5} {'Tiers Won'}")
        print(f"  {'─' * 60}")
        from collections import Counter, defaultdict
        win_counts = Counter(r["winner"] for r in wins)
        agent_tiers = defaultdict(set)
        agent_scores = defaultdict(list)
        for r in wins:
            agent_tiers[r["winner"]].add(r["tier"])
            agent_scores[r["winner"]].append(r["score"])

        for agent, count in win_counts.most_common(10):
            avg = sum(agent_scores[agent]) / len(agent_scores[agent])
            tiers = ", ".join(sorted(agent_tiers[agent]))
            print(f"  {agent:<28} {count:>5} {avg:>5.1f} {tiers}")

    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
