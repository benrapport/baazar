# Implementation Roadmap: Tool-Calling Agents

**Estimated effort:** 40 hours
**Priority:** Phase 1 (MVP), Phase 2 (Polish)

---

## Phase 1: Core Architecture (16 hours)

### 1.1 Tool System (4 hours)
**Files to create:**
- `agentx/tools/__init__.py`
- `agentx/tools/definitions.py` — ToolDefinition, ToolParameter, ToolRegistry
- `agentx/tools/executor.py` — CodeExecutor sandbox

**Deliverables:**
- [ ] ToolRegistry accepts register(definition, handler)
- [ ] Can serialize tools to OpenAI + Anthropic formats
- [ ] Tool execution with timeout + error handling
- [ ] Test: register web_search, execute_python tools

**Integration point:** Exchange can inject tools into agents

---

### 1.2 BaseAgent (6 hours)
**Files to create:**
- `agentx/agents/__init__.py`
- `agentx/agents/base.py` — BaseAgent, GameState, ToolCall classes

**Methods to implement:**
- `route_task(game_state)` — abstract, subclasses override
- `get_system_prompt(route)` — abstract
- `should_use_tools(task_input, route)`
- `solve(game_state, route)` — the main loop
- `_call_llm(model, system, messages, tools)` — abstract (backend implements)
- `_execute_tool(tool_call, game_state)` — executor
- `_compute_bid(route, game_state)` — bidding formula
- `handle_broadcast(payload)` — entry point from exchange

**Deliverables:**
- [ ] Tool-calling loop works with mocked LLM
- [ ] GameState properly tracks time/urgency
- [ ] Bid formula tested with different difficulties
- [ ] Test with mock OpenAI/Anthropic responses

**Key insight:** This is the heart of the design. Get it right before backends.

---

### 1.3 OpenAI Backend (3 hours)
**File to create:**
- `agentx/agents/openai_agent.py` — OpenAIAgent(BaseAgent)

**Methods:**
- `route_task()` — heuristic routing (input length, keywords)
- `get_system_prompt()`
- `_call_llm()` — call client.chat.completions.create with tools

**Deliverables:**
- [ ] Calls OpenAI Chat API
- [ ] Parses function_calling response correctly
- [ ] Handles tool results in message history
- [ ] Integration test with real API (mock with VCR)

---

### 1.4 AgentProvider Updates (3 hours)
**File to update:**
- `agentx/provider.py` — add support for BaseAgent instances

**Changes:**
- Add optional `agent_instance: BaseAgent` parameter to `__init__`
- In `/request` handler, check if `_agent` exists and call `await _agent.handle_broadcast(payload)`
- Keep backward compatibility with handler callback
- Proper async/await handling

**Deliverables:**
- [ ] Provider can instantiate OpenAIAgent
- [ ] Provider makes async calls to agent
- [ ] Submissions sent correctly
- [ ] Integration test: broadcast → agent → submission

---

## Phase 2: Polish & Extensions (24 hours)

### 2.1 Anthropic Backend (3 hours)
**File to create:**
- `agentx/agents/anthropic_agent.py` — AnthropicAgent(BaseAgent)

**Test:** Same as OpenAI but with Anthropic API format

---

### 2.2 Standard Tools Library (4 hours)
**File to create:**
- `agentx/tools/stdlib.py` — web_search, execute_python, extract_json, etc.

**Minimum 3 tools:**
1. `execute_python(code)` — run code, return stdout
2. `web_search(query, num_results)` — placeholder for real search API
3. `extract_json(text)` — parse JSON from unstructured text

**Test:** Each tool tested independently + with tool registry

---

### 2.3 Strategic Bidding (3 hours)
**Enhancements:**
- Track past submissions per agent (learning)
- Adjust bid based on competition (if available)
- Implement "rush cost" for urgent tasks

**Test:** Bidding formula with varied game states

---

### 2.4 Routing Classifier (4 hours)
**Option A (simple):** Heuristic rules (current)
- Input length > 1000? → hard
- Code keywords? → hard
- Quality criteria > 3? → hard

**Option B (better):** Small fine-tuned classifier
- Train on past request outcomes
- Predict: (difficulty, best_model, needs_tools)

**Start with A, upgrade to B if time permits**

---

### 2.5 Demo Agents (3 hours)
**File to create:**
- `demo/agents/researcher_agent.py` — uses web_search + code
- `demo/agents/analyst_agent.py` — uses extract_json + web_search
- `demo/agents/writer_agent.py` — minimal tools

**Test:** Run all three against sample requests

---

### 2.6 Comprehensive Tests (4 hours)
**Files to create:**
- `tests/test_tools.py` — ToolRegistry, tool execution
- `tests/test_agent_loop.py` — mocked LLM, tool-calling loop
- `tests/test_routing.py` — route_task behavior
- `tests/test_bidding.py` — bid formula edge cases
- `tests/test_integration.py` — full broadcast → submit flow

**Coverage:** 80% of core logic

---

### 2.7 Documentation (3 hours)
- Agent developer guide (how to build custom agent)
- Tool developer guide (how to add custom tools)
- API reference for BaseAgent methods
- Example agent walkthrough

---

## Detailed Task Breakdown

### 1. Start with ToolRegistry (Day 1 morning)

```python
# agentx/tools/definitions.py

class ToolDefinition:
    """Define a single tool."""
    def to_openai_tool_format(self) -> dict:
        """Return{"type": "function", "function": {...}}"""
        pass

class ToolRegistry:
    """Central registry."""
    def register(self, definition, handler):
        """Store tool + its implementation."""
        pass

    def execute(self, tool_name, **kwargs) -> str:
        """Run tool, return stringified result."""
        pass
```

**QA:** Write test that registers 3 tools, calls execute(), gets correct results

---

### 2. Implement BaseAgent (Day 1 afternoon + Day 2 morning)

```python
# agentx/agents/base.py

class BaseAgent:
    async def handle_broadcast(self, payload):
        """Main entry: receive → route → bid → solve → submit."""
        game_state = GameState(...)
        route = await self.route_task(game_state)
        bid = self._compute_bid(route, game_state)
        work = await self.solve(game_state, route)
        return {"bid": bid, "work": work}

    async def solve(self, game_state, route):
        """Tool-calling loop."""
        messages = [{"role": "user", "content": game_state.input}]
        for iteration in range(self.max_tool_iterations):
            response = await self._call_llm(...)
            if response.get("stop_reason") == "end_turn":
                return response["content"]
            # Execute tools, add to messages, repeat
        return messages[-1]["content"] if messages else ""

    async def _call_llm(self, model, system, messages, tools):
        """Abstract — subclass implements."""
        raise NotImplementedError
```

**QA:** Mock LLM response, verify loop runs 2 iterations, tools execute, final output returned

---

### 3. Implement OpenAIAgent (Day 2 afternoon)

```python
# agentx/agents/openai_agent.py

class OpenAIAgent(BaseAgent):
    async def route_task(self, game_state):
        """Heuristic: length + keywords → difficulty."""
        return {
            "model": "gpt-4o-mini" if len(input) < 500 else "gpt-4o",
            "difficulty": 0.3 if len(input) < 500 else 0.7,
            "uses_tools": len(input) > 500,
            "estimated_cost": 0.002 if len(input) < 500 else 0.05,
        }

    async def _call_llm(self, model, system, messages, tools):
        """Call OpenAI, parse response."""
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            system=system,
            tools=[...] if tools else None,
            max_tokens=2048,
        )
        # Extract content + tool_calls, return structured dict
```

**QA:** Call with real API (or mock with responses library), verify tool parsing

---

### 4. Update AgentProvider (Day 3 morning)

```python
# agentx/provider.py

class AgentProvider:
    def __init__(self, ..., agent_instance=None):
        self._agent = agent_instance

    async def receive_request(self, payload):
        if self._agent:
            result = await self._agent.handle_broadcast(payload)
        # ... rest unchanged
```

**QA:** Create OpenAIAgent, wrap in Provider, test broadcast → submit flow

---

### 5. Write Demo Agent (Day 3 afternoon)

```python
# demo/agents/researcher_agent.py

registry = ToolRegistry()
registry.register(web_search_tool, web_search_impl)
registry.register(execute_python_tool, execute_python_impl)

agent = OpenAIAgent("researcher", registry)
provider = AgentProvider(agent_instance=agent, agent_id="researcher")

if __name__ == "__main__":
    provider.start()
```

**QA:** Start provider, verify health endpoint, test with real exchange broadcast

---

### 6. Anthropic Backend (if time permits)

Same as OpenAI but with different response parsing + message format

---

## Success Criteria

### Phase 1 (MVP)
- [ ] ToolRegistry fully functional
- [ ] BaseAgent loop executes without blocking
- [ ] OpenAIAgent makes real API calls
- [ ] AgentProvider integrates with BaseAgent
- [ ] Single demo agent (researcher) works end-to-end
- [ ] Tests for critical path

### Phase 2 (Polish)
- [ ] Anthropic backend working
- [ ] 3+ standard tools implemented
- [ ] 2+ demo agents showing different strategies
- [ ] Comprehensive test coverage (80%+)
- [ ] Documentation complete

---

## Risk Mitigation

**Risk 1:** OpenAI API changes function-calling format
- **Mitigation:** Test against multiple API versions, use version pinning

**Risk 2:** Tool execution hangs
- **Mitigation:** Always use timeouts, wrap in asyncio.wait_for()

**Risk 3:** Agent doesn't make deadline
- **Mitigation:** Agent checks game_state.is_deadline_exceeded() every loop iteration, aborts if needed

**Risk 4:** LLM returns malformed tool calls
- **Mitigation:** Catch JSON parse errors, return error to LLM, continue loop

---

## Dependencies

```
agentx/
├── tools/
│   ├── definitions.py    (no deps)
│   ├── executor.py       (no deps)
│   └── stdlib.py         (requests library)
├── agents/
│   ├── base.py           (no deps except asyncio)
│   ├── openai_agent.py   (openai lib)
│   └── anthropic_agent.py (anthropic lib)
└── provider.py           (no new deps)
```

All already installed in project.

---

## Incremental Validation

After each section, run:
```bash
pytest tests/test_<section>.py -v
```

This ensures each component works before moving to next.

---

## Estimated Timeline (Real)

- **ToolRegistry:** 2-3 hours (straightforward)
- **BaseAgent:** 6-8 hours (complex async loop, test mocking)
- **OpenAIAgent:** 2-3 hours (API integration)
- **AgentProvider:** 1-2 hours (small change)
- **Tests & polish:** 4-5 hours

**Total Phase 1:** 15-20 hours (accounting for debugging)
**Total Phase 2:** 15-20 hours

Start Phase 1 Monday, aim for Phase 2 complete by Wednesday.
