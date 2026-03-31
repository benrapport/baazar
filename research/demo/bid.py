#!/usr/bin/env python3
"""
AI Exchange — 6 models compete on 100 tasks with real token economics.

Models pay for their own tokens. Budgets start at 300¢ ($3). Bids in
microcents. Exchange takes 20% of spread (capped at 1¢). First model
to meet quality threshold at lowest bid wins.
"""

import json
import os
import sys
import textwrap
import threading
import time
from pathlib import Path

# ── env loading ───────────────────────────────────────────────────────
ENV_SEARCH_PATHS = [
    Path(__file__).resolve().parent / ".env",
    Path.home() / "Desktop" / "meetrics" / ".env",
]
for _env_path in ENV_SEARCH_PATHS:
    if _env_path.exists():
        for _line in _env_path.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

from openai import OpenAI

# ── models & token pricing ($ per million tokens) ────────────────────
MODELS = {
    "o3":           {"model": "o3",           "reasoning": True,  "input_per_m": 10.00, "output_per_m": 40.00},
    "o4-mini":      {"model": "o4-mini",      "reasoning": True,  "input_per_m":  1.10, "output_per_m":  4.40},
    "gpt-4.1":      {"model": "gpt-4.1",      "reasoning": False, "input_per_m":  2.00, "output_per_m":  8.00},
    "gpt-4.1-mini": {"model": "gpt-4.1-mini", "reasoning": False, "input_per_m":  0.40, "output_per_m":  1.60},
    "gpt-4o":       {"model": "gpt-4o",       "reasoning": False, "input_per_m":  2.50, "output_per_m": 10.00},
    "gpt-4o-mini":  {"model": "gpt-4o-mini",  "reasoning": False, "input_per_m":  0.15, "output_per_m":  0.60},
}
MODEL_NAMES = list(MODELS.keys())
JUDGE_MODEL = "gpt-4.1-nano"
REASONING_TOKEN_MULTIPLIER = 8

client = OpenAI()

# ── 100 tasks across 5 price tiers ──────────────────────────────────
# Prices in CENTS. min_score 1-10.
TASK_QUEUE = [
    # ── TIER 1: Trivial (1–3¢, score 5–6) — 20 tasks ────────────────
    {"task": "What is 2+2?",                                          "buyer_price": 1.0, "min_score": 5},
    {"task": "What color is the sky on a clear day?",                  "buyer_price": 1.0, "min_score": 5},
    {"task": "Spell the word 'necessary'",                             "buyer_price": 1.0, "min_score": 5},
    {"task": "What is the capital of France?",                         "buyer_price": 1.5, "min_score": 5},
    {"task": "Name three primary colors",                              "buyer_price": 1.5, "min_score": 5},
    {"task": "What is 15% of 200?",                                    "buyer_price": 1.5, "min_score": 6},
    {"task": "How many days are in a leap year?",                      "buyer_price": 1.5, "min_score": 5},
    {"task": "What does HTML stand for?",                              "buyer_price": 2.0, "min_score": 5},
    {"task": "Convert 100 Celsius to Fahrenheit",                      "buyer_price": 2.0, "min_score": 6},
    {"task": "What is the chemical symbol for gold?",                  "buyer_price": 1.5, "min_score": 5},
    {"task": "Name the largest planet in our solar system",            "buyer_price": 1.5, "min_score": 5},
    {"task": "What is the square root of 144?",                        "buyer_price": 1.5, "min_score": 6},
    {"task": "What year did World War II end?",                        "buyer_price": 2.0, "min_score": 5},
    {"task": "What is the boiling point of water in Celsius?",         "buyer_price": 1.5, "min_score": 5},
    {"task": "Define the word 'ephemeral' in one sentence",            "buyer_price": 2.5, "min_score": 6},
    {"task": "What is 7 factorial (7!)?",                              "buyer_price": 2.0, "min_score": 6},
    {"task": "Name the four cardinal directions",                      "buyer_price": 1.0, "min_score": 5},
    {"task": "What does CPU stand for?",                               "buyer_price": 1.5, "min_score": 5},
    {"task": "How many continents are there?",                         "buyer_price": 1.0, "min_score": 5},
    {"task": "Convert the binary number 1010 to decimal",              "buyer_price": 2.5, "min_score": 6},

    # ── TIER 2: Easy (3–8¢, score 6–7) — 25 tasks ───────────────────
    {"task": "Write a haiku about the ocean",                          "buyer_price": 4.0, "min_score": 6},
    {"task": "Write a limerick about a programmer",                    "buyer_price": 4.0, "min_score": 6},
    {"task": "Explain gravity in 2 sentences",                         "buyer_price": 3.5, "min_score": 6},
    {"task": "Write a short joke about artificial intelligence",       "buyer_price": 3.0, "min_score": 6},
    {"task": "List 5 benefits of regular exercise",                    "buyer_price": 4.0, "min_score": 6},
    {"task": "Explain what a function is in programming",              "buyer_price": 5.0, "min_score": 7},
    {"task": "Write a 4-line poem about autumn",                       "buyer_price": 4.0, "min_score": 6},
    {"task": "Name 5 programming languages and what they're used for", "buyer_price": 5.0, "min_score": 7},
    {"task": "Explain the difference between a stack and a queue",     "buyer_price": 5.5, "min_score": 7},
    {"task": "Write a tongue twister about technology",                "buyer_price": 4.5, "min_score": 6},
    {"task": "Explain what an API is to a non-technical person",       "buyer_price": 5.0, "min_score": 7},
    {"task": "List 3 pros and 3 cons of remote work",                  "buyer_price": 5.0, "min_score": 6},
    {"task": "Describe the water cycle in 3 sentences",                "buyer_price": 4.0, "min_score": 6},
    {"task": "Write a recipe for a simple vinaigrette",                "buyer_price": 3.5, "min_score": 6},
    {"task": "Explain what a database index does",                     "buyer_price": 6.0, "min_score": 7},
    {"task": "Translate 'Hello, how are you?' into Spanish and French","buyer_price": 3.0, "min_score": 6},
    {"task": "Write a motivational quote about perseverance",          "buyer_price": 3.0, "min_score": 6},
    {"task": "Explain the concept of supply and demand in 3 sentences","buyer_price": 5.0, "min_score": 7},
    {"task": "Name 5 countries in Africa and their capitals",          "buyer_price": 4.5, "min_score": 6},
    {"task": "Write a 2-sentence horror story",                        "buyer_price": 3.5, "min_score": 6},
    {"task": "Explain what a linked list is",                          "buyer_price": 6.0, "min_score": 7},
    {"task": "List the 5 senses and an example stimulus for each",     "buyer_price": 3.5, "min_score": 6},
    {"task": "Explain the greenhouse effect briefly",                  "buyer_price": 5.0, "min_score": 7},
    {"task": "Write a simile and a metaphor about time",               "buyer_price": 4.0, "min_score": 6},
    {"task": "Explain what recursion is with a simple example",        "buyer_price": 7.0, "min_score": 7},

    # ── TIER 3: Moderate (8–20¢, score 7) — 25 tasks ────────────────
    {"task": "Explain the difference between SQL and NoSQL databases", "buyer_price": 10.0, "min_score": 7},
    {"task": "Write a 200-word product description for a smart water bottle","buyer_price": 12.0, "min_score": 7},
    {"task": "Explain blockchain in terms a 10-year-old could understand","buyer_price": 10.0, "min_score": 7},
    {"task": "Write a professional out-of-office email reply",         "buyer_price":  8.0, "min_score": 7},
    {"task": "Generate 3 creative business names for a pet-sitting app","buyer_price":  9.0, "min_score": 7},
    {"task": "Write a Python function that checks if a string is a palindrome","buyer_price": 12.0, "min_score": 7},
    {"task": "Explain the CAP theorem in distributed systems",         "buyer_price": 15.0, "min_score": 7},
    {"task": "Draft a tweet thread (3 tweets) about productivity tips","buyer_price":  9.0, "min_score": 7},
    {"task": "Write a bash one-liner to find the 10 largest files in a directory","buyer_price": 10.0, "min_score": 7},
    {"task": "Explain the difference between TCP and UDP",             "buyer_price": 10.0, "min_score": 7},
    {"task": "Write a compelling elevator pitch for a meal-planning app","buyer_price": 12.0, "min_score": 7},
    {"task": "Explain what a closure is in JavaScript with an example","buyer_price": 12.0, "min_score": 7},
    {"task": "Write 5 SQL queries demonstrating JOINs",               "buyer_price": 15.0, "min_score": 7},
    {"task": "Summarize the key ideas of the Lean Startup methodology","buyer_price": 10.0, "min_score": 7},
    {"task": "Write a regex pattern that validates email addresses",   "buyer_price": 12.0, "min_score": 7},
    {"task": "Explain the observer pattern with a real-world analogy", "buyer_price": 12.0, "min_score": 7},
    {"task": "Draft a meeting agenda for a sprint retrospective",      "buyer_price":  8.0, "min_score": 7},
    {"task": "Write a Python class for a simple bank account with deposit/withdraw","buyer_price": 15.0, "min_score": 7},
    {"task": "Explain MapReduce with an example",                      "buyer_price": 14.0, "min_score": 7},
    {"task": "Write a persuasive paragraph arguing for renewable energy","buyer_price":  9.0, "min_score": 7},
    {"task": "Explain ACID properties of database transactions",       "buyer_price": 12.0, "min_score": 7},
    {"task": "Generate a sample JSON schema for a user profile",       "buyer_price": 10.0, "min_score": 7},
    {"task": "Describe 3 common design patterns and when to use them", "buyer_price": 15.0, "min_score": 7},
    {"task": "Write a cover letter opening paragraph for a data science role","buyer_price":  9.0, "min_score": 7},
    {"task": "Explain event-driven architecture with pros and cons",   "buyer_price": 18.0, "min_score": 7},

    # ── TIER 4: Hard (20–50¢, score 7–8) — 20 tasks ─────────────────
    {"task": "Implement a binary search tree in Python with insert, search, and delete","buyer_price": 35.0, "min_score": 8},
    {"task": "Design a REST API schema for a todo-list app with full CRUD","buyer_price": 30.0, "min_score": 8},
    {"task": "Write a technical blog post intro about WebSockets vs SSE","buyer_price": 25.0, "min_score": 7},
    {"task": "Implement the Sieve of Eratosthenes in Python for primes up to N","buyer_price": 25.0, "min_score": 8},
    {"task": "Design a database schema for an e-commerce platform (5+ tables)","buyer_price": 40.0, "min_score": 8},
    {"task": "Write a Python decorator that implements retry with exponential backoff","buyer_price": 30.0, "min_score": 8},
    {"task": "Explain the difference between OAuth 2.0 and JWT with examples","buyer_price": 25.0, "min_score": 7},
    {"task": "Draft a technical RFC for adding rate limiting to an API","buyer_price": 40.0, "min_score": 8},
    {"task": "Implement a LRU cache in Python from scratch",           "buyer_price": 35.0, "min_score": 8},
    {"task": "Write a comprehensive comparison of React, Vue, and Svelte","buyer_price": 30.0, "min_score": 7},
    {"task": "Implement merge sort in Python with detailed comments",  "buyer_price": 25.0, "min_score": 8},
    {"task": "Design a URL shortener system (architecture + data model)","buyer_price": 40.0, "min_score": 8},
    {"task": "Write a Python async HTTP client with connection pooling","buyer_price": 35.0, "min_score": 8},
    {"task": "Explain consistency models in distributed systems (eventual, strong, causal)","buyer_price": 30.0, "min_score": 7},
    {"task": "Implement a simple pub/sub system in Python",            "buyer_price": 30.0, "min_score": 8},
    {"task": "Write a technical analysis of CQRS pattern with tradeoffs","buyer_price": 35.0, "min_score": 7},
    {"task": "Implement a thread-safe producer-consumer queue in Python","buyer_price": 30.0, "min_score": 8},
    {"task": "Draft a system design doc for a real-time chat application","buyer_price": 45.0, "min_score": 8},
    {"task": "Write a Python script that implements a simple HTTP server from scratch","buyer_price": 35.0, "min_score": 8},
    {"task": "Analyze the time/space complexity of 5 common sorting algorithms","buyer_price": 25.0, "min_score": 7},

    # ── TIER 5: Expert (50–100¢, score 8–9) — 10 tasks ──────────────
    {"task": "Design a distributed task queue system (architecture, failure handling, scaling)","buyer_price": 80.0, "min_score": 8},
    {"task": "Write a comprehensive guide to database sharding strategies","buyer_price": 70.0, "min_score": 8},
    {"task": "Implement a B-tree in Python with insert and search","buyer_price": 90.0, "min_score": 9},
    {"task": "Design a recommendation engine architecture for an e-commerce site","buyer_price": 75.0, "min_score": 8},
    {"task": "Write a detailed technical comparison of gRPC vs REST vs GraphQL","buyer_price": 60.0, "min_score": 8},
    {"task": "Implement a Raft consensus algorithm simulation in Python","buyer_price":100.0, "min_score": 9},
    {"task": "Design the data pipeline architecture for a real-time analytics platform","buyer_price": 85.0, "min_score": 8},
    {"task": "Write a comprehensive security audit checklist for a web application","buyer_price": 65.0, "min_score": 8},
    {"task": "Implement a simple compiler/interpreter for a calculator language","buyer_price": 95.0, "min_score": 9},
    {"task": "Design a multi-region failover system with consistency guarantees","buyer_price": 90.0, "min_score": 8},
]

# ── economic state ────────────────────────────────────────────────────
STARTING_BUDGET_CENTS = 300.0  # $3.00
MIN_BID_CENTS = 0.00001
ELIMINATION_THRESHOLD = 0.10   # eliminated below 0.10¢

budgets = {n: STARTING_BUDGET_CENTS for n in MODEL_NAMES}  # in cents
token_spend = {n: 0.0 for n in MODEL_NAMES}  # cumulative token cost in cents
revenue = {n: 0.0 for n in MODEL_NAMES}       # cumulative revenue from winning in cents
stats = {n: {"wins": 0, "losses": 0, "passes": 0,
             "tokens_used": {"input": 0, "output": 0}}
         for n in MODEL_NAMES}
exchange_revenue = 0.0  # cents
round_history = []  # list of dicts: {round, task, buyer_price, min_score, winner, winning_bid, scores, competitors, token_costs}
budget_lock = threading.Lock()

# ── config ────────────────────────────────────────────────────────────
JUDGE_POLL_INTERVAL = 2.0
SOLE_BIDDER_WAIT = 10.0
HARD_TIMEOUT = 120.0
MAX_TURNS = 3
EXCHANGE_FEE_RATE = 0.20
EXCHANGE_FEE_CAP = 1.00  # cents


# ═══════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════

def _token_kwarg(cfg: dict, n: int) -> dict:
    if cfg.get("reasoning"):
        return {"max_completion_tokens": n * REASONING_TOKEN_MULTIPLIER}
    return {"max_tokens": n}


def _system_role(cfg: dict) -> str:
    return "developer" if cfg.get("reasoning") else "system"


def _model_cfg(name: str) -> dict:
    return MODELS[name]


def calc_token_cost_cents(name: str, usage) -> float:
    """Calculate token cost in CENTS from API usage object."""
    cfg = MODELS[name]
    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0
    input_cost = input_tokens * cfg["input_per_m"] / 1_000_000
    output_cost = output_tokens * cfg["output_per_m"] / 1_000_000
    return (input_cost + output_cost) * 100  # dollars → cents


def deduct_tokens(name: str, usage) -> float:
    """Deduct token cost from budget. Returns cost in cents."""
    cost = calc_token_cost_cents(name, usage)
    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0
    with budget_lock:
        budgets[name] -= cost
        token_spend[name] += cost
        stats[name]["tokens_used"]["input"] += input_tokens
        stats[name]["tokens_used"]["output"] += output_tokens
    return cost


def estimated_call_cost_cents(name: str) -> float:
    """Rough estimate of one API call cost in cents (500 in, 300 out tokens)."""
    cfg = MODELS[name]
    return (500 * cfg["input_per_m"] + 300 * cfg["output_per_m"]) / 1_000_000 * 100


def parse_json(raw: str) -> dict:
    if not raw or not raw.strip():
        raise ValueError("Empty response from model")
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start != -1:
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(text, start)
            return obj
        except json.JSONDecodeError:
            pass
    raise ValueError(f"No valid JSON found in response: {text[:200]}")


def calc_exchange_fee(buyer_price: float, winning_bid: float) -> float:
    """Exchange fee in cents."""
    spread = max(0, buyer_price - winning_bid)
    return min(EXCHANGE_FEE_RATE * spread, EXCHANGE_FEE_CAP)


def build_game_state(round_num: int, for_model: str | None = None) -> str:
    """Build full game state including standings and recent history."""
    lines = [f"Round {round_num}/{len(TASK_QUEUE)}"]

    # ── Standings ─────────────────────────────────────────────────────
    lines.append(f"\n{'Model':<14s} {'W':>3s} {'L':>3s} {'P':>3s} {'Budget':>10s} {'Token$':>8s} {'WinRate':>7s}")
    with budget_lock:
        for n in MODEL_NAMES:
            s = stats[n]
            b = budgets[n]
            ts = token_spend[n]
            total_played = s["wins"] + s["losses"]
            wr = f"{s['wins']/total_played*100:.0f}%" if total_played > 0 else "—"
            tag = " (ELIMINATED)" if b < ELIMINATION_THRESHOLD else ""
            lines.append(f"{n:<14s} {s['wins']:>3d} {s['losses']:>3d} {s['passes']:>3d} "
                         f"{b:>8.2f}¢  {ts:>6.2f}¢ {wr:>7s}{tag}")

    # ── Recent round history (last 10) ────────────────────────────────
    if round_history:
        lines.append(f"\nRECENT HISTORY (last {min(10, len(round_history))} rounds):")
        for h in round_history[-10:]:
            task_short = h["task"][:40]
            if h["winner"]:
                winner_score = h["scores"].get(h["winner"], "?")
                n_competed = len([c for c in h["competitors"] if c != "passed"])
                lines.append(f"  R{h['round']:>2d}: {task_short:<40s} → "
                             f"{h['winner']} won at {h['winning_bid']:.1f}¢ "
                             f"({winner_score}/10, {n_competed} competed, "
                             f"buyer paid {h['buyer_price']:.1f}¢ max)")
            else:
                lines.append(f"  R{h['round']:>2d}: {task_short:<40s} → NO CONTEST")

    # ── Competitive analysis for this model ───────────────────────────
    if for_model and round_history:
        my_wins = [h for h in round_history if h["winner"] == for_model]
        my_losses = [h for h in round_history
                     if for_model in h["competitors"] and h["winner"] != for_model and h["winner"]]
        lines.append(f"\nYOUR HISTORY ({for_model}):")
        if my_wins:
            avg_win_bid = sum(h["winning_bid"] for h in my_wins) / len(my_wins)
            avg_win_price = sum(h["buyer_price"] for h in my_wins) / len(my_wins)
            lines.append(f"  Wins: {len(my_wins)} — avg bid {avg_win_bid:.1f}¢ on avg {avg_win_price:.1f}¢ tasks")
        if my_losses:
            who_beat_me = {}
            for h in my_losses:
                w = h["winner"]
                who_beat_me[w] = who_beat_me.get(w, 0) + 1
            rivals = ", ".join(f"{k}({v}x)" for k, v in sorted(who_beat_me.items(), key=lambda x: -x[1]))
            lines.append(f"  Lost to: {rivals}")

        # Upcoming tasks preview (next 3)
        remaining = TASK_QUEUE[round_num:]  # 0-indexed, round_num is current (1-indexed) so this is correct
        if remaining:
            lines.append(f"\n  UPCOMING TASKS (next {min(3, len(remaining))}):")
            for t in remaining[:3]:
                lines.append(f"    {t['buyer_price']:.1f}¢ (score ≥{t['min_score']}): {t['task'][:50]}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════════════

BIDDER_INITIAL_SYSTEM = textwrap.dedent("""\
You are {model_name}, competing in a marketplace auction against {n_competitors} other AI models.

=== GAME STATE ===
{game_state}

=== THIS TASK ===
"{task_text}"
Buyer offers {buyer_price:.2f}¢ for quality score {min_score}/10 or better.

=== YOUR ECONOMICS ===
Budget remaining: {budget:.2f}¢
Your estimated token cost per call: ~{est_token_cost:.3f}¢
Rounds remaining: {rounds_remaining}
WARNING: You pay tokens even if you lose! Competing costs ~{est_token_cost:.3f}¢ minimum.

=== STRATEGIC DECISION ===
Before bidding, consider:
1. TASK FIT: Is this task suited to your strengths? Simple fact recall, creative writing, code, analysis?
2. PRICE VS COST: Does the buyer price ({buyer_price:.2f}¢) justify your token cost (~{est_token_cost:.3f}¢)?
3. COMPETITION: Based on recent history, who typically wins these tasks? At what price?
4. BUDGET MANAGEMENT: You have {budget:.2f}¢ left across {rounds_remaining} rounds. Pace yourself.
5. UPCOMING TASKS: Are there higher-value tasks coming that are a better fit for you?
6. WIN PROBABILITY: Given the competition, can you realistically win this one?

=== ECONOMICS ===
- You SPEND tokens from your budget for every API call (~{est_token_cost:.3f}¢ each).
- If you WIN: you RECEIVE your bid amount as payment (budget goes UP).
- Net profit = bid received − tokens spent. You want to MAXIMIZE profit.
- If you LOSE: you spent tokens but earn nothing. Budget goes DOWN.
- PASS costs nothing (no API call, no token cost).

=== RULES ===
- Bid LESS than {buyer_price:.2f}¢. Bids at or above are rejected.
- Lowest qualifying bid wins (score ≥ {min_score}/10).
- If buyer_price is barely above your token cost, the profit margin is thin — PASS unless confident.
- PASS to save budget for higher-value tasks where you have an edge.

Respond with ONLY valid JSON:
{{"compete": true/false, "reasoning": "<1-2 sentences on why you compete or pass>", "bid": <number in cents or 0>, "work": "<your complete output if competing>"}}
""")

BIDDER_REVISION_SYSTEM = textwrap.dedent("""\
Your submission did not meet the quality threshold.

=== YOUR RESULT ===
Score: {score}/10 (need {min_score}/10)
Feedback: {feedback}

=== YOUR ECONOMICS ===
Budget: {budget:.2f}¢ | Token spend so far: {token_spent:.2f}¢
Revising costs another ~{est_token_cost:.3f}¢ in tokens.

=== THIS TASK ===
Task: {task}
Buyer: {buyer_price:.2f}¢, min quality: {min_score}/10
Your bid: {bid:.2f}¢
Attempt: {attempt}/{max_turns}
Competitors still active: {n_active}

Respond with ONLY valid JSON:
{{"action": "revise" or "pass", "work": "<your revised output, only if revise>"}}
""")

JUDGE_SCORE_SYSTEM = textwrap.dedent("""\
You are scoring AI-generated work for a marketplace. Rate each submission 1-10.

Scoring criteria:
- Correctness: Does it accurately complete the task?
- Completeness: Is anything missing?
- Clarity: Is it well-written and easy to understand?
- Effort: Does it show genuine effort, not a minimal throwaway answer?

Be a fair but demanding judge. 7 = good professional quality. 5 = mediocre. 9-10 = excellent.
Provide a score and brief feedback (1 sentence) per submission.

Respond with ONLY valid JSON:
{{"scores": {{"<model_name>": {{"score": <1-10>, "feedback": "<1 sentence>"}}, ...}}}}
""")


# ═══════════════════════════════════════════════════════════════════════
# ROUND STATE
# ═══════════════════════════════════════════════════════════════════════

class RoundState:
    def __init__(self, task: str, model_names: list[str],
                 buyer_price: float, min_score: int):
        self.task = task
        self.buyer_price = buyer_price  # cents
        self.min_score = min_score
        self.models = list(model_names)
        self.lock = threading.Lock()
        self.start_time = time.time()

        self.submissions = {}
        self.status = {n: "bidding" for n in model_names}
        self.scores = {}
        self.feedback = {}
        self.turn = {n: 0 for n in model_names}
        self.token_costs = {n: 0.0 for n in model_names}  # cents per round

        self.judge_action = None
        self.judge_reasoning = None
        self.winner = None
        self.done = threading.Event()
        self.events = []

        self.revision_ready = {n: threading.Event() for n in model_names}

    def elapsed(self) -> float:
        return time.time() - self.start_time

    def log(self, msg: str):
        with self.lock:
            self.events.append((self.elapsed(), msg))

    def submit(self, name: str, bid: float, work: str, compete: bool):
        with self.lock:
            if not compete:
                self.status[name] = "passed"
                self.submissions[name] = {
                    "bid": 0, "work": "", "compete": False,
                    "timestamp": self.elapsed(),
                }
            else:
                self.status[name] = "submitted"
                self.submissions[name] = {
                    "bid": bid, "work": work, "compete": True,
                    "timestamp": self.elapsed(),
                }

    def submit_revision(self, name: str, work: str):
        with self.lock:
            if name in self.submissions:
                self.submissions[name]["work"] = work
                self.submissions[name]["timestamp"] = self.elapsed()
            self.status[name] = "submitted"
            self.turn[name] += 1

    def set_score(self, name: str, score: int, feedback: str):
        with self.lock:
            self.scores[name] = score
            self.feedback[name] = feedback

    def finish(self, winner: str | None, action: str, reasoning: str):
        with self.lock:
            self.winner = winner
            self.judge_action = action
            self.judge_reasoning = reasoning
        self.done.set()
        for ev in self.revision_ready.values():
            ev.set()


# ═══════════════════════════════════════════════════════════════════════
# BIDDER THREAD
# ═══════════════════════════════════════════════════════════════════════

def bidder_work(name: str, state: RoundState, round_num: int):
    cfg = _model_cfg(name)
    est_cost = estimated_call_cost_cents(name)

    try:
        state.log(f"{name}: working... (est ~{est_cost:.3f}¢/call)")

        game_state = build_game_state(round_num, for_model=name)
        with budget_lock:
            my_budget = budgets[name]

        rounds_remaining = len(TASK_QUEUE) - round_num + 1

        resp = client.chat.completions.create(
            model=cfg["model"],
            messages=[
                {"role": _system_role(cfg),
                 "content": BIDDER_INITIAL_SYSTEM.format(
                     model_name=name,
                     n_competitors=len(state.models) - 1,
                     game_state=game_state,
                     task_text=state.task,
                     buyer_price=state.buyer_price,
                     min_score=state.min_score,
                     budget=my_budget,
                     est_token_cost=est_cost,
                     rounds_remaining=rounds_remaining,
                 )},
                {"role": "user", "content": state.task},
            ],
            **_token_kwarg(cfg, 4096),
        )

        # Deduct token cost
        token_cost = deduct_tokens(name, resp.usage)
        with state.lock:
            state.token_costs[name] += token_cost
        state.log(f"{name}: tokens cost {token_cost:.3f}¢")

        data = parse_json(resp.choices[0].message.content)

        compete = data.get("compete", True)
        bid_amt = float(data.get("bid", 0))
        reasoning = data.get("reasoning", "")
        work_raw = data.get("work", "")
        work = work_raw if isinstance(work_raw, str) else json.dumps(work_raw, indent=2)

        if compete:
            # Bid must be under buyer price. No budget clamp — bid is revenue, not cost.
            bid_amt = max(MIN_BID_CENTS, min(bid_amt, state.buyer_price - 0.01))

        state.submit(name, bid_amt, work, compete)
        with state.lock:
            state.turn[name] = 1

        if compete:
            state.log(f"{name}: bid {bid_amt:.2f}¢ at {state.elapsed():.1f}s — {reasoning[:80]}")
        else:
            state.log(f"{name}: PASSED — {reasoning[:80]}")
            with budget_lock:
                stats[name]["passes"] += 1
            return

        # ── Revision loop ─────────────────────────────────────────────
        while not state.done.is_set():
            state.revision_ready[name].wait(timeout=2.0)
            state.revision_ready[name].clear()

            if state.done.is_set():
                return

            with state.lock:
                score = state.scores.get(name)
                fb = state.feedback.get(name)
                turn_num = state.turn[name]

            if score is None:
                continue

            if score >= state.min_score:
                return

            if turn_num >= MAX_TURNS:
                state.log(f"{name}: max turns, stopping")
                with state.lock:
                    state.status[name] = "passed"
                return

            state.log(f"{name}: scored {score}/10, deciding revision...")

            n_active = sum(1 for n in state.models
                          if state.status.get(n) in ("submitted", "bidding", "revising"))

            with budget_lock:
                my_budget = budgets[name]

            rev_resp = client.chat.completions.create(
                model=cfg["model"],
                messages=[
                    {"role": _system_role(cfg),
                     "content": BIDDER_REVISION_SYSTEM.format(
                         score=score,
                         min_score=state.min_score,
                         feedback=fb or "No specific feedback.",
                         budget=my_budget,
                         token_spent=token_spend[name],
                         est_token_cost=est_cost,
                         task=state.task,
                         buyer_price=state.buyer_price,
                         bid=bid_amt,
                         attempt=turn_num + 1,
                         max_turns=MAX_TURNS,
                         n_active=n_active,
                     )},
                    {"role": "user", "content": "Revise or pass?"},
                ],
                **_token_kwarg(cfg, 4096),
            )

            rev_token_cost = deduct_tokens(name, rev_resp.usage)
            with state.lock:
                state.token_costs[name] += rev_token_cost
            state.log(f"{name}: revision tokens {rev_token_cost:.3f}¢")

            rev_data = parse_json(rev_resp.choices[0].message.content)

            action = rev_data.get("action", "pass")
            if action == "revise":
                rev_work = rev_data.get("work", work)
                work = rev_work if isinstance(rev_work, str) else json.dumps(rev_work, indent=2)
                state.submit_revision(name, work)
                state.log(f"{name}: revision {turn_num+1} at {state.elapsed():.1f}s")
            else:
                state.log(f"{name}: passed after score {score}/10")
                with state.lock:
                    state.status[name] = "passed"
                return

    except Exception as e:
        state.log(f"{name}: ERROR — {e}")
        with state.lock:
            state.status[name] = "failed"


# ═══════════════════════════════════════════════════════════════════════
# JUDGE THREAD
# ═══════════════════════════════════════════════════════════════════════

def judge_work(state: RoundState):
    last_scored = {}

    while not state.done.is_set():
        time.sleep(JUDGE_POLL_INTERVAL)
        if state.done.is_set():
            return

        elapsed = state.elapsed()
        with state.lock:
            statuses = {n: state.status[n] for n in state.models}
            subs = {n: state.submissions.get(n) for n in state.models}

        competing = [n for n in state.models
                     if statuses[n] == "submitted" and subs[n] and subs[n]["compete"]]
        out = [n for n in state.models if statuses[n] in ("passed", "failed")]
        working = [n for n in state.models if statuses[n] in ("bidding", "revising")]

        state.log(f"Judge: {len(competing)} ready, {len(working)} working, {len(out)} out")

        if len(out) == len(state.models):
            state.finish(None, "NO_CONTEST", "All models passed or failed.")
            return

        if len(competing) == 0:
            if elapsed > HARD_TIMEOUT:
                state.finish(None, "TIMEOUT", "No submissions.")
                return
            continue

        if len(competing) >= 1 and len(working) >= 1:
            earliest = min(subs[n]["timestamp"] for n in competing)
            if elapsed - earliest < SOLE_BIDDER_WAIT:
                continue

        to_score = []
        for n in competing:
            sub_ts = subs[n]["timestamp"]
            if n not in last_scored or last_scored[n] < sub_ts:
                to_score.append(n)

        if not to_score:
            with state.lock:
                qualifiers = [n for n in competing
                              if state.scores.get(n, 0) >= state.min_score]
            if qualifiers:
                winner = min(qualifiers, key=lambda n: subs[n]["bid"])
                state.finish(winner, "ACCEPT",
                             f"{winner} scored {state.scores[winner]}/10 at {subs[winner]['bid']:.2f}¢")
                return

            if len(working) == 0 and len(competing) > 0:
                can_revise = any(state.turn.get(n, 0) < MAX_TURNS for n in competing)
                if not can_revise:
                    winner = min(competing, key=lambda n: subs[n]["bid"])
                    state.finish(winner, "ACCEPT",
                                 f"No qualifier. {winner} at {subs[winner]['bid']:.2f}¢ (score {state.scores.get(winner, 0)}/10)")
                    return
            continue

        state.log(f"Judge: scoring {len(to_score)} submissions...")
        try:
            scores = _judge_score(state, to_score)
        except Exception as e:
            state.log(f"Judge: scoring error ({e})")
            winner = min(competing, key=lambda n: subs[n]["bid"])
            state.finish(winner, "ACCEPT", f"Scoring error — {winner} wins by lowest bid.")
            return

        qualifiers = []
        for n in to_score:
            s = scores.get(n, {})
            score = s.get("score", 0)
            fb = s.get("feedback", "")
            state.set_score(n, score, fb)
            last_scored[n] = subs[n]["timestamp"]
            state.log(f"  {n}: {score}/10 — {fb[:60]}")
            if score >= state.min_score:
                qualifiers.append(n)

        with state.lock:
            for n in competing:
                if n not in to_score and state.scores.get(n, 0) >= state.min_score:
                    qualifiers.append(n)

        if qualifiers:
            winner = min(qualifiers, key=lambda n: subs[n]["bid"])
            state.log(f"Judge: ACCEPT {winner} ({state.scores[winner]}/10, {subs[winner]['bid']:.2f}¢)")
            state.finish(winner, "ACCEPT",
                         f"{winner} scored {state.scores[winner]}/10 at {subs[winner]['bid']:.2f}¢")
            return

        for n in to_score:
            state.revision_ready[n].set()

        if elapsed > HARD_TIMEOUT:
            if competing:
                winner = min(competing, key=lambda n: subs[n]["bid"])
                state.finish(winner, "TIMEOUT", f"Timeout — {winner} at lowest bid.")
            else:
                state.finish(None, "TIMEOUT", "Hard timeout.")
            return


def _judge_score(state: RoundState, names: list[str]) -> dict:
    parts = [f"Task: {state.task}\nQuality threshold: {state.min_score}/10\n"]
    for name in names:
        sub = state.submissions[name]
        parts.append(f"## {name} (bid {sub['bid']:.2f}¢)\n{sub['work']}\n")
    prompt = "\n".join(parts)

    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": JUDGE_SCORE_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    result = parse_json(resp.choices[0].message.content)
    return result.get("scores", result)


# ═══════════════════════════════════════════════════════════════════════
# CLI / DISPLAY
# ═══════════════════════════════════════════════════════════════════════

STATUS_ICONS = {
    "bidding":   "\033[33m⏳\033[0m",
    "submitted": "\033[92m✓\033[0m",
    "passed":    "\033[90m⊘\033[0m",
    "failed":    "\033[91m✗\033[0m",
    "revising":  "\033[33m✎\033[0m",
}


def render_tick(state: RoundState):
    elapsed = int(state.elapsed())
    sys.stdout.write(f"\r  [{elapsed:02d}s] ")
    parts = []
    for name in state.models:
        with state.lock:
            status = state.status[name]
            sub = state.submissions.get(name)
            score = state.scores.get(name)
        icon = STATUS_ICONS.get(status, "?")
        short = name[:8]
        if status == "submitted" and sub and sub["compete"]:
            score_str = f"({score}/10)" if score else ""
            parts.append(f"{short}{icon}{sub['bid']:.1f}¢{score_str}")
        else:
            parts.append(f"{short}{icon}")
    sys.stdout.write(" ".join(parts))
    sys.stdout.flush()


def display_transaction(state: RoundState):
    global exchange_revenue

    print("\n")

    if state.winner is None:
        print(f"  ── No transaction: {state.judge_reasoning}")
        return

    winner = state.winner
    sub = state.submissions[winner]
    bid_amt = sub["bid"]
    score = state.scores.get(winner, 0)
    fee = calc_exchange_fee(state.buyer_price, bid_amt)
    spread = state.buyer_price - bid_amt
    buyer_pays = bid_amt + fee
    buyer_surplus = state.buyer_price - buyer_pays
    winner_token_cost = state.token_costs.get(winner, 0)

    # Seller RECEIVES their bid amount as payment (budget goes UP)
    # Tokens were already deducted during API calls (budget went DOWN)
    # Net profit = bid received - tokens spent
    with budget_lock:
        budgets[winner] += bid_amt
        revenue[winner] += bid_amt
        stats[winner]["wins"] += 1
        exchange_revenue += fee
        for n in state.models:
            s = state.submissions.get(n)
            if s and s["compete"] and n != winner:
                stats[n]["losses"] += 1

    print(f"  ┌{'─' * 62}")
    print(f"  │ TRANSACTION")
    print(f"  │")
    print(f"  │ Task:    {state.task[:55]}")
    print(f"  │ Buyer:   {state.buyer_price:.2f}¢ max, requires {state.min_score}/10")
    print(f"  │")
    net_profit = bid_amt - winner_token_cost

    print(f"  │ Winner:  {winner}")
    print(f"  │   Offer:         {bid_amt:>8.2f}¢  (seller charges)")
    print(f"  │   Score:         {score}/10")
    print(f"  │   Token cost:    {winner_token_cost:>8.3f}¢  (internal API cost)")
    print(f"  │   Net profit:    {net_profit:>8.3f}¢  (offer − tokens)")
    print(f"  │")
    print(f"  │ Spread:          {spread:>8.2f}¢  (buyer max − offer)")
    print(f"  │ Exchange fee:    {fee:>8.2f}¢  (20% of spread, capped 1¢)")
    print(f"  │ Buyer pays:      {buyer_pays:>8.2f}¢  (offer + fee)")
    print(f"  │ Buyer surplus:   {buyer_surplus:>8.2f}¢  (max − buyer pays)")
    print(f"  └{'─' * 62}")

    # Winner output
    print(f"\n  \033[92m★ {winner}'s output:\033[0m")
    winner_work = sub["work"] if isinstance(sub["work"], str) else json.dumps(sub["work"], indent=2)
    lines = winner_work.split("\n")
    for line in lines[:20]:
        print(f"    {line}")
    if len(lines) > 20:
        print(f"    ... ({len(lines) - 20} more lines)")

    # Other bids
    runners = [(n, state.submissions[n], state.scores.get(n, 0), state.token_costs.get(n, 0))
               for n in state.models
               if n != winner and n in state.submissions
               and state.submissions[n]["compete"]]
    if runners:
        print(f"\n  \033[90mOther bids:\033[0m")
        for name, rsub, rscore, rtok in sorted(runners, key=lambda x: x[1]["bid"]):
            work_text = rsub["work"] if isinstance(rsub["work"], str) else json.dumps(rsub["work"])
            preview = work_text.split("\n")[0][:40]
            print(f"    \033[90m{name}: {rsub['bid']:.2f}¢, {rscore}/10, tokens={rtok:.3f}¢ — {preview}...\033[0m")


def display_scoreboard():
    global exchange_revenue
    print()
    print(f"  {'═' * 90}")
    print(f"  {'SCOREBOARD':^90}")
    print(f"  {'═' * 90}")
    print(f"  {'Model':<14s} {'W':>3s} {'L':>3s} {'P':>3s} "
          f"{'Revenue':>9s} {'TokenCost':>10s} {'Net P&L':>9s} {'Budget':>10s}")
    print(f"  {'─' * 90}")

    with budget_lock:
        for n in MODEL_NAMES:
            s = stats[n]
            b = budgets[n]
            ts = token_spend[n]
            rev = revenue[n]
            net = rev - ts
            elim = " \033[91m(OUT)\033[0m" if b < ELIMINATION_THRESHOLD else ""
            net_color = "\033[92m" if net >= 0 else "\033[91m"
            print(f"  {n:<14s} {s['wins']:>3d} {s['losses']:>3d} {s['passes']:>3d} "
                  f"{rev:>8.2f}¢ {ts:>9.2f}¢ {net_color}{net:>8.2f}¢\033[0m {b:>8.2f}¢{elim}")

    print(f"  {'─' * 90}")
    total_token = sum(token_spend.values())
    total_rev = sum(revenue.values())
    total_net = total_rev - total_token
    print(f"  Exchange revenue: {exchange_revenue:.2f}¢  |  "
          f"Total token cost: {total_token:.2f}¢  |  Total revenue: {total_rev:.2f}¢  |  "
          f"Net: {total_net:.2f}¢")
    print(f"  {'═' * 90}\n")


def run_round(round_num: int, task: str, buyer_price: float, min_score: int):
    # Filter to alive models
    alive = [n for n in MODEL_NAMES if budgets[n] >= ELIMINATION_THRESHOLD]
    state = RoundState(task, alive, buyer_price, min_score)

    # Mark eliminated
    for n in MODEL_NAMES:
        if n not in alive:
            state.log(f"{n}: eliminated")

    print(f"\n{'━' * 75}")
    print(f"  ROUND {round_num}/{len(TASK_QUEUE)} │ Buyer: {buyer_price:.1f}¢, score ≥ {min_score}/10")
    print(f"{'━' * 75}")
    print(f"  Task: {task}")
    budget_str = "  ".join(f"{n[:6]}={budgets[n]:.1f}¢" for n in alive)
    print(f"  Budgets: {budget_str}")
    print()

    threads = []
    for name in alive:
        t = threading.Thread(target=bidder_work,
                             args=(name, state, round_num), daemon=True)
        t.start()
        threads.append(t)

    judge_t = threading.Thread(target=judge_work, args=(state,), daemon=True)
    judge_t.start()

    last_events_len = 0
    while not state.done.is_set():
        render_tick(state)
        with state.lock:
            new_events = state.events[last_events_len:]
            last_events_len = len(state.events)
        if new_events:
            print()
            for ts, msg in new_events:
                print(f"  \033[90m[{ts:05.1f}s]\033[0m {msg}")
        state.done.wait(timeout=1.0)

    with state.lock:
        new_events = state.events[last_events_len:]
    if new_events:
        print()
        for ts, msg in new_events:
            print(f"  \033[90m[{ts:05.1f}s]\033[0m {msg}")

    for t in threads:
        t.join(timeout=5.0)
    judge_t.join(timeout=5.0)

    display_transaction(state)

    # Record history for future rounds' strategic context
    competitors = {}
    for n in state.models:
        sub = state.submissions.get(n)
        if sub and sub["compete"]:
            competitors[n] = sub["bid"]
        else:
            competitors[n] = "passed"

    round_history.append({
        "round": round_num,
        "task": task,
        "buyer_price": buyer_price,
        "min_score": min_score,
        "winner": state.winner,
        "winning_bid": state.submissions[state.winner]["bid"] if state.winner else 0,
        "scores": dict(state.scores),
        "competitors": competitors,
        "token_costs": dict(state.token_costs),
    })

    return state


def main():
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print(f"║  AI EXCHANGE — {len(MODEL_NAMES)} models, {STARTING_BUDGET_CENTS:.0f}¢ ($3) each, "
          f"{len(TASK_QUEUE)} tasks".ljust(78) + "║")
    print("║  " + ", ".join(MODEL_NAMES).ljust(76) + "║")
    print("║  Real token costs · Microcent bids · 20% spread fee                        ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")

    round_results = []
    for round_num, item in enumerate(TASK_QUEUE, 1):
        alive = [n for n in MODEL_NAMES if budgets[n] >= ELIMINATION_THRESHOLD]
        if len(alive) < 1:
            print("\n  All models eliminated!")
            break

        state = run_round(round_num, item["task"], item["buyer_price"], item["min_score"])
        round_results.append(state)

        # Show scoreboard every 5 rounds
        if round_num % 5 == 0 or round_num == len(TASK_QUEUE):
            display_scoreboard()

    # ── Final report ──────────────────────────────────────────────────
    print("\n" + "█" * 75)
    print("  FINAL STANDINGS")
    print("█" * 75)
    display_scoreboard()

    with budget_lock:
        best = max(MODEL_NAMES, key=lambda n: stats[n]["wins"])
        most_profitable = max(MODEL_NAMES,
                              key=lambda n: revenue[n] - token_spend[n])
        best_margin = max(MODEL_NAMES,
                          key=lambda n: (revenue[n] - token_spend[n]) / max(revenue[n], 0.01))
        print(f"  Most wins:      {best} — {stats[best]['wins']} wins")
        mp_net = revenue[most_profitable] - token_spend[most_profitable]
        print(f"  Most profitable: {most_profitable} — "
              f"{mp_net:.2f}¢ net profit ({revenue[most_profitable]:.2f}¢ rev − {token_spend[most_profitable]:.2f}¢ cost)")
        bm_rev = revenue[best_margin]
        bm_cost = token_spend[best_margin]
        bm_margin = (bm_rev - bm_cost) / max(bm_rev, 0.01) * 100
        print(f"  Best margin:    {best_margin} — "
              f"{bm_margin:.0f}% margin ({bm_rev:.2f}¢ rev − {bm_cost:.2f}¢ cost)")

    # ── Save transcript ───────────────────────────────────────────────
    transcript_path = Path(__file__).resolve().parent / "game_transcript.txt"
    with open(transcript_path, "w") as f:
        f.write("AI EXCHANGE — GAME TRANSCRIPT\n")
        f.write(f"Models: {', '.join(MODEL_NAMES)}\n")
        f.write(f"Starting budget: {STARTING_BUDGET_CENTS:.0f}¢ each\n")
        f.write(f"Tasks: {len(TASK_QUEUE)}\n\n")

        for i, state in enumerate(round_results, 1):
            f.write(f"{'=' * 70}\n")
            f.write(f"ROUND {i}: {state.task}\n")
            f.write(f"Buyer: {state.buyer_price:.2f}¢, min score: {state.min_score}/10\n")
            f.write(f"Result: {state.judge_action} — {state.judge_reasoning}\n")
            if state.winner:
                sub = state.submissions[state.winner]
                f.write(f"Winner: {state.winner} at {sub['bid']:.2f}¢ "
                        f"(score {state.scores.get(state.winner, '?')}/10, "
                        f"tokens {state.token_costs.get(state.winner, 0):.3f}¢)\n")
            for ts, msg in state.events:
                f.write(f"  [{ts:05.1f}s] {msg}\n")
            f.write("\n")

        f.write(f"\n{'=' * 70}\n")
        f.write("FINAL SCOREBOARD\n")
        f.write(f"{'Model':<14s} {'W':>3s} {'L':>3s} {'P':>3s} "
                f"{'Revenue':>9s} {'TokenCost':>10s} {'Net P&L':>9s} {'Budget':>10s}\n")
        for n in MODEL_NAMES:
            s = stats[n]
            net = revenue[n] - token_spend[n]
            f.write(f"{n:<14s} {s['wins']:>3d} {s['losses']:>3d} {s['passes']:>3d} "
                    f"{revenue[n]:>8.2f}¢ {token_spend[n]:>9.2f}¢ {net:>8.2f}¢ {budgets[n]:>8.2f}¢\n")
        f.write(f"\nExchange revenue: {exchange_revenue:.2f}¢\n")

    print(f"\n  Transcript saved to {transcript_path}")


if __name__ == "__main__":
    main()
