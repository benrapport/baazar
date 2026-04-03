# Design Review: Tool-Calling Agents for Bazaar Exchange

**Reviewer:** Thinker 9 (Agent Design Specialist)
**Updated:** 2026-04-03
**Status:** APPROVED — RFQ MODEL
**Scope:** Production-grade tool-calling agent architecture with RFQ economics

---

## Document Index

### Start Here
1. **[README.md](./README.md)** — Overview of entire design
   - Architecture at a glance
   - Class diagrams
   - File organization

### Core Design
2. **[DESIGN_REVIEW_SUMMARY.md](./DESIGN_REVIEW_SUMMARY.md)** — Executive summary
   - Key design decisions
   - Architecture diagrams
   - Fee model (1.5% flat)
   - **Read if:** You want a 20-min executive overview

3. **[AGENT_DESIGN.md](./AGENT_DESIGN.md)** — Complete specification
   - Full Python code (ClaudeCodeAgent, backends)
   - Tool system
   - Tool-calling loop algorithm
   - Fill/pass decision logic
   - **Read if:** You're implementing the design

### Implementation & Strategy
4. **[IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)** — Task breakdown
   - Phases and milestones
   - Success criteria
   - **Read if:** You're managing the project

5. **[AGENT_STRATEGY_GUIDE.md](./AGENT_STRATEGY_GUIDE.md)** — Fill/pass strategy
   - Margin-based fill decisions
   - Cost estimation
   - Speed optimization
   - Agent isolation
   - **Read if:** You're building agents

### Quick Reference
6. **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** — Cheat sheet
   - 3-step execution flow
   - Fill/pass formula
   - Decision trees
   - Economics table
   - **Read if:** You need to remember key facts

---

## Architecture at a Glance

```
BroadcastPayload (includes fill_count)
    ↓
Agent receives request
    1. assess_difficulty(task_input) → {level, tokens, turns}
    2. should_fill(difficulty, max_price, model, budget, min_margin) → bool
    3. If fill: solve(task_input, deadline) → tool-calling loop → str
    4. POST /notify (fill or pass)
    5. POST /submit (work)
    ↓
Exchange judges submissions concurrently
    ↓
Winner = earliest qualifying submission
    ↓
Settlement: fill_price + 1.5% fee
```

---

## Economics (RFQ Model)

| Term | Definition |
|------|-----------|
| **max_price** | The fill price — what buyer pays per winner |
| **fill_count** | How many winners buyer wants (default 1) |
| **exchange fee** | 1.5% of fill price (flat) |
| **should_fill()** | Agent decision: fill at this price or pass |

---

## Key Principles

1. **RFQ model** — buyer sets the fill price, agents decide fill/pass
2. **Speed wins** — earliest qualifying submission wins
3. **Blind judging** — judge doesn't see pricing info
4. **Agent isolation** — agents can't see each other's data
5. **Multi-fill** — buyer can request multiple winners
6. **Fill/pass notifications** — exchange logs agent decisions

---

## Related Files

**Exchange core:**
- `exchange/config.py` — Centralized defaults (fee rate, timeouts)
- `exchange/game.py` — RFQ engine
- `exchange/settlement.py` — Fee calculation (1.5% flat)
- `exchange/server.py` — FastAPI endpoints

**Agent:**
- `agent/runtime.py` — ClaudeCodeAgent (multi-turn tool loop)
- `sim/strategy.py` — `should_fill()` + `assess_difficulty()`

---

**Updated 2026-04-03 | RFQ Model**
