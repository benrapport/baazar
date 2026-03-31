"""Session state: message history, token accounting, cost tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from constants.models import Model, token_cost_usd


@dataclass
class Session:
    """Tracks a single agent solve session (one task)."""

    model: Model
    messages: list[dict] = field(default_factory=list)
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def cost_usd(self) -> float:
        return token_cost_usd(self.model, self.input_tokens, self.output_tokens)

    @property
    def elapsed_s(self) -> float:
        return time.time() - self.start_time

    def add_user(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str | None, tool_calls: list[dict] | None = None):
        msg: dict = {"role": "assistant"}
        if content:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, name: str, output: str):
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": output,
        })

    def record_usage(self, input_tokens: int, output_tokens: int):
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.turns += 1
