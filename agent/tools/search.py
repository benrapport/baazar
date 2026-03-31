"""Text search within provided content."""

from __future__ import annotations

from typing import Any

from .base import ToolResult


class SearchTool:
    """Case-insensitive line-based text search."""

    @property
    def name(self) -> str:
        return "search_text"

    @property
    def description(self) -> str:
        return "Search for lines matching a query in provided text (case-insensitive)"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (case-insensitive)",
                },
                "text": {
                    "type": "string",
                    "description": "Text to search in",
                },
            },
            "required": ["query", "text"],
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        """Search for matching lines in text."""
        query = kwargs.get("query", "")
        text = kwargs.get("text", "")

        if not query or not text:
            return ToolResult(output="", error="Both query and text are required")

        query_lower = query.lower()
        lines = text.split("\n")
        matches = []

        for line_num, line in enumerate(lines, start=1):
            if query_lower in line.lower():
                matches.append(f"{line_num}: {line}")

        if matches:
            output = "\n".join(matches)
            return ToolResult(output=output, error=None)
        else:
            return ToolResult(output="No matches found", error=None)
