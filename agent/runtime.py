"""Agent runtime: multi-turn tool-calling loop with cost tracking and session management."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from agent.backends import create_backend
from agent.backends.base import LLMBackend, LLMResponse, ToolCall
from agent.session import Session
from agent.tools import BUILTIN_TOOLS
from agent.tools.base import Tool, tool_to_openai_schema, tool_to_anthropic_schema
from constants.models import Model, ModelProvider, MODEL_PROVIDER, token_cost_usd

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for ClaudeCodeAgent."""
    model: Model = Model.GPT_4_1_MINI
    system_prompt: str = "You are a capable AI agent. Solve the task using the tools available to you."
    max_turns: int = 10
    max_tokens: int = 4096
    temperature: float = 0.3
    tools: list[Tool] | None = None  # None = use BUILTIN_TOOLS
    budget_cents: float = 3000.0  # $30 starting budget


class ClaudeCodeAgent:
    """A reusable agent module that mirrors Claude Code's architecture.

    Instantiate with a config, then call solve() for each task.
    The agent maintains a running cost tally across solves.
    """

    def __init__(self, config: AgentConfig | None = None):
        """Initialize the agent with configuration."""
        self.config = config or AgentConfig()

        # Initialize backend
        self.backend: LLMBackend = create_backend(self.config.model)

        # Initialize tools
        self.tools = self.config.tools or BUILTIN_TOOLS
        self._tool_map: dict[str, Tool] = {tool.name: tool for tool in self.tools}

        # Build tool schemas based on provider
        provider = MODEL_PROVIDER[self.config.model]
        if provider == ModelProvider.OPENAI:
            self.tool_schemas = [tool_to_openai_schema(tool) for tool in self.tools]
        elif provider == ModelProvider.ANTHROPIC:
            self.tool_schemas = [tool_to_anthropic_schema(tool) for tool in self.tools]
        else:
            raise ValueError(f"Unknown provider for model {self.config.model}")

        # Cost tracking
        self._total_cost_usd = 0.0
        self._last_session: Session | None = None

    def solve(self, task_input: str, deadline: float | None = None) -> str:
        """Solve a task using the multi-turn tool-calling loop.

        Args:
            task_input: The task description/question
            deadline: Unix timestamp when to stop and return current best answer

        Returns:
            The final text answer from the agent

        Raises:
            ValueError: If budget is exceeded
        """
        # Create session
        session = Session(model=self.config.model)
        self._last_session = session

        # Add task as user message
        session.add_user(task_input)

        # Multi-turn loop
        while session.turns < self.config.max_turns:
            # Check deadline
            if deadline is not None:
                remaining = deadline - time.time()
                if remaining < 2.0:
                    logger.info(f"Deadline approaching ({remaining:.1f}s left), returning current answer")
                    # Return whatever text we have
                    for msg in reversed(session.messages):
                        if msg.get("role") == "assistant" and msg.get("content"):
                            return msg["content"]
                    return "Task timed out with no answer."

            # Call LLM
            logger.info(f"Turn {session.turns + 1}: calling {self.config.model.value}")
            response: LLMResponse = self.backend.call(
                messages=session.messages,
                tools=self.tool_schemas,
                system_prompt=self.config.system_prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            # Record token usage
            session.record_usage(response.input_tokens, response.output_tokens)
            self._total_cost_usd += token_cost_usd(
                self.config.model,
                response.input_tokens,
                response.output_tokens,
            )

            # Check budget
            if self._total_cost_usd * 100 > self.config.budget_cents:
                raise ValueError(
                    f"Budget exceeded: ${self._total_cost_usd:.2f} > ${self.config.budget_cents / 100:.2f}"
                )

            # If no tool calls, return text
            if not response.tool_calls:
                logger.info(f"Turn {session.turns}: LLM returned text, ending loop")
                session.add_assistant(content=response.content)
                return response.content or "No response generated."

            # Execute tool calls
            logger.info(f"Turn {session.turns}: executing {len(response.tool_calls)} tool(s)")

            # Convert tool calls to OpenAI format for assistant message
            tool_calls_for_message = []
            for tool_call in response.tool_calls:
                tool_calls_for_message.append({
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": json.dumps(tool_call.arguments),
                    },
                })

            # Add assistant message with tool calls
            session.add_assistant(content=response.content, tool_calls=tool_calls_for_message)

            # Execute each tool
            for tool_call in response.tool_calls:
                tool = self._tool_map.get(tool_call.name)
                if tool is None:
                    result_output = f"Error: Tool '{tool_call.name}' not found"
                    logger.error(result_output)
                else:
                    try:
                        tool_result = tool.execute(**tool_call.arguments)
                        result_output = tool_result.output
                        if tool_result.error:
                            logger.warning(f"Tool {tool_call.name} error: {tool_result.error}")
                    except Exception as e:
                        result_output = f"Error executing {tool_call.name}: {str(e)}"
                        logger.error(result_output, exc_info=True)

                # Add tool result to session
                session.add_tool_result(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    output=result_output,
                )

        # Max turns reached
        logger.warning(f"Max turns ({self.config.max_turns}) reached")
        for msg in reversed(session.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                return msg["content"]
        return "Max turns reached with no answer."

    @property
    def total_cost_usd(self) -> float:
        """Total cost spent across all solves in USD."""
        return self._total_cost_usd

    @property
    def budget_remaining_cents(self) -> float:
        """Remaining budget in cents."""
        spent_cents = self._total_cost_usd * 100
        return max(0.0, self.config.budget_cents - spent_cents)

    @property
    def last_session(self) -> Session | None:
        """The most recent solve session (for inspection)."""
        return self._last_session
