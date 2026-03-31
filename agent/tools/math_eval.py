"""Safe mathematical expression evaluation."""

from __future__ import annotations

import ast
import math
from typing import Any

from .base import ToolResult


class MathEvalTool:
    """Safely evaluates mathematical expressions."""

    @property
    def name(self) -> str:
        return "math_eval"

    @property
    def description(self) -> str:
        return "Evaluate mathematical expressions safely"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate",
                }
            },
            "required": ["expression"],
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        """Evaluate a mathematical expression safely."""
        expression = kwargs.get("expression", "")
        if not expression:
            return ToolResult(output="", error="No expression provided")

        try:
            # First try ast.literal_eval for simple expressions
            result = ast.literal_eval(expression)
            return ToolResult(output=str(result), error=None)
        except (ValueError, SyntaxError):
            # Fall back to eval with restricted globals (math module only)
            try:
                safe_globals = {
                    "__builtins__": {},
                    "math": math,
                    "sin": math.sin,
                    "cos": math.cos,
                    "tan": math.tan,
                    "sqrt": math.sqrt,
                    "pi": math.pi,
                    "e": math.e,
                    "log": math.log,
                    "exp": math.exp,
                    "abs": abs,
                    "pow": pow,
                }
                result = eval(expression, safe_globals, {})
                return ToolResult(output=str(result), error=None)
            except Exception as e:
                return ToolResult(output="", error=f"Evaluation error: {str(e)}")
