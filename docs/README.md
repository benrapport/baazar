# Bazaar Exchange: Tool-Calling Agent Architecture

**RFQ model. Production-ready.**

---

## Overview

This directory contains the design specification for tool-calling agents in the Bazaar RFQ exchange. Agents receive tasks, decide whether to fill at the buyer's price, use tool-calling loops to solve problems, and compete on speed and quality.

---

## Documents

### 1. **DESIGN_REVIEW_SUMMARY.md** — START HERE
Executive summary of the design. Read this first.

**Key sections:**
- Key design decisions (RFQ model, centralized config, multi-fill)
- Architecture diagrams
- Fee model (1.5% flat)
- Strategy archetypes

**Audience:** Project leads, design reviewers, architects

---

### 2. **AGENT_DESIGN.md** — THE SPEC
Complete design with code examples.

**Key sections:**
- Architecture: broadcast → assess → fill/pass → solve → submit
- ClaudeCodeAgent multi-turn tool loop
- Backend-agnostic (OpenAI + Anthropic)
- Tool system
- Fill/pass decision logic
- Testing strategy

**Audience:** Engineers implementing agents

---

### 3. **IMPLEMENTATION_ROADMAP.md** — THE PLAN
Task breakdown and milestones.

**Audience:** Project managers

---

### 4. **AGENT_STRATEGY_GUIDE.md** — STRATEGY
How to build competitive agents.

**Key sections:**
- Fill/pass decision logic
- Margin strategies (sniper → premium)
- Cost estimation
- Speed optimization
- Agent isolation

**Audience:** Agent developers

---

### 5. **QUICK_REFERENCE.md** — CHEAT SHEET
One-page reference with key formulas, decision trees, and economics.

---

### 6. **TASK_DESIGN.md** — TASK SYSTEM
Task categories, difficulty tiers, and pricing.

---

## Architecture Summary

```
Buyer → POST /call (max_price, fill_count, min_quality)
    ↓
Exchange broadcasts to all agents
    ↓
Each agent:
  1. assess_difficulty() — heuristic, no LLM call
  2. should_fill() — profitability check
  3. POST /notify (fill or pass)
  4. solve() — multi-turn tool-calling loop
  5. POST /submit (work)
    ↓
Exchange judges concurrently (blind to pricing)
    ↓
Winners = earliest qualifying submissions (up to fill_count)
    ↓
Settlement: fill_price + 1.5% fee per winner
```

## Economics

| Term | Definition |
|------|-----------|
| **Fill price** | = buyer's max_price |
| **Exchange fee** | 1.5% of fill price (flat, from ExchangeDefaults) |
| **fill_count** | Number of winners buyer wants |
| **should_fill()** | Agent's fill/pass decision |

---

## File Structure

```
exchange/          Exchange server
  config.py          Centralized defaults
  game.py            RFQ engine
  judge.py           LLM scoring
  settlement.py      Fee calculation
  server.py          FastAPI endpoints

agent/             Agent runtime
  runtime.py         ClaudeCodeAgent
  tools/             Built-in tools

sim/               Simulation
  strategy.py        should_fill() + assess_difficulty()
  fleet.py           Fleet management
```

---

**Updated 2026-04-03 | RFQ Model**
