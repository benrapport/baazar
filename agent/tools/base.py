"""Tool protocol and helpers for the agent tool-calling system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ToolResult:
    """Result of executing a tool."""
    output: str
    error: str | None = None


@runtime_checkable
class Tool(Protocol):
    """Protocol that all tools must implement."""

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def input_schema(self) -> dict: ...

    def execute(self, **kwargs: Any) -> ToolResult: ...


def tool_to_openai_schema(tool: Tool) -> dict:
    """Convert a Tool to OpenAI function-calling schema."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }


def tool_to_anthropic_schema(tool: Tool) -> dict:
    """Convert a Tool to Anthropic tool_use schema."""
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }
