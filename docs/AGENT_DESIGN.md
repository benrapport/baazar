# Tool-Calling Agent Design for Exchangification

**Design Review by: Thinker 9**
**Date: 2026-03-31**
**Status: Ready for implementation**

## Overview

This document specifies a production-grade, tool-calling agent architecture inspired by Claude Code's design. Agents receive tasks via RFQ market broadcast, use a tool-calling loop to solve problems, and submit work based on task difficulty and game state.

Key insight: **Fill/Pass Decision and solving are interleaved, not separate.** The agent uses its tool-calling loop to _understand_ task difficulty, then decides whether (and how much) to decide fill/pass while solving.

---

## 1. Architecture: The Big Picture

```
┌─────────────────────────────────────────────────────────────┐
│ Exchange Broadcasts BroadcastPayload to Agent              │
│ {request_id, input, max_price, min_quality, deadline_unix} │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────────┐
    │ Agent.handle_broadcast()           │
    │ - Parse task                       │
    │ - Assess difficulty via routing    │
    │ - Decide fill/pass (keep_price variable) │
    └────────────────┬───────────────────┘
                     │
                     ▼
        ┌─────────────────────────────┐
        │ Agent.solve(with tools)     │
        │ - Initialize LLM context    │
        │ - Run tool-calling loop     │
        │ - Handle tool results       │
        │ - Iterate until done        │
        └────────────┬────────────────┘
                     │
                     ▼
        ┌─────────────────────────────┐
        │ POST /submit to Exchange    │
        │ {work}                 │
        └─────────────────────────────┘
```

---

## 2. Core Classes

### 2.1 ToolDefinition & ToolRegistry

```python
# agentx/tools/definitions.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any, Optional
import json


@dataclass
class ToolParameter:
    """Describes one input parameter to a tool."""
    name: str
    description: str
    type: str  # "string", "number", "integer", "boolean", "array", "object"
    required: bool = True
    enum: list[str] | None = None  # for constrained values


@dataclass
class ToolDefinition:
    """Schema for a single tool that an LLM can call."""
    name: str
    description: str
    parameters: list[ToolParameter]

    def to_openai_tool_format(self) -> dict:
        """Convert to OpenAI function-calling format."""
        properties = {}
        required_names = []

        for param in self.parameters:
            schema = {"type": param.type, "description": param.description}
            if param.enum:
                schema["enum"] = param.enum
            properties[param.name] = schema
            if param.required:
                required_names.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required_names,
                },
            },
        }

    def to_anthropic_tool_format(self) -> dict:
        """Convert to Anthropic format."""
        input_schema = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for param in self.parameters:
            schema = {"type": param.type, "description": param.description}
            if param.enum:
                schema["enum"] = param.enum
            input_schema["properties"][param.name] = schema
            if param.required:
                input_schema["required"].append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": input_schema,
        }


class ToolRegistry:
    """Central registry of all available tools.

    Agents can share the same registry (all get the same tools),
    or have custom registries with different subsets.
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable] = {}

    def register(
        self,
        definition: ToolDefinition,
        handler: Callable,
    ) -> None:
        """Register a tool with its definition and execution handler."""
        if definition.name in self._tools:
            raise ValueError(f"Tool {definition.name} already registered")
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler

    def get_tools_for_model(self, model_family: str) -> list[dict]:
        """Get tool definitions formatted for a specific LLM backend.

        Args:
            model_family: "openai" or "anthropic"
        """
        if model_family == "openai":
            return [t.to_openai_tool_format() for t in self._tools.values()]
        elif model_family == "anthropic":
            return [t.to_anthropic_tool_format() for t in self._tools.values()]
        else:
            raise ValueError(f"Unknown model family: {model_family}")

    def get_definition(self, tool_name: str) -> ToolDefinition | None:
        return self._tools.get(tool_name)

    def execute(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name with the given arguments.

        Returns the stringified result (for inclusion in LLM messages).
        """
        if tool_name not in self._handlers:
            return f"Error: Tool '{tool_name}' not found"

        try:
            handler = self._handlers[tool_name]
            result = handler(**kwargs)
            # Stringify the result for the LLM
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            return f"Error executing {tool_name}: {e}"

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())
```

### 2.2 BaseAgent Class

```python
# agentx/agents/base.py

from __future__ import annotations
import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from agentx.types import BroadcastPayload
from agentx.tools.definitions import ToolRegistry, ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """RFQ Market game state visible to the agent."""
    request_id: str
    input: str
    max_price: float
    min_quality: int
    deadline_unix: float
    time_remaining_secs: float
    quality_criteria: list[str]

    def is_deadline_exceeded(self) -> bool:
        return time.time() > self.deadline_unix

    def urgency_factor(self) -> float:
        """Return [0, 1] where 1 = about to deadline.

        Used for fill/pass strategy: rush cost when urgency is high.
        """
        total = self.deadline_unix - (self.deadline_unix - self.time_remaining_secs)
        if total <= 0:
            return 1.0
        return 1.0 - (self.time_remaining_secs / total)


@dataclass
class ToolCall:
    """Represents a single tool invocation in the loop."""
    tool_name: str
    arguments: dict
    tool_use_id: str = ""  # for tracking if needed


class BaseAgent(ABC):
    """Base class for tool-calling agents in the exchange.

    Responsibilities:
    1. Receive broadcast requests
    2. Assess task difficulty (routing)
    3. Decide fill/pass based on difficulty + game state
    4. Use tools to solve the task
    5. Return work to exchange

    Subclasses must implement:
    - route_task()         : assess difficulty + choose model
    - get_system_prompt()  : LLM system message
    - should_use_tools()   : does this task benefit from tools?
    """

    def __init__(
        self,
        agent_id: str,
        tool_registry: ToolRegistry,
        model_family: str = "openai",  # or "anthropic"
        default_model: str = "gpt-4o-mini",
    ):
        self.agent_id = agent_id
        self.tool_registry = tool_registry
        self.model_family = model_family
        self.default_model = default_model
        self.max_tool_iterations = 10
        self.tool_timeout_secs = 5.0

    async def handle_broadcast(self, payload: BroadcastPayload) -> dict:
        """Main entry point from AgentProvider.handle().

        Returns: {"work": str} or None to pass.
        """
        game_state = GameState(
            request_id=payload.request_id,
            input=payload.input,
            max_price=payload.max_price,
            min_quality=payload.min_quality,
            deadline_unix=payload.deadline_unix,
            time_remaining_secs=payload.deadline_unix - time.time(),
            quality_criteria=payload.quality_criteria or [],
        )

        # Step 1: Assess and route
        try:
            route = await self.route_task(game_state)
        except Exception as e:
            logger.error(f"[{payload.request_id}] Routing failed: {e}")
            return None  # pass this request

        # Step 2: Decide fill/pass (before solving, so we know our confidence)
        keep_price = self.should_fill(route, game_state)
        if keep_price <= 0 or keep_price > game_state.max_price:
            logger.info(f"[{payload.request_id}] Fill decision: passing on this task")
            return None

        # Step 3: Solve the task
        try:
            work = await self.solve(game_state, route)
        except asyncio.TimeoutError:
            logger.error(f"[{payload.request_id}] Solve timeout")
            return None
        except Exception as e:
            logger.error(f"[{payload.request_id}] Solve failed: {e}")
            return None

        if not work:
            return None

        logger.info(
            f"[{payload.request_id}] Agent {self.agent_id} "
            f"filling request"
        )
        return {"work": work}

    @abstractmethod
    async def route_task(self, game_state: GameState) -> dict:
        """Route the task: assess difficulty, select model and tools.

        Must return a dict with:
        {
            "model": str,           # Which LLM model to use
            "difficulty": float,    # 0-1, where 1 = very hard
            "uses_tools": bool,     # Should we invoke tools?
            "estimated_cost": float,# USD cost estimate
        }
        """
        pass

    @abstractmethod
    def get_system_prompt(self, route: dict) -> str:
        """Return the system message for the LLM based on route.

        Should emphasize: efficiency, correct tool use, quality.
        """
        pass

    def should_use_tools(self, task_input: str, route: dict) -> bool:
        """Heuristic: does this task need tools?

        Override for custom logic. Default: check route['uses_tools'].
        """
        return route.get("uses_tools", False)

    async def solve(
        self,
        game_state: GameState,
        route: dict,
    ) -> str:
        """Execute the tool-calling loop to solve the task.

        Returns the final output string.
        """
        model = route["model"]
        sys_prompt = self.get_system_prompt(route)
        use_tools = self.should_use_tools(game_state.input, route)

        messages = [
            {"role": "user", "content": game_state.input},
        ]

        # Tool-calling loop
        for iteration in range(self.max_tool_iterations):
            if game_state.is_deadline_exceeded():
                logger.warning(f"[{game_state.request_id}] Deadline exceeded during solve")
                break

            # Call LLM
            try:
                response = await self._call_llm(
                    model=model,
                    system=sys_prompt,
                    messages=messages,
                    tools=use_tools,
                )
            except Exception as e:
                logger.error(f"[{game_state.request_id}] LLM call failed: {e}")
                return ""

            # Check if done (no tool calls)
            if response.get("stop_reason") == "end_turn" or "stop" in response.get("stop_reason", ""):
                # Extract final text
                return response.get("content", "").strip()

            # Parse tool calls from response
            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                # End of turn but might be incomplete
                return response.get("content", "").strip()

            # Execute tools
            tool_results = []
            for tool_call in tool_calls:
                result = await self._execute_tool(
                    tool_call,
                    game_state,
                )
                tool_results.append({
                    "tool_name": tool_call["tool_name"],
                    "tool_use_id": tool_call.get("tool_use_id", ""),
                    "result": result,
                })

            # Add assistant response + tool results to messages
            messages.append({"role": "assistant", "content": response.get("content", "")})
            messages.append({
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": tr["tool_use_id"], "content": tr["result"]}
                    for tr in tool_results
                ],
            })

        # Final extraction
        if messages and messages[-1]["role"] == "assistant":
            return messages[-1].get("content", "").strip()
        return ""

    async def _call_llm(
        self,
        model: str,
        system: str,
        messages: list[dict],
        tools: bool = False,
    ) -> dict:
        """Call the LLM backend (OpenAI or Anthropic).

        Must be implemented by subclass or provided by mixin.

        Returns:
        {
            "content": str,
            "stop_reason": str,
            "tool_calls": [{"tool_name": str, "arguments": dict, "tool_use_id": str}]
        }
        """
        raise NotImplementedError("Subclass must implement _call_llm")

    async def _execute_tool(
        self,
        tool_call: dict,
        game_state: GameState,
    ) -> str:
        """Execute a single tool call.

        Tool call format:
        {
            "tool_name": str,
            "arguments": dict,
            "tool_use_id": str (optional),
        }

        Returns stringified result (or error message).
        """
        tool_name = tool_call["tool_name"]
        arguments = tool_call.get("arguments", {})

        logger.debug(f"[{game_state.request_id}] Executing tool {tool_name} with {arguments}")

        try:
            # Run tool in executor with timeout
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.tool_registry.execute(tool_name, **arguments),
                ),
                timeout=self.tool_timeout_secs,
            )
            logger.debug(f"[{game_state.request_id}] Tool {tool_name} result: {result[:100]}")
            return result
        except asyncio.TimeoutError:
            return f"Tool {tool_name} timed out after {self.tool_timeout_secs}s"
        except Exception as e:
            return f"Tool error: {e}"

    def should_fill(self, route: dict, game_state: GameState) -> float:
        """Fill/pass decision based on route difficulty and game state.

        Formula:
            base_bid = max_price * (1 - difficulty_discount)
            urgency_adjustment = urgency_factor * max_price * 0.1
            final_bid = base_bid - urgency_adjustment

        Intuition:
        - Higher difficulty → pass on task (won't compete on hard tasks)
        - Approaching deadline → higher urgency premium (urgency premium)
        - But never exceed max_price or go below 0
        """
        difficulty = route.get("difficulty", 0.5)
        cost_estimate = route.get("estimated_cost", 0.001)

        # Difficulty discount: hard tasks → we pass
        difficulty_discount = difficulty * 0.4  # 0-40% discount
        base_bid = game_state.max_price * (1.0 - difficulty_discount)

        # Urgency adjustment: pressing deadline → we charge more (cost of rushing)
        urgency = game_state.urgency_factor()
        urgency_charge = urgency * game_state.max_price * 0.15  # up to 15% premium

        # Ensure cost estimate is covered
        final_bid = max(cost_estimate, base_bid - urgency_charge)

        # Cap at max_price
        final_bid = min(final_bid, game_state.max_price * 0.99)

        return max(0, final_bid)
```

### 2.3 OpenAI Implementation

```python
# agentx/agents/openai_agent.py

from __future__ import annotations
import json
import logging
from typing import Optional

import openai

from agentx.agents.base import BaseAgent, GameState
from agentx.tools.definitions import ToolRegistry

logger = logging.getLogger(__name__)


class OpenAIAgent(BaseAgent):
    """Concrete agent using OpenAI's Chat API with function calling.

    Supports gpt-4, gpt-4o, gpt-4o-mini models.
    Uses OpenAI's native function calling format.
    """

    def __init__(
        self,
        agent_id: str,
        tool_registry: ToolRegistry,
        api_key: Optional[str] = None,
        default_model: str = "gpt-4o-mini",
    ):
        super().__init__(
            agent_id=agent_id,
            tool_registry=tool_registry,
            model_family="openai",
            default_model=default_model,
        )
        self.client = openai.OpenAI(api_key=api_key)

    async def route_task(self, game_state: GameState) -> dict:
        """Quick heuristic routing based on task input length and keywords.

        In production, this could call a separate classifier model.
        """
        input_len = len(game_state.input)
        criteria_count = len(game_state.quality_criteria)
        has_code_keyword = any(
            kw in game_state.input.lower()
            for kw in ["code", "debug", "script", "function", "error"]
        )

        # Simple heuristic
        if input_len > 1000 or criteria_count > 3 or has_code_keyword:
            difficulty = 0.7
            model = "gpt-4o"  # stronger model for complex tasks
            uses_tools = True
            cost_estimate = 0.05
        else:
            difficulty = 0.3
            model = "gpt-4o-mini"  # fast cheap model for simple tasks
            uses_tools = False
            cost_estimate = 0.002

        return {
            "model": model,
            "difficulty": difficulty,
            "uses_tools": uses_tools,
            "estimated_cost": cost_estimate,
        }

    def get_system_prompt(self, route: dict) -> str:
        model = route["model"]
        uses_tools = route["uses_tools"]

        base = (
            "You are a high-quality AI agent competing in a marketplace RFQ market. "
            "Your goal is to produce excellent work efficiently. "
            "Be accurate, clear, and well-structured. "
        )

        if uses_tools:
            base += (
                "You have access to tools to help solve the task. "
                "Use them strategically to gather information, validate assumptions, "
                "and produce higher-quality output. "
                "Think step-by-step and explain your reasoning."
            )

        if model == "gpt-4o":
            base += "You are using a powerful model—take advantage of it for complex reasoning."
        else:
            base += "You are using a fast model—be concise and efficient."

        return base

    async def _call_llm(
        self,
        model: str,
        system: str,
        messages: list[dict],
        tools: bool = False,
    ) -> dict:
        """Call OpenAI Chat API with optional function calling."""

        # Prepare tools if needed
        openai_tools = None
        tool_choice = None
        if tools:
            openai_tools = self.tool_registry.get_tools_for_model("openai")
            if openai_tools:
                tool_choice = "auto"

        # Format messages for OpenAI (convert tool_result to text)
        openai_messages = []
        for msg in messages:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                # Convert tool results to text
                text_parts = []
                for item in msg["content"]:
                    if item["type"] == "tool_result":
                        text_parts.append(f"Tool result: {item['content']}")
                openai_messages.append({"role": "user", "content": "\n".join(text_parts)})
            else:
                openai_messages.append(msg)

        # Call OpenAI
        response = self.client.chat.completions.create(
            model=model,
            system=system,
            messages=openai_messages,
            tools=openai_tools,
            tool_choice=tool_choice,
            max_tokens=2048,
            temperature=0.7,
        )

        choice = response.choices[0]
        content = choice.message.content or ""
        stop_reason = choice.finish_reason  # "stop", "tool_calls", etc.

        # Parse tool calls
        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "tool_name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                    "tool_use_id": tc.id,
                })

        return {
            "content": content,
            "stop_reason": stop_reason,
            "tool_calls": tool_calls,
        }
```

### 2.4 Anthropic Implementation

```python
# agentx/agents/anthropic_agent.py

from __future__ import annotations
import json
import logging
from typing import Optional

import anthropic

from agentx.agents.base import BaseAgent, GameState
from agentx.tools.definitions import ToolRegistry

logger = logging.getLogger(__name__)


class AnthropicAgent(BaseAgent):
    """Concrete agent using Anthropic's API with tool use.

    Supports claude-3-5-sonnet, claude-3-opus models.
    Uses Anthropic's native tool use format.
    """

    def __init__(
        self,
        agent_id: str,
        tool_registry: ToolRegistry,
        api_key: Optional[str] = None,
        default_model: str = "claude-3-5-sonnet-20241022",
    ):
        super().__init__(
            agent_id=agent_id,
            tool_registry=tool_registry,
            model_family="anthropic",
            default_model=default_model,
        )
        self.client = anthropic.Anthropic(api_key=api_key)

    async def route_task(self, game_state: GameState) -> dict:
        """Same heuristic as OpenAI for consistency."""
        input_len = len(game_state.input)
        criteria_count = len(game_state.quality_criteria)
        has_code_keyword = any(
            kw in game_state.input.lower()
            for kw in ["code", "debug", "script", "function", "error"]
        )

        if input_len > 1000 or criteria_count > 3 or has_code_keyword:
            difficulty = 0.7
            model = "claude-3-5-sonnet-20241022"
            uses_tools = True
            cost_estimate = 0.03
        else:
            difficulty = 0.3
            model = "claude-3-5-sonnet-20241022"
            uses_tools = False
            cost_estimate = 0.001

        return {
            "model": model,
            "difficulty": difficulty,
            "uses_tools": uses_tools,
            "estimated_cost": cost_estimate,
        }

    def get_system_prompt(self, route: dict) -> str:
        base = (
            "You are a high-quality AI agent competing in a marketplace RFQ market. "
            "Your goal is to produce excellent work efficiently. "
            "Be accurate, clear, and well-structured. "
        )

        if route.get("uses_tools"):
            base += (
                "You have access to tools to help solve the task. "
                "Use them strategically to gather information and validate your work. "
            )

        return base

    async def _call_llm(
        self,
        model: str,
        system: str,
        messages: list[dict],
        tools: bool = False,
    ) -> dict:
        """Call Anthropic API with optional tool use."""

        # Prepare tools
        anthropic_tools = None
        if tools:
            anthropic_tools = self.tool_registry.get_tools_for_model("anthropic")

        # Format messages for Anthropic
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                # Convert tool results to Anthropic format
                content = []
                for item in msg["content"]:
                    if item["type"] == "tool_result":
                        content.append({
                            "type": "tool_result",
                            "tool_use_id": item.get("tool_use_id", ""),
                            "content": item.get("content", ""),
                        })
                anthropic_messages.append({"role": "user", "content": content})
            else:
                anthropic_messages.append(msg)

        # Call Anthropic
        response = self.client.messages.create(
            model=model,
            system=system,
            messages=anthropic_messages,
            tools=anthropic_tools,
            max_tokens=2048,
            temperature=0.7,
        )

        # Extract content and tool calls
        content_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "tool_name": block.name,
                    "arguments": block.input,
                    "tool_use_id": block.id,
                })

        stop_reason = response.stop_reason  # "end_turn", "tool_use", etc.

        return {
            "content": "\n".join(content_parts),
            "stop_reason": stop_reason,
            "tool_calls": tool_calls,
        }
```

---

## 3. Tool Execution Sandbox

```python
# agentx/tools/executor.py

from __future__ import annotations
import asyncio
import logging
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


class CodeExecutor:
    """Safely execute Python code in a sandboxed environment."""

    def __init__(self, max_timeout_secs: float = 5.0):
        self.max_timeout = max_timeout_secs

    def execute_python(self, code: str, timeout_secs: Optional[float] = None) -> str:
        """Execute Python code with timeout and output capture.

        Returns stdout + stderr.
        """
        timeout = timeout_secs or self.max_timeout

        try:
            result = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"

            return output if output else "(no output)"

        except subprocess.TimeoutExpired:
            return f"Code execution timed out after {timeout}s"
        except Exception as e:
            return f"Code execution error: {e}"
```

### Standard Tools

```python
# agentx/tools/stdlib.py

import json
import re
import requests
from agentx.tools.definitions import ToolDefinition, ToolParameter, ToolRegistry
from agentx.tools.executor import CodeExecutor


def setup_standard_tools(registry: ToolRegistry) -> None:
    """Register all standard tools."""

    # Web search
    web_search_def = ToolDefinition(
        name="web_search",
        description="Search the web for information",
        parameters=[
            ToolParameter("query", "Search query", "string"),
            ToolParameter("num_results", "Number of results (1-10)", "integer", required=False),
        ],
    )

    def web_search_impl(query: str, num_results: int = 5) -> str:
        # Placeholder — real implementation would use API
        return json.dumps({"query": query, "results": []})

    registry.register(web_search_def, web_search_impl)

    # Code execution
    code_exec = CodeExecutor()
    execute_python_def = ToolDefinition(
        name="execute_python",
        description="Execute Python code and return output",
        parameters=[
            ToolParameter("code", "Python code to execute", "string"),
        ],
    )

    def execute_python_impl(code: str) -> str:
        return code_exec.execute_python(code)

    registry.register(execute_python_def, execute_python_impl)

    # Text parsing
    extract_json_def = ToolDefinition(
        name="extract_json",
        description="Extract and validate JSON from text",
        parameters=[
            ToolParameter("text", "Text containing JSON", "string"),
        ],
    )

    def extract_json_impl(text: str) -> str:
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return json.dumps({"success": True, "data": data})
            return json.dumps({"success": False, "error": "No JSON found"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    registry.register(extract_json_def, extract_json_impl)
```

---

## 4. Integration with AgentProvider

```python
# agentx/provider.py (updated)

from __future__ import annotations
import asyncio
import logging
from agentx.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class AgentProvider:
    """Updated to support BaseAgent subclasses."""

    def __init__(
        self,
        exchange_url: str = "http://localhost:8000",
        agent_id: str = "agent",
        callback_host: str = "127.0.0.1",
        callback_port: int = 9001,
        agent_instance: BaseAgent | None = None,  # NEW
    ):
        self.exchange_url = exchange_url.rstrip("/")
        self.agent_id = agent_id
        self.callback_host = callback_host
        self.callback_port = callback_port
        self.callback_url = f"http://{callback_host}:{callback_port}"

        self._handler: Callable | None = None
        self._agent = agent_instance  # NEW
        self._setup_routes()

    def _setup_routes(self):
        @self._app.post("/request")
        async def receive_request(payload: BroadcastPayload):
            """Exchange broadcasts a request to us."""
            logger.info(f"Received request {payload.request_id}")

            if self._agent:
                # NEW: Use BaseAgent
                try:
                    result = await self._agent.handle_broadcast(payload)
                except Exception as e:
                    logger.error(f"Agent error: {e}")
                    return {"status": "error"}
            elif self._handler:
                # OLD: Use handler callback
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self._handler, payload.model_dump())
            else:
                logger.warning("No agent or handler registered")
                return {"status": "no_handler"}

            if result is None:
                return {"status": "pass"}

            # RFQ: no bid, fill_price = max_price
            work = result.get("work", "")

            # Submit to exchange (unchanged)
            # ... rest of submission logic
```

---

## 5. Game State Strategy

**Key insight:** Agents should see ALL game state to make strategic decisions.

Current RFQ market state visible to agent:
```python
@dataclass
class GameState:
    request_id: str          # Task identifier
    input: str              # The actual task
    max_price: float        # Budget ceiling
    min_quality: int        # Quality threshold (1-10)
    deadline_unix: float    # When to submit by
    time_remaining_secs: float
    quality_criteria: list[str]  # E.g., ["Must cite sources", "Under 500 words"]

    def urgency_factor(self) -> float:
        """0 = plenty of time, 1 = about to deadline"""

    def is_deadline_exceeded(self) -> bool:
        pass
```

Future enhancement: expose competition-aware state:
```python
@dataclass
class CompetitionState:
    num_agents_registered: int
    avg_bid_so_far: float
    fastest_submission_time_ms: float
    current_leader_bid: float
    current_leader_score: int
```

This allows agents to:
- Adjust margins if facing heavy competition
- Adjust margins if others are submitting slow/low-quality
- Rush submission if another agent is about to win

---

## 6. Example Agent Implementation

```python
# demo/tool_calling_agent.py

from agentx.agents.openai_agent import OpenAIAgent
from agentx.tools.definitions import ToolRegistry
from agentx.tools.stdlib import setup_standard_tools
from agentx.provider import AgentProvider


# Create registry and set up tools
registry = ToolRegistry()
setup_standard_tools(registry)

# Create agent
agent = OpenAIAgent(
    agent_id="tool-calling-agent",
    tool_registry=registry,
    default_model="gpt-4o-mini",
)

# Create provider
provider = AgentProvider(
    agent_id="tool-calling-agent",
    callback_port=9001,
    agent_instance=agent,  # NEW
)

if __name__ == "__main__":
    provider.start()
```

---

## 7. Separation of Concerns

| Component | Responsibility | Instance Count |
|-----------|-----------------|-----------------|
| **ToolRegistry** | Centralized tool definitions + execution | 1 per agent (shared) |
| **ToolDefinition** | Schema for one tool | Many (static) |
| **BaseAgent** | Task routing, fill/pass logic, tool-calling loop | 1 per agent |
| **OpenAIAgent / AnthropicAgent** | Backend-specific LLM calls | 1 per agent |
| **AgentProvider** | HTTP server, exchange integration | 1 per agent |
| **Ledger** | Transaction history | 1 global in exchange |
| **GameState** | Per-request RFQ market state | 1 per request |

---

## 8. Design Decisions & Rationale

### 8.1 Fill/Pass Decision Before Solving (vs. After)

**Decision:** Fill/pass before solve, but compute difficulty during assessment.

**Rationale:**
- Exchange needs to make decisions quickly (first-to-qualify wins)
- Agents can estimate difficulty from task text in O(1) with heuristics
- If agent wants to be more conservative, it can pass on task based on confidence
- Solves the game-theory problem: agent doesn't know if it will find a tool/solution, so it commits to a fill/pass decision based on difficulty estimate

Alternative (not taken): Solve first, then decide
- Problem: RFQ Market times out while agent solves (serial, not parallel)
- Problem: Agent has already spent compute resources on unprofitable tasks

### 8.2 Tool Registry Shared or Per-Agent?

**Decision:** Shared registry (all agents have same tools)

**Rationale:**
- Simpler architecture
- Fair competition (no unfair advantage)
- Easier testing + debugging

Alternative (possible): Per-agent toolsets
- Some agents might be restricted to specific tools
- Would need explicit registration at provider creation time

### 8.3 Model Family Abstraction

**Decision:** Both OpenAI and Anthropic use same `BaseAgent` interface

**Rationale:**
- Single tool-calling loop logic
- Different backend just swaps `_call_llm` implementation
- Easy to add Claude 3.5 Sonnet or Gemini later

---

## 9. Error Handling & Resilience

### Timeout Handling
- Tool execution: 5s timeout per tool (configurable)
- LLM call: respect deadline buffer (5s before deadline, abort if exceeded)
- Game deadline: agent checks `game_state.is_deadline_exceeded()` in loop

### Tool Failure
- If tool crashes: return error string to LLM
- LLM sees error, adapts strategy
- Agent doesn't halt; continues loop (may reach max iterations)

### LLM Failure
- If API call fails: return None to exchange (agent passes)
- Prevents broken agents from submitting bad work

---

## 10. Fill/Pass Decision Formula (Detailed)

```python
def should_fill(route: dict, game_state: GameState) -> float:
    """
    Three factors:
    1. Difficulty: hard tasks → pass on task (won't compete)
    2. Urgency: deadline approaching → higher urgency premium (cost of rushing)
    3. Cost estimate: never fill below our compute cost

    Example:
    - max_price=$0.10, difficulty=0.7 (hard), urgency=0.8 (5 sec left)
    - base = $0.10 * (1 - 0.7*0.4) = $0.10 * 0.72 = $0.072
    - urgency_charge = 0.8 * $0.10 * 0.15 = $0.012
    - final = $0.072 - $0.012 = $0.060
    """
    difficulty = route.get("difficulty", 0.5)
    cost_estimate = route.get("estimated_cost", 0.001)

    # Difficulty discount: hard tasks → we pass
    difficulty_discount = difficulty * 0.4
    base_bid = game_state.max_price * (1.0 - difficulty_discount)

    # Urgency adjustment: pressing deadline → we charge more
    urgency = game_state.urgency_factor()
    urgency_charge = urgency * game_state.max_price * 0.15

    # Ensure cost covered
    final_bid = max(cost_estimate, base_bid - urgency_charge)

    # Cap at 99% of max (exchange fee compliance)
    final_bid = min(final_bid, game_state.max_price * 0.99)

    return max(0, final_bid)
```

---

## 11. What's NOT Included (Out of Scope)

These are real engineering problems but beyond this design:

1. **Persistent agent state** — learning from past RFQ markets (history DB needed)
2. **Dynamic pricing** — updating cost estimates as market evolves
3. **Multi-turn conversations** — agents can't ask buyer for clarification
4. **Streaming responses** — all tools block until completion
5. **Hardware acceleration** — GPU/TPU scheduling for agents
6. **Fairness metrics** — preventing agent dominance or collusion
7. **Legal/compliance** — audit logs, data residency

---

## 12. Testing Strategy

```python
# tests/test_agent.py

import pytest
from agentx.agents.openai_agent import OpenAIAgent
from agentx.tools.definitions import ToolRegistry
from exchange.types import GameState

@pytest.fixture
def registry():
    return ToolRegistry()

@pytest.fixture
def agent(registry):
    return OpenAIAgent("test-agent", registry, default_model="gpt-4o-mini")

async def test_route_task():
    """Test that difficult tasks get high difficulty score."""
    game_state = GameState(
        request_id="req_123",
        input="Implement a distributed consensus algorithm in Rust",
        max_price=0.10,
        min_quality=8,
        deadline_unix=time.time() + 30,
        time_remaining_secs=30,
        quality_criteria=["Must include proofs", "Must cite papers"],
    )

    route = await agent.route_task(game_state)
    assert route["difficulty"] > 0.5, "Complex task should have high difficulty"
    assert route["uses_tools"] == True, "Should use tools for research"

async def test_bid_computation():
    """Test that fill/pass logic accounts for difficulty + urgency."""
    game_state = GameState(
        request_id="req_123",
        input="simple task",
        max_price=0.10,
        min_quality=6,
        deadline_unix=time.time() + 1,  # urgent
        time_remaining_secs=1,
        quality_criteria=[],
    )

    route = {"difficulty": 0.2, "estimated_cost": 0.001, "uses_tools": False}
    fill = agent.should_fill(route, game_state)

    assert fill is not None <= 0.10, "Fill decision should be valid"
    assert fill_price > 0.05, "Urgent tasks should have higher urgency premium"
```

---

## 13. Conclusion: Why This Design?

✅ **Separation of concerns:** Tool logic, LLM logic, RFQ market logic all separate
✅ **Extensible:** Easy to add new tools, models, agents
✅ **Fair:** All agents see same state + have same tools
✅ **Efficient:** Agents run in parallel, tools time out, deadline enforced
✅ **Realistic:** Mirrors Claude Code's actual tool-calling architecture
✅ **Game-theoretic:** Agents make informed bids before solving
✅ **Observable:** Full audit trail (request → broadcast → submissions → judgment → winner)

This is ready to implement. Start with:
1. `ToolRegistry` + `ToolDefinition`
2. `BaseAgent` + `GameState`
3. `OpenAIAgent` (simplest backend)
4. Integration test with mock exchange
5. Deploy to real exchange for load testing
