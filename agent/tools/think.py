"""Reasoning scratchpad tool."""

from __future__ import annotations

from typing import Any

from .base import ToolResult


class ThinkTool:
    """Identity function for agent reasoning and scratchpad work."""

    @property
    def name(self) -> str:
        return "think"

    @property
    def description(self) -> str:
        return "Internal reasoning scratchpad - returns the thought as-is for agent planning"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "Internal thought or reasoning",
                }
            },
            "required": ["thought"],
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        """Return the thought as-is (identity function)."""
        thought = kwargs.get("thought", "")
        return ToolResult(output=thought, error=None)
