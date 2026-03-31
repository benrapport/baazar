"""Execute Python code in a subprocess sandbox."""

from __future__ import annotations

import subprocess
from typing import Any

from .base import ToolResult


class PythonExecTool:
    """Executes Python code in a subprocess with a 10-second timeout."""

    @property
    def name(self) -> str:
        return "execute_python"

    @property
    def description(self) -> str:
        return "Execute Python code in a subprocess sandbox with 10-second timeout"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                }
            },
            "required": ["code"],
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute Python code and return output."""
        code = kwargs.get("code", "")
        if not code:
            return ToolResult(output="", error="No code provided")

        try:
            result = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                timeout=10,
                text=True,
            )
            output = result.stdout + result.stderr
            error = None if result.returncode == 0 else result.stderr
            return ToolResult(output=output, error=error)
        except subprocess.TimeoutExpired:
            return ToolResult(output="", error="Code execution timed out after 10 seconds")
        except Exception as e:
            return ToolResult(output="", error=f"Execution error: {str(e)}")
