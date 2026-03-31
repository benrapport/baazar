from agent.tools.base import Tool, ToolResult, tool_to_openai_schema, tool_to_anthropic_schema
from agent.tools.python_exec import PythonExecTool
from agent.tools.think import ThinkTool
from agent.tools.math_eval import MathEvalTool
from agent.tools.search import SearchTool

BUILTIN_TOOLS: list[Tool] = [
    PythonExecTool(),
    ThinkTool(),
    MathEvalTool(),
    SearchTool(),
]
