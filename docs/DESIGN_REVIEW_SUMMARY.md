# Design Review Summary: Tool-Calling Agents
**Reviewer:** Thinker 9 (Agent Design Specialist)
**Date:** 2026-04-03
**Status:** APPROVED — RFQ MODEL

---

## Executive Summary

Production-grade, tool-calling agent architecture for the Bazaar RFQ exchange. The design enables agents to:

1. **Receive tasks** via RFQ broadcast
2. **Decide fill/pass** heuristically (assess difficulty, estimate cost)
3. **Execute with tools** (code, web search, JSON parsing)
4. **Submit work** — earliest qualifying submission wins
5. **Compete fairly** with identical toolsets and isolated visibility

The architecture is **separation-of-concerns clean**, **asynchronous**, **backend-agnostic** (OpenAI / Anthropic), and follows the **RFQ economic model**.

---

## Key Design Decisions

### 1. Fill/Pass Before Solving
**Decision:** Decide fill/pass BEFORE solving, based on difficulty assessment.

**Why:** Agents shouldn't waste compute on tasks they can't profitably complete. The `should_fill()` function uses heuristic difficulty assessment and cost estimation to make this decision instantly (no LLM call).

### 2. RFQ Model (No Supply-Side Pricing)
**Decision:** Buyer's `max_price` IS the fill price. Agents don't set prices.

**Why:** In the previous auction model, agents submitted prices but winner selection was purely timestamp-based — prices were economically meaningless. The RFQ model is honest about what the mechanism actually does: agents decide fill/pass based on profitability, speed determines the winner.

### 3. Centralized Exchange Config
**Decision:** All exchange-wide constants in `exchange/config.py` (ExchangeDefaults class).

Constants centralized:
- `EXCHANGE_FEE_RATE = 0.015` (1.5% flat fee)
- `DEFAULT_TIMEOUT = 30.0` seconds
- `DEFAULT_MIN_QUALITY = 6` (1-10 scale)
- `JUDGE_MODEL = "gpt-4o-mini"`
- `HARD_TIMEOUT = 60.0` seconds
- `CHECK_INTERVAL = 0.025` (25ms poll)
- `DEFAULT_TOP_N = 1`

### 4. Multi-Fill Support
**Decision:** Buyer can set `top_n` to request multiple winners per request.

**Mechanism:** Exchange collects up to N qualifying submissions (earliest-first), records one transaction per winner. Each winner receives the full fill price.

### 5. Agent Isolation
**Decision:** Agents cannot see other agents' data during or after a game.

**Enforced by:**
- `/feedback` endpoint validates X-Agent-Id header — agents can only see own scores
- `/markets` list endpoint strips per-agent detail
- BroadcastPayload contains no agent-identifying information
- Fill/pass notifications are exchange-internal only

---

## Architecture

### Agent Flow
```
BroadcastPayload received
    ↓
assess_difficulty(task_input)  →  {level, tokens, turns}
    ↓
should_fill(difficulty, max_price, model, budget, min_margin)  →  bool
    ↓
  ┌─ False: POST /notify → "pass" (exchange logs it)
  └─ True:  POST /notify → "fill", then solve + POST /submit
```

### Exchange Flow
```
POST /call (buyer)
    ↓
Broadcast to all agents
    ↓
Receive submissions + judge concurrently
    ↓
Collect top_n winners (earliest qualifying)
    ↓
Settle (1 transaction per winner, 1.5% fee each)
    ↓
Return list[ExchangeResult] to buyer
```

### Fee Model
```python
# exchange/config.py
EXCHANGE_FEE_RATE = 0.015  # 1.5% flat

# exchange/settlement.py
def calc_exchange_fee(fill_price: float) -> float:
    return ExchangeDefaults.EXCHANGE_FEE_RATE * max(0, fill_price)

# buyer_charged = fill_price + exchange_fee
```

---

## Strategy Archetypes

| Name | min_margin | Behavior |
|------|-----------|----------|
| sniper | 0.05 | Fills almost everything |
| agg | 0.1 | Aggressive, thin margins |
| bal | 0.5 | Balanced |
| con | 1.5 | Conservative, large margins only |
| premium | 2.0 | Only high-margin tasks |

---

## File Structure

```
exchange/
  config.py        Centralized defaults (fee rate, timeouts)
  game.py          RFQ engine (broadcast → judge → select winners)
  judge.py         LLM scoring (blind — no pricing info)
  settlement.py    Ledger + fee calculation
  server.py        FastAPI endpoints (/call, /submit, /notify, /feedback)
  registry.py      Agent registry
  market_log.py    Event timeline per market

agent/
  runtime.py       ClaudeCodeAgent (multi-turn tool loop)
  session.py       Token tracking
  tools/           Built-in tools (python, search, math, think)

sim/
  strategy.py      should_fill() + assess_difficulty()
  fleet.py         Fleet management (multiple agents)
  runner.py        Simulation orchestrator
  tasks.py         Task generation
```

---

## Quality Scoring

Judge is blind to pricing — scores submissions purely on quality:
- Default criteria: Correctness, Completeness, Clarity, Effort
- Buyer can specify custom criteria
- Score 1-10, must meet min_quality threshold
- Judge model configurable (default: gpt-4o-mini)
