"""LLM backend protocol — abstraction over OpenAI / Anthropic APIs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ToolCall:
    """A tool call requested by the LLM."""
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    """Unified response from any LLM backend."""
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = "end_turn"  # "end_turn", "tool_use", "max_tokens"


@runtime_checkable
class LLMBackend(Protocol):
    """Protocol for LLM API backends."""

    def call(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> LLMResponse: ...
