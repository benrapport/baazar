# Quick Reference: Tool-Calling Agent Design

**Print this. Pin to your monitor.**

---

## Entry Point

```python
# Agent receives this from exchange
@dataclass
class BroadcastPayload:
    request_id: str
    input: str
    max_price: float
    min_quality: int
    deadline_unix: float
    quality_criteria: list[str]

# Agent returns this
@dataclass
class SubmissionPayload:
    bid: float  # USD
    work: str   # task output
```

---

## 4-Step Execution

```python
class BaseAgent:
    async def handle_broadcast(payload):
        # 1. Parse
        game_state = GameState(...)

        # 2. Route
        route = await self.route_task(game_state)
        # → {model, difficulty, uses_tools, estimated_cost}

        # 3. Bid
        bid = self._compute_bid(route, game_state)

        # 4. Solve
        work = await self.solve(game_state, route)

        # 5. Submit
        return {"bid": bid, "work": work}
```

---

## Tool-Calling Loop

```python
async def solve(game_state, route):
    messages = [{"role": "user", "content": game_state.input}]

    for i in range(10):
        if game_state.is_deadline_exceeded():
            break

        response = await self._call_llm(..., tools=True)
        if not response["tool_calls"]:
            return response["content"]

        for tc in response["tool_calls"]:
            result = await self._execute_tool(tc, game_state)
            messages.append(result)

        messages.append({"role": "assistant", ...})

    return messages[-1]["content"]
```

---

## Bidding Formula (One Liner)

```python
bid = max_price × (1 - difficulty×0.4) + max_price × urgency×0.15
bid = max(bid, cost_estimate)  # floor
bid = min(bid, max_price×0.99)  # ceiling
```

### Factors

| Factor | Effect | Range |
|--------|--------|-------|
| **Difficulty** | Hard tasks → lower bid | 0-40% discount |
| **Urgency** | Deadline near → higher bid | 0-15% premium |
| **Cost** | Never bid below cost | hard floor |
| **Fee compliance** | Must leave room for fee | 99% of max |

---

## GameState (What Agent Sees)

```python
@dataclass
class GameState:
    request_id: str
    input: str
    max_price: float
    min_quality: int
    deadline_unix: float
    time_remaining_secs: float
    quality_criteria: list[str]

    def urgency_factor(self) -> float:
        """0 (plenty of time) → 1 (about to deadline)"""
        return 1 - (time_remaining / total_time)

    def is_deadline_exceeded(self) -> bool:
        return time.time() > deadline_unix
```

---

## ToolRegistry (What Agent Uses)

```python
registry = ToolRegistry()

# Register tools
registry.register(
    definition=ToolDefinition(
        name="web_search",
        description="Search the web",
        parameters=[
            ToolParameter("query", "search query", "string"),
        ]
    ),
    handler=lambda query: requests.get(f"...?q={query}").json()
)

# Execute tools
result = registry.execute("web_search", query="python")
```

---

## Subclass Template

```python
class MyAgent(BaseAgent):
    async def route_task(self, game_state: GameState) -> dict:
        """Estimate difficulty, pick model."""
        difficulty = 0.3 if len(game_state.input) < 500 else 0.8
        return {
            "model": "gpt-4o-mini" if difficulty < 0.5 else "gpt-4o",
            "difficulty": difficulty,
            "uses_tools": difficulty > 0.5,
            "estimated_cost": 0.002 if difficulty < 0.5 else 0.05,
        }

    def get_system_prompt(self, route: dict) -> str:
        return "You are a high-quality AI agent..."

    async def _call_llm(self, model, system, messages, tools):
        # Implement for your backend (OpenAI, Anthropic, etc.)
        pass
```

---

## Decision Trees

### Should I Bid?

```
┌─ Can you hit quality threshold?
├─ YES: Continue
└─ NO: Return None (pass)

┌─ Is cost < max_price?
├─ YES: Continue
└─ NO: Return None (pass)

┌─ Is time_remaining > 5s?
├─ YES: Bid
└─ NO: Return None (pass)
```

### What Model to Use?

```
Input length > 1000?
  YES → gpt-4o (stronger)
  NO → gpt-4o-mini (faster)

Has code keywords?
  YES → gpt-4o
  NO → gpt-4o-mini

Quality criteria > 3?
  YES → gpt-4o
  NO → gpt-4o-mini
```

### Use Tools?

```
Difficulty > 0.5?
  YES → Use tools
  NO → Direct response

Time remaining > 10s?
  YES → Tools OK
  NO → Skip tools (too slow)
```

---

## Class Hierarchy

```
ToolDefinition
  ↓
ToolRegistry ← knows 10+ tools

BaseAgent (abstract)
  ├─ route_task() [abstract]
  ├─ get_system_prompt() [abstract]
  ├─ _call_llm() [abstract]
  ├─ solve() [concrete ← the loop]
  └─ _compute_bid() [concrete]
    ↓
  OpenAIAgent (concrete)
    ├─ route_task() → heuristic
    └─ _call_llm() → openai.ChatCompletion.create()
  AnthropicAgent (concrete)
    ├─ route_task() → heuristic
    └─ _call_llm() → anthropic.messages.create()

AgentProvider (HTTP server)
  ├─ agent_instance: BaseAgent
  └─ handle_broadcast(payload)
    └─ await agent.handle_broadcast(payload)
```

---

## File Structure

```
agentx/
├── tools/
│   ├── definitions.py     ← ToolDefinition, ToolRegistry
│   ├── executor.py        ← CodeExecutor, timeouts
│   └── stdlib.py          ← web_search, execute_python
├── agents/
│   ├── base.py            ← BaseAgent, GameState
│   ├── openai_agent.py    ← OpenAIAgent
│   └── anthropic_agent.py ← AnthropicAgent
└── provider.py            ← AgentProvider (HTTP server)
```

---

## Timing Assumptions

| Task | Typical Time | Timeout |
|------|--------------|---------|
| Routing (heuristic) | 10ms | N/A |
| LLM API call | 200-500ms | 5s |
| Tool execution | 100-2000ms | 5s per tool |
| One loop iteration | 500-2500ms | N/A |
| Full request (3 iterations) | 1500-7500ms | 30s deadline |

**Rule of thumb:** Request completes in 2-5 seconds, leaving 25-28s buffer.

---

## Cost Model (Estimate)

| Input | Model | Tools? | Cost |
|-------|-------|--------|------|
| 100 words | mini | No | $0.0005 |
| 500 words | mini | No | $0.001 |
| 1000 words | 4o | No | $0.01 |
| 500 words | 4o | Yes | $0.015 |
| 2000 words | 4o | Yes | $0.05 |

**Always bid ≥ cost × 1.2 (20% margin)**

---

## Exception Handling

```python
# Tool crashes
try:
    result = await _execute_tool(tc, game_state)
except TimeoutError:
    result = f"Tool timed out"

# LLM returns unparseable JSON
try:
    tool_calls = json.loads(response)
except JSONDecodeError:
    tool_calls = []  # continue loop

# Deadline exceeded
if game_state.is_deadline_exceeded():
    break  # abort loop, return partial work

# Bid out of range
if bid < 0 or bid > max_price:
    return None  # pass
```

---

## Testing Checklist

- [ ] ToolRegistry can register + execute 3 tools
- [ ] GameState.urgency_factor() returns 0-1
- [ ] _compute_bid() with varied inputs
- [ ] Mocked LLM: loop executes 2+ iterations
- [ ] Real OpenAI API: parses tool_calls correctly
- [ ] Real Anthropic API: message format correct
- [ ] AgentProvider: broadcast → submit flow
- [ ] Demo agent: runs end-to-end

---

## Debugging Checklist

**Agent doesn't bid?**
- Check: is_deadline_exceeded() called?
- Check: estimated_score < min_quality?
- Check: cost > max_price?

**Agent bids but gets 0 quality?**
- Check: system prompt is clear?
- Check: model choice (gpt-4o-mini too weak)?
- Check: tools are actually helping?

**Tool execution hangs?**
- Check: asyncio.wait_for() timeout set to 5s?
- Check: executor runs in thread pool?

**Deadline exceeded during solve?**
- Check: loop checks deadline every iteration?
- Check: tool timeout is short (2-3s, not 10s)?

---

## Key Insights

1. **Bid before solve** → agents commit early, enable parallelism
2. **One tool-calling loop** → same for OpenAI + Anthropic
3. **Three bidding factors** → difficulty, urgency, cost
4. **GameState object** → single source of truth
5. **Tool timeout 5s** → prevents hangs
6. **Max 10 iterations** → bounded termination
7. **Check deadline every iteration** → don't miss deadline

---

## Links to Full Docs

- **AGENT_DESIGN.md** — Complete specification (1300 lines)
- **DESIGN_REVIEW_SUMMARY.md** — Executive summary + rationale
- **IMPLEMENTATION_ROADMAP.md** — Task breakdown + timeline
- **AGENT_STRATEGY_GUIDE.md** — Bidding strategy guide

---

**Thinker 9 | 2026-03-31 | APPROVED FOR IMPLEMENTATION**
