# Exchangification: Tool-Calling Agent Architecture

**Design complete. Ready for implementation.**

---

## Overview

This directory contains the complete design specification for tool-calling agents in the Exchangification auction system. Agents are inspired by Claude Code's architecture: they receive tasks, use tool-calling loops to solve problems, and bid strategically in real-time auctions.

---

## Documents

### 1. **DESIGN_REVIEW_SUMMARY.md** ⭐ START HERE
Executive summary of the design. Read this first.

**Key sections:**
- Executive summary (2 min read)
- 6 critical design decisions with rationale
- Architecture diagrams
- Risk assessment
- Deployment checklist

**Audience:** Project leads, design reviewers, architects

---

### 2. **AGENT_DESIGN.md** 🏗️ THE SPEC
Complete, production-grade design with real Python code.

**Key sections:**
- Architecture: broadcast → route → bid → solve → submit
- 4 core classes: `ToolDefinition`, `ToolRegistry`, `BaseAgent`, `GameState`
- OpenAI implementation (`OpenAIAgent`)
- Anthropic implementation (`AnthropicAgent`)
- Tool execution sandbox
- Tool-calling loop algorithm
- Bidding formula (detailed)
- Testing strategy

**Audience:** Implementers, software engineers

**Length:** ~1000 lines of pseudocode + real Python

---

### 3. **IMPLEMENTATION_ROADMAP.md** 📅 THE PLAN
Detailed breakdown of implementation tasks by phase.

**Key sections:**
- Phase 1 (MVP): ToolRegistry, BaseAgent, OpenAI backend (16 hours)
- Phase 2 (Polish): Anthropic, stdlib tools, demo agents (24 hours)
- Day-by-day task breakdown
- Success criteria
- Risk mitigation

**Audience:** Project managers, implementers

---

### 4. **AGENT_STRATEGY_GUIDE.md** 🎯 FOR AGENT DEVELOPERS
Practical guide for agents to make strategic bidding decisions.

**Key sections:**
- The game: bidding tradeoffs
- Difficulty-based bidding (easy ❌ vs. hard ✓)
- Urgency premium (rushing costs money)
- Quality confidence (can you win?)
- Cost-based bidding (never bid below cost)
- Full bidding formula with 3 examples
- Learning from history
- Edge cases & gotchas
- Checklist before bidding

**Audience:** Agent developers, data scientists

---

## Architecture at a Glance

```python
# Agent receives broadcast
payload = {
    request_id: str,
    input: str,
    max_price: float,
    deadline_unix: float,
    min_quality: int,
}

# Agent processes in 4 steps
1. route_task(game_state)
   → Assess difficulty, pick model
   → Returns: {model, difficulty, uses_tools, estimated_cost}

2. _compute_bid(route, game_state)
   → difficulty_discount + urgency_premium
   → Returns: float (bid price in USD)

3. solve(game_state, route)
   → Tool-calling loop:
     a. Call LLM with available tools
     b. Parse response: content + tool_calls
     c. Execute tools (max 5s per tool)
     d. Add results to messages
     e. Repeat until LLM stops or deadline exceeded
   → Returns: str (final output)

4. submit({bid, work})
   → HTTP POST back to exchange
   → Exchange judges work + selects winner
```

---

## Class Diagram

```
┌─────────────────────────────────────────┐
│ ToolRegistry (1 per agent)              │
├─────────────────────────────────────────┤
│ - _tools: dict[name → ToolDefinition]   │
│ - _handlers: dict[name → Callable]      │
├─────────────────────────────────────────┤
│ + register(definition, handler)         │
│ + execute(tool_name, **kwargs) → str    │
│ + get_tools_for_model(backend) → list   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ GameState (1 per request)               │
├─────────────────────────────────────────┤
│ request_id, input, max_price, deadline  │
│ time_remaining_secs, quality_criteria   │
├─────────────────────────────────────────┤
│ + urgency_factor() → 0-1                │
│ + is_deadline_exceeded() → bool         │
└─────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ BaseAgent (abstract)                     │
├──────────────────────────────────────────┤
│ - tool_registry: ToolRegistry            │
│ - agent_id: str                          │
├──────────────────────────────────────────┤
│ + async handle_broadcast(payload)        │ ← entry point
│ + async route_task(game_state)           │ abstract
│ + get_system_prompt(route)               │ abstract
│ + async solve(game_state, route)         │ ← main loop
│ + async _call_llm(...)                   │ abstract
│ + _compute_bid(route, game_state)        │
└──────────────────────────────────────────┘
        △ △
        │ └─────────────────────────┐
        │                           │
   OpenAIAgent            AnthropicAgent
   (OpenAI API)           (Anthropic API)
```

---

## The Tool-Calling Loop

```python
async def solve(game_state: GameState, route: dict) -> str:
    messages = [{"role": "user", "content": game_state.input}]

    for iteration in range(10):  # max iterations
        if game_state.is_deadline_exceeded():
            break

        response = await _call_llm(
            model=route["model"],
            system=get_system_prompt(route),
            messages=messages,
            tools=route["uses_tools"],
        )

        # Check if done
        if response.get("stop_reason") == "end_turn":
            return response["content"]

        # Execute tools
        tool_calls = response.get("tool_calls", [])
        if not tool_calls:
            return response["content"]

        tool_results = [
            await _execute_tool(tc, game_state)
            for tc in tool_calls
        ]

        # Add to message history and repeat
        messages.append({"role": "assistant", "content": response["content"]})
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "content": result}
            for result in tool_results
        ]})

    return messages[-1].get("content", "")
```

---

## Bidding Formula

```python
def _compute_bid(route: dict, game_state: GameState) -> float:
    """Three-factor bidding formula."""

    difficulty = route["difficulty"]           # 0-1
    cost = route["estimated_cost"]             # USD

    # Factor 1: Difficulty
    difficulty_discount = difficulty * 0.4    # 0-40%
    base_bid = game_state.max_price * (1.0 - difficulty_discount)

    # Factor 2: Urgency
    urgency = game_state.urgency_factor()      # 0-1
    urgency_premium = urgency * game_state.max_price * 0.15  # 0-15%

    # Combine
    final_bid = base_bid + (urgency_premium * game_state.max_price)

    # Floors & ceilings
    final_bid = max(final_bid, cost)           # never below cost
    final_bid = min(final_bid, game_state.max_price * 0.99)  # exchange fee

    return final_bid
```

---

## File Organization

```
agentx/
├── tools/
│   ├── definitions.py         # ToolDefinition, ToolRegistry
│   ├── executor.py            # CodeExecutor sandbox
│   └── stdlib.py              # web_search, execute_python, extract_json
├── agents/
│   ├── base.py                # BaseAgent, GameState (abstract)
│   ├── openai_agent.py        # OpenAIAgent (concrete)
│   └── anthropic_agent.py     # AnthropicAgent (concrete)
└── provider.py                # AgentProvider (updated)

demo/
├── agents/
│   ├── researcher_agent.py    # Example: uses web_search
│   ├── analyst_agent.py       # Example: uses extract_json
│   └── writer_agent.py        # Example: minimal tools

tests/
├── test_tools.py              # ToolRegistry, tool execution
├── test_agent_loop.py         # Mocked LLM, tool-calling loop
├── test_routing.py            # route_task behavior
├── test_bidding.py            # bid formula edge cases
└── test_integration.py        # full broadcast → submit
```

---

## Key Design Decisions

| Decision | What | Why |
|----------|------|-----|
| **Bidding before solving** | Bid price decided during routing, before solve | Agent commits early; enables parallel competition |
| **Shared tool registry** | All agents get same tools | Fair competition; no exclusive capabilities |
| **Backend-agnostic** | BaseAgent works with OpenAI + Anthropic | Easy to add Claude, Gemini, etc. |
| **GameState object** | Encapsulates auction context | Single source of truth; extensible |
| **Three-factor bidding** | difficulty + urgency + cost | Rational equilibrium; agents don't lose money |
| **10-iteration max** | Bounded tool-calling loop | Prevents runaway; guarantees termination |

---

## Testing Strategy

### Unit Tests
- ToolRegistry: register, execute, format
- GameState: urgency_factor, is_deadline_exceeded
- Bidding: _compute_bid with varied inputs

### Integration Tests
- Mock LLM: fixed tool_calls, verify loop executes N iterations
- Real API: OpenAI + Anthropic with VCR cassettes

### E2E Tests
- 3 demo agents + live exchange
- Verify winners are qualifiers (score ≥ min_quality)
- Verify bids respect fee structure

---

## Deployment Timeline

**Phase 1 (MVP):** 16 hours (by April 2)
- ToolRegistry + stdlib tools
- BaseAgent + tool-calling loop
- OpenAI backend
- Basic tests

**Phase 2 (Polish):** 12 hours (by April 4)
- Anthropic backend
- Demo agents
- Comprehensive tests
- Documentation

**Live:** April 5 (test with real exchange)
**Production:** April 7

---

## FAQ

**Q: Why not implement in LangChain/LlamaIndex?**
A: Those are application frameworks. We need production agent architecture with game-theory aware bidding. Building from scratch gives us control + understanding.

**Q: What if an agent's tools take too long?**
A: Tool execution has 5s timeout per tool. If exceeded, LLM gets error message, adapts strategy. Agent doesn't halt.

**Q: How do agents learn to specialize?**
A: By tracking history (win rate by task type) and adjusting bidding. Phase 2 will include historical analytics.

**Q: Can agents see other agents' bids?**
A: No (hidden information). This makes game-theory cleaner and prevents collusion.

**Q: Why not use Claude Code as the agent?**
A: Claude Code is a UI framework. We need a scalable agent class that can run 100s of parallel instances in an auction.

---

## References

### External
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic Tool Use](https://docs.anthropic.com/en/docs/build-a-bot/tool-use)
- [Auction Theory (Vickrey)](https://en.wikipedia.org/wiki/Vickrey_auction)

### Internal
- `exchange/game.py` — How exchange runs auctions
- `exchange/settlement.py` — Fee structure (20% spread, $0.01 cap)
- `agentx/provider.py` — SDK for agents (will be updated)

---

## Contact

**Design by:** Thinker 9 (Design Specialist)
**Date:** 2026-03-31
**Status:** Approved for implementation

Questions? See DESIGN_REVIEW_SUMMARY.md § "Open Questions & Future Work"
