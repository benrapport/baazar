# Quick Reference: Agent Design (RFQ Model)

**Print this. Pin to your monitor.**

---

## Entry Point

```python
# Agent receives this from exchange
@dataclass
class BroadcastPayload:
    request_id: str
    input: str
    max_price: float      # the fill price
    min_quality: int
    fill_count: int       # how many winners buyer wants
    deadline_unix: float
    quality_criteria: list[str]

# Agent returns this (or None to pass)
@dataclass
class SubmissionPayload:
    work: str   # task output
```

---

## 3-Step Execution

```python
# 1. Assess difficulty (heuristic, no LLM call)
difficulty = assess_difficulty(task_input)

# 2. Decide fill/pass
if not should_fill(difficulty, max_price, model, budget, min_margin):
    return None  # pass — notify exchange

# 3. Solve + submit
work = agent.solve(task_input, deadline=deadline)
return {"work": work}
```

---

## Tool-Calling Loop

```python
async def solve(task_input, deadline):
    messages = [{"role": "user", "content": task_input}]

    for i in range(max_turns):
        if time.time() > deadline - 2.0:
            break  # return best answer

        response = backend.call(messages, tools=tool_schemas)
        if not response.tool_calls:
            return response.content  # done

        for tc in response.tool_calls:
            result = execute_tool(tc)
            messages.append(result)

    return messages[-1]["content"]
```

---

## Fill/Pass Decision

```python
def should_fill(difficulty, max_price, model, budget, min_margin):
    estimated_cost = estimate_cost(difficulty, model)
    if budget < estimated_cost:
        return False  # can't afford it
    if max_price < estimated_cost * (1 + min_margin):
        return False  # not profitable enough
    return True
```

### Strategy Archetypes

| Strategy | min_margin | Fills at |
|----------|-----------|----------|
| sniper | 0.05 | 5% margin |
| agg | 0.1 | 10% margin |
| bal | 0.5 | 50% margin |
| con | 1.5 | 150% margin |
| premium | 2.0 | 200% margin |

---

## Decision Trees

### Should I Fill?

```
┌─ Is max_price > estimated_cost × (1 + min_margin)?
├─ YES: Continue
└─ NO: Pass

┌─ Is budget sufficient?
├─ YES: Continue
└─ NO: Pass

┌─ Is model appropriate for difficulty?
├─ YES: Fill
└─ NO: Pass
```

### What Model to Use?

```
Difficulty = hard/extreme?
  → Expensive model (GPT-4o, o4-mini)

Difficulty = easy/medium?
  → Cheap model (GPT-4o-mini)
```

---

## Economics

| Term | Value |
|------|-------|
| Fill price | = buyer's max_price |
| Exchange fee | 1.5% of fill price |
| Buyer charged | fill_price + fee |
| Agent receives | fill_price |
| Agent profit | fill_price - compute_cost |

---

## Cost Model

| Model | Input/1M | Output/1M | Easy (~200 tok) | Medium (~800 tok) |
|-------|----------|-----------|-----------------|-------------------|
| GPT-4o-mini | $0.15 | $0.60 | ~$0.0001 | ~$0.0004 |
| GPT-4.1-mini | $0.40 | $1.60 | ~$0.0003 | ~$0.0011 |
| GPT-4o | $2.50 | $10.00 | ~$0.0017 | ~$0.0068 |
| o4-mini | $1.10 | $4.40 | ~$0.0007 | ~$0.0030 |

---

## Timing

| Task | Typical | Timeout |
|------|---------|---------|
| Difficulty assessment | <1ms | N/A |
| Fill/pass decision | <1ms | N/A |
| LLM API call | 200-500ms | 5s |
| Tool execution | 100-2000ms | 5s |
| Full solve (3 turns) | 1.5-7.5s | 30s deadline |

---

## File Structure

```
exchange/
  config.py         ← ExchangeDefaults (fee rate, timeouts)
  game.py           ← RFQ engine (broadcast → judge → select)
  judge.py          ← LLM scoring (blind to pricing)
  settlement.py     ← Ledger + fee calculation
  server.py         ← FastAPI endpoints

agent/
  runtime.py        ← ClaudeCodeAgent (multi-turn tool loop)
  tools/            ← Built-in tools

sim/
  strategy.py       ← should_fill() + assess_difficulty()
  fleet.py          ← Fleet management
```

---

## Debugging

**Agent doesn't fill?**
- Check: `max_price < estimated_cost * (1 + min_margin)`?
- Check: budget exhausted?
- Check: model-difficulty mismatch? (cheap model on hard task)

**Agent fills but gets low quality?**
- Check: system prompt quality
- Check: model choice (gpt-4o-mini too weak for task?)
- Check: are tools helping or hindering?

**Deadline exceeded?**
- Check: loop checks deadline every iteration?
- Check: tool timeout is short (2-3s)?

---

## Key Principles

1. **Fill/pass before solving** — don't waste compute on unprofitable tasks
2. **Speed wins** — earliest qualifying submission wins
3. **Agent isolation** — you can't see competitors
4. **Blind judging** — judge doesn't know the fill price
5. **Multi-fill** — check `fill_count` for more winning slots

---

**Updated 2026-04-03 | RFQ Model**
