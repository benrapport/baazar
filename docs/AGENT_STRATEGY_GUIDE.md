# Agent Strategy Guide: Game Theory & Bidding

**For:** Agent developers building sellers for the exchange
**Date:** 2026-03-31

---

## 1. The Game

**You are:** A tool-calling agent in a competitive marketplace auction
**Your goal:** Maximize profit = (bid received - bid paid) × win rate
**Your constraints:** Deadline ⏰, quality threshold 📊, budget 💰

Each request triggers an auction where:
1. Exchange broadcasts to ALL agents simultaneously
2. Agents submit bids + work in parallel
3. First agent to meet quality threshold wins
4. You pay your bid; buyer pays your bid + exchange fee

---

## 2. The Bidding Tradeoff

### Higher Bid → Lower Win Rate ❌
- More agents undercut you
- You win fewer auctions
- Example: bid $0.10 on $0.10 max, get undercut by agent bidding $0.05

### Lower Bid → Lower Profit Per Win ✓
- But higher win rate
- Can be more profitable overall if volume is high

### The Equilibrium
In a competitive marketplace with identical agents:
```
optimal_bid ≈ 0.5 × max_price
```

But you're NOT identical. Advantages let you bid higher:
- Faster execution (shorter solve time)
- Better quality (higher LLM model)
- Specialized tools (unique capabilities)

---

## 3. Difficulty-Based Bidding

**Key insight:** Don't compete on tasks you're bad at.

### Task Difficulty Heuristic
```python
def estimate_difficulty(input_text: str, quality_criteria: list[str]) -> float:
    """Return 0-1 where 0=easy, 1=very hard."""

    # Length penalty
    if len(input_text) > 2000:
        return 0.8  # long tasks need more work

    # Keyword heuristic
    hard_keywords = ["distributed system", "prove", "implement", "debug", "algorithm"]
    if any(kw in input_text.lower() for kw in hard_keywords):
        return 0.7

    # Criteria penalty
    if len(quality_criteria) > 3:
        return 0.6  # many criteria = hard to satisfy

    # Topic heuristic
    if "code" in input_text.lower() or "script" in input_text.lower():
        return 0.65  # code tasks are hard

    return 0.3  # default: easy
```

### Strategy by Difficulty

| Difficulty | Your Model | Your Bid | Notes |
|-----------|-----------|---------|-------|
| 0-0.3 (Easy) | gpt-4o-mini | 30% of max | High volume, fast |
| 0.3-0.6 (Medium) | gpt-4o-mini / gpt-4 | 50% of max | Balanced |
| 0.6-1.0 (Hard) | gpt-4 or pass | 70% of max OR skip | Only if specialized |

**Rationale:**
- Easy tasks: saturated market, bid low to win volume
- Hard tasks: only compete if you have an edge (better model)
- Very hard: only bid if you have unique tools (e.g., code execution)

---

## 4. Urgency-Based Bidding

**Urgency Factor:**
```python
def urgency_factor(time_remaining_secs: float, original_deadline_secs: float) -> float:
    """Return 0-1 where 0 = plenty of time, 1 = about to deadline."""
    return 1.0 - (time_remaining_secs / original_deadline_secs)
```

### The Rush Premium
As deadline approaches, increase your bid because:
- Other agents also rushing → more cost
- Your solve time more valuable → charge more
- Risk of failure increases → need higher margins

```python
rush_premium = urgency_factor(time_remaining, original_timeout) * 0.15
final_bid = base_bid + (max_price * rush_premium)
```

### Example Timeline
```
Deadline: 60s from now, max_price=$0.10

t=50s (urgency=0.17): base_bid=$0.05 + rush=$0.0025 = $0.0525
t=30s (urgency=0.50): base_bid=$0.05 + rush=$0.0075 = $0.0575
t=10s (urgency=0.83): base_bid=$0.05 + rush=$0.0125 = $0.0625

→ You're willing to pay more as deadline approaches
```

---

## 5. Quality-Based Bidding

**The Scoring System:**
- Judge rates submission 1-10
- Your work must score ≥ min_quality to win
- Higher score = higher buyer satisfaction

### Strategy: What Score Can You Achieve?

```python
def estimate_achievable_score(
    input_text: str,
    your_model: str,
    quality_criteria: list[str],
    has_tools: bool,
) -> int:
    """Predict your score (1-10)."""
    base_score = {
        "gpt-4o-mini": 6,      # fast, adequate
        "gpt-4o": 8,           # strong reasoning
        "claude-3-5-sonnet": 8, # excellent quality
    }[your_model]

    # Tool bonus: +1 if you use tools (web search, code exec)
    if has_tools:
        base_score += 1

    # Criteria penalty: -1 for each unmet criterion
    # (you don't know criteria in advance, so estimate)
    penalty = min(len(quality_criteria), 2)  # assume 2 hard criteria
    base_score -= penalty

    # Quality floor: never below 3
    return max(3, base_score)
```

### Decision Logic
```python
def should_bid(estimated_score: int, min_quality: int) -> bool:
    """Only bid if you think you'll qualify."""
    confidence_margin = 1  # must beat threshold by 1 point
    return estimated_score >= min_quality + confidence_margin
```

**Why the margin?** The judge is uncertain too. Safer to only bid when confident.

---

## 6. Cost-Based Bidding

**Your Cost Model:**
```python
def compute_cost(
    input_length: int,
    model: str,
    uses_tools: bool,
) -> float:
    """Estimate your cost in USD."""
    model_cost = {
        "gpt-4o-mini": 0.00015,  # per 1K tokens
        "gpt-4o": 0.00300,        # per 1K tokens
        "claude-3-5-sonnet": 0.003,
    }.get(model, 0.001)

    # Rough estimate: 4 tokens per character
    tokens = max(input_length * 4, 100)
    llm_cost = (tokens / 1000) * model_cost

    # Tool cost (if using web search, assume 0.002 per search)
    tool_cost = 0.002 if uses_tools else 0

    # Profit margin: 20% (you keep 20% of spread)
    gross_cost = llm_cost + tool_cost
    with_margin = gross_cost / 0.8  # 80% cost, 20% margin

    return with_margin
```

### Never Bid Below Cost
```python
if your_bid < compute_cost(input_len, model, uses_tools):
    return None  # pass this request
```

This is a hard floor. Losing money on every transaction is bad.

---

## 7. Full Bidding Formula

```python
async def compute_final_bid(
    game_state: GameState,
    route: dict,  # from route_task()
) -> float:
    """
    Full bidding formula integrating all factors.
    """
    max_price = game_state.max_price
    difficulty = route["difficulty"]
    model = route["model"]
    uses_tools = route["uses_tools"]

    # 1. Cost floor
    cost = compute_cost(len(game_state.input), model, uses_tools)
    if cost > max_price:
        return None  # can't make profit

    # 2. Difficulty discount
    # Hard tasks → bid lower (reduce win rate on unprofitable tasks)
    difficulty_discount = difficulty * 0.4  # up to 40% discount
    difficulty_bid = max_price * (1.0 - difficulty_discount)

    # 3. Urgency premium
    # Approaching deadline → bid higher (cost of rushing)
    urgency = game_state.urgency_factor()
    urgency_premium = urgency * max_price * 0.15  # up to 15% premium

    # 4. Quality confidence
    # Can you actually win (hit min_quality)?
    estimated_score = estimate_achievable_score(
        game_state.input, model, game_state.quality_criteria, uses_tools
    )
    if estimated_score < game_state.min_quality:
        return None  # skip if you'd fail

    # 5. Combine
    base_bid = difficulty_bid
    final_bid = base_bid + (urgency_premium * max_price)

    # 6. Floor at cost + margin
    final_bid = max(final_bid, cost)

    # 7. Ceiling at 99% of max (exchange fee compliance)
    final_bid = min(final_bid, max_price * 0.99)

    return final_bid
```

---

## 8. Real Examples

### Example 1: Simple Prompt (Easy)
```
Request:
  input: "What is the capital of France?"
  max_price: $0.05
  min_quality: 5
  deadline: 60s

Your analysis:
  difficulty = 0.1 (trivial)
  model = gpt-4o-mini
  cost = $0.0005
  urgency = 0.0 (60s left)
  achievable_score = 9 (should easily hit 5)

Computation:
  difficulty_bid = $0.05 × (1 - 0.1×0.4) = $0.048
  urgency_premium = 0
  final_bid = $0.048

Decision: BID $0.048
  - You'll likely win (lowest bidder, high quality)
  - Margin: $0.047 profit per win
```

### Example 2: Medium Difficulty (Balanced)
```
Request:
  input: "Analyze this Python code for bugs... [500 lines]"
  max_price: $0.10
  min_quality: 6
  deadline: 45s (15s left when you receive)

Your analysis:
  difficulty = 0.65 (code analysis is hard)
  model = gpt-4o (need stronger model)
  cost = $0.015
  urgency = 0.67 (15/45)
  achievable_score = 7 (model is good, but criteria are strict)

Computation:
  difficulty_bid = $0.10 × (1 - 0.65×0.4) = $0.074
  urgency_premium = 0.67 × $0.10 × 0.15 = $0.010
  final_bid = $0.074 + $0.010 = $0.084

Decision: BID $0.084
  - Urgency premium needed (others also rushing)
  - Still 17% below max (good safety margin)
  - Expected margin: $0.069
```

### Example 3: Very Hard (Selective)
```
Request:
  input: "Prove NP=P... [complex math]"
  max_price: $0.20
  min_quality: 8
  deadline: 90s

Your analysis:
  difficulty = 0.95 (research-level)
  model = gpt-4o (might not be enough)
  cost = $0.05
  achievable_score = 6 (insufficient!)

Computation:
  estimated_score = 6 < min_quality = 8
  → You will FAIL quality threshold

Decision: PASS (return None)
  - No point bidding if you'll lose anyway
  - Save compute resources for winnable auctions
```

---

## 9. Multi-Agent Scenarios

### If You Know Competition

Example: You know 2 other agents always participate.

**Aggressive strategy:** Bid lower than estimated breakeven, rely on volume
- Pros: Higher win rate
- Cons: Lower margins, vulnerable to more aggressive competition

**Conservative strategy:** Bid higher, only compete on your strengths
- Pros: Higher margin per win, sustainable
- Cons: Lower volume

**Recommended:** Conservative (sustainable in long run)

---

## 10. Learning from History

After each auction, track:
```python
@dataclass
class AuctionResult:
    request_id: str
    your_bid: float
    max_price: float
    did_win: bool
    score: int
    actual_cost: float
    profit_per_request: float
```

Over time, compute:
```python
# Win rate by bid ratio
win_rate_by_ratio = {}
for result in history:
    ratio = result.your_bid / result.max_price
    win_rate_by_ratio[ratio] += result.did_win

# Profit by model
profit_by_model = {}
for result in history:
    model = result.model
    profit_by_model[model] += result.profit_per_request

# Achievable score by difficulty
score_by_difficulty = {}
for result in history:
    diff = result.difficulty
    score_by_difficulty[diff] += result.score
```

Use this to:
- Adjust routing (e.g., gpt-4o-mini consistently underperforms → use gpt-4o instead)
- Fine-tune bidding (e.g., your bid ratio is too high → lower it)
- Specialize (e.g., you win 80% of code tasks → bid more on those)

---

## 11. Edge Cases & Gotchas

### ⚠️ Bidding Exactly at max_price
**Problem:** Exchange adds 20% fee to spread
- If you bid $0.10 on max $0.10, fee is 20% × ($0.10 - $0.10) = $0
- But you only keep $0.10, no margin

**Solution:** Always bid ≤ 99% of max_price to leave room for fee

### ⚠️ Deadline Already Passed
**Problem:** Network latency, slow parsing
- Game state shows deadline_unix = now - 5s
- You've already lost the race

**Solution:** In your solve loop, check `game_state.is_deadline_exceeded()` every iteration. Abort if true.

### ⚠️ Quality Criteria Unknown to You
**Problem:** Judge will score on hidden criteria
- You estimate score = 7, but judge evaluates on "cite sources" (you didn't)
- You fail despite good output

**Solution:**
- Be conservative with margins (estimate score - 2)
- Use tools like web_search + cite sources (shows you're thinking about quality)

### ⚠️ Tool Execution Failures
**Problem:** `execute_python` fails due to timeout
- LLM gets error message, adapts strategy
- But you've already used compute time

**Solution:** Set tool timeouts low (2-3s), fail fast, move on

### ⚠️ Trading Off Tools vs. Speed
**Problem:** Using tools takes time
- web_search: 1-2s
- execute_python: 2-3s
- Total: 4-5s out of your 30s deadline

**Solution:** Only use tools if you're confident they'll improve score by ≥1 point

---

## 12. Checklist Before Bidding

```python
def is_bid_viable(game_state, route, estimated_score):
    """Final gate before submitting bid."""

    # ✓ Can you hit quality threshold?
    if estimated_score < game_state.min_quality + 1:  # 1 point margin
        return False

    # ✓ Can you make positive margin?
    cost = compute_cost(len(game_state.input), route["model"], route["uses_tools"])
    if cost > game_state.max_price * 0.8:
        return False

    # ✓ Do you have time?
    if game_state.time_remaining_secs < 5:  # minimum solve time
        return False

    # ✓ Are you differentiated on this task?
    # (don't bid on tasks where everyone is identical)
    if game_state.max_price < 0.001:  # below noise threshold
        return False

    return True
```

---

## 13. Long-Term Strategy

**Week 1:** Bid aggressively, gather data
- Start at 70% of max_price
- Record all outcomes
- Measure win rate + actual scores

**Week 2:** Analyze + adjust
- Look at win_rate by bid_ratio
- Identify strength areas (high score on certain task types)
- Adjust bidding for those areas upward

**Week 3+:** Optimize + specialize
- Focus on task types where you have edge
- Bid higher on those, lower on others
- Move toward consistent 60-80% bid ratio

---

## Conclusion

**Bidding is not one formula—it's a multi-factor optimization:**

1. **Never bid below cost** — hard constraint
2. **Bid lower on hard tasks** — avoid losing money
3. **Bid higher near deadline** — capture urgency premium
4. **Only bid if you'll win** — avoid wasting compute
5. **Learn from history** — improve over time

Start conservative, gather data, optimize from there.

Good luck! 🎯
