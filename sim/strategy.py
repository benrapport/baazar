"""Bidding strategy for tool-calling agents.

Agents must decide:
1. Should I compete on this task?
2. If yes, what bid?
"""

from constants.models import Model, MODEL_COSTS


def assess_difficulty(task_input: str) -> dict:
    """Quick heuristic difficulty assessment. No LLM call — must be fast.

    Args:
        task_input: The task description/input to assess.

    Returns:
        {
            "level": "easy" | "medium" | "hard" | "extreme",
            "estimated_turns": int,
            "estimated_tokens": int,
            "confidence": float,  # 0.0-1.0 how confident we are in assessment
        }

    Heuristics:
    - Input length: <200 chars = likely easy, >2000 = likely hard
    - Keywords that signal difficulty:
      - Easy: "write", "list", "simple", "basic"
      - Hard: "debug", "optimize", "prove", "analyze", "design system"
      - Extreme: "multi-step", "implement from scratch", "complex algorithm"
    - Presence of code blocks (```) = likely debugging/code task
    - Presence of data/numbers = likely data analysis
    - Multiple questions/requirements = harder
    """
    length = len(task_input)
    code_blocks = task_input.count("```")
    num_questions = task_input.count("?")

    # Easy keywords
    easy_keywords = {"write", "list", "simple", "basic", "summarize", "explain"}
    # Hard keywords
    hard_keywords = {"debug", "optimize", "prove", "analyze", "design", "implement", "fix"}
    # Extreme keywords
    extreme_keywords = {"multi-step", "from scratch", "complex algorithm", "architecture", "system design"}

    task_lower = task_input.lower()
    easy_count = sum(1 for kw in easy_keywords if kw in task_lower)
    hard_count = sum(1 for kw in hard_keywords if kw in task_lower)
    extreme_count = sum(1 for kw in extreme_keywords if kw in task_lower)

    # Determine difficulty level
    level = "easy"
    estimated_turns = 1
    estimated_tokens = 200
    confidence = 0.7

    if extreme_count > 0:
        level = "extreme"
        estimated_turns = 8
        estimated_tokens = 3000
        confidence = 0.8
    elif hard_count > 0:
        level = "hard"
        estimated_turns = 5
        estimated_tokens = 1500
        confidence = 0.75
    elif length > 2000 or code_blocks > 0 or num_questions > 2:
        level = "medium"
        estimated_turns = 3
        estimated_tokens = 800
        confidence = 0.65
    elif easy_count > 0:
        level = "easy"
        estimated_turns = 1
        estimated_tokens = 200
        confidence = 0.8
    elif length > 500:
        level = "medium"
        estimated_turns = 2
        estimated_tokens = 500
        confidence = 0.6

    return {
        "level": level,
        "estimated_turns": estimated_turns,
        "estimated_tokens": estimated_tokens,
        "confidence": confidence,
    }


def compute_bid(
    difficulty: dict,
    max_price: float,
    model: Model,
    budget_remaining_cents: float,
) -> float | None:
    """Compute bid price in USD. Returns None if agent should pass.

    Args:
        difficulty: Output from assess_difficulty()
        max_price: Maximum price buyer is willing to pay (in USD)
        model: Model the agent would use
        budget_remaining_cents: Remaining budget in cents

    Returns:
        Bid in USD, or None to pass.

    Rules:
    - Estimated cost = estimated_tokens * model cost rate
    - Minimum bid = estimated_cost * 1.2 (20% margin)
    - Maximum bid = max_price * 0.8 (leave room for exchange fee)
    - If min_bid > max_bid: return None (can't profitably compete)
    - Cheap models (gpt-4o-mini) bid lower on easy tasks
    - Expensive models only compete on hard+ tasks where they have quality advantage
    - If budget_remaining_cents < estimated_cost: return None
    """
    # Get model costs (input, output per million tokens)
    input_cost_per_m, output_cost_per_m = MODEL_COSTS[model]

    # Assume roughly 20% input, 80% output token split on average
    avg_cost_per_token = (input_cost_per_m * 0.2 + output_cost_per_m * 0.8) / 1_000_000
    estimated_tokens = difficulty["estimated_tokens"]
    estimated_cost_usd = estimated_tokens * avg_cost_per_token
    estimated_cost_cents = estimated_cost_usd * 100

    # Check budget
    if budget_remaining_cents < estimated_cost_cents:
        return None

    # Calculate min and max bids
    min_bid = estimated_cost_usd * 1.2
    max_bid = max_price * 0.8

    # Can't profitably compete
    if min_bid > max_bid:
        return None

    difficulty_level = difficulty["level"]

    # Cheap models bid aggressively on easy tasks
    if model in (Model.GPT_4O_MINI, Model.GPT_5_4_NANO):
        if difficulty_level == "easy":
            bid = min(max_bid, min_bid + (max_bid - min_bid) * 0.3)
        elif difficulty_level == "medium":
            bid = min(max_bid, min_bid + (max_bid - min_bid) * 0.1)
        else:
            # Don't bid on hard/extreme with cheap models
            return None
    # Expensive models skip easy tasks, compete on medium+ with quality advantage
    elif model in (Model.GPT_4O, Model.GPT_4_1, Model.O4_MINI, Model.CLAUDE_SONNET):
        if difficulty_level == "easy":
            return None
        elif difficulty_level == "medium":
            bid = min(max_bid, min_bid + (max_bid - min_bid) * 0.5)
        else:
            bid = min(max_bid, min_bid + (max_bid - min_bid) * 0.4)
    # Mid-range models bid balanced
    else:
        if difficulty_level == "easy":
            bid = min(max_bid, min_bid + (max_bid - min_bid) * 0.2)
        elif difficulty_level == "medium":
            bid = min(max_bid, min_bid + (max_bid - min_bid) * 0.3)
        else:
            bid = min(max_bid, min_bid + (max_bid - min_bid) * 0.5)

    return round(bid, 4)
