"""Anthropic backend implementation for the LLM agent."""

from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic

from agent.backends.base import LLMBackend, LLMResponse, ToolCall


class AnthropicBackend(LLMBackend):
    """Anthropic messages API backend with tool_use."""

    def __init__(self, model: str, client: Anthropic | None = None):
        """Initialize the Anthropic backend.

        Args:
            model: Anthropic model name (e.g., "claude-sonnet-4-6-20250514")
            client: Optional Anthropic client. If None, creates a new one.
        """
        self.model = model
        self.client = client or Anthropic()

    def call(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """Call the Anthropic API.

        Args:
            messages: Conversation history in OpenAI format.
                     May include "tool" role messages from session.add_tool_result().
            tools: Tools in Anthropic format from tool_to_anthropic_schema().
            system_prompt: System instruction string.
            max_tokens: Maximum response tokens.
            temperature: Sampling temperature.

        Returns:
            LLMResponse with content, tool_calls, tokens, and stop_reason.
        """
        # Convert messages from OpenAI format to Anthropic format
        request_messages = []

        for msg in messages:
            role = msg["role"]

            if role == "tool":
                # Convert tool result message to Anthropic format
                # These appear in the messages list as tool_result blocks
                request_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg["tool_call_id"],
                        "content": msg.get("content", ""),
                    }],
                })
            elif role == "assistant" and "tool_calls" in msg:
                # Convert assistant message with tool calls to Anthropic format
                content: list[dict[str, Any]] = []

                if msg.get("content"):
                    content.append({
                        "type": "text",
                        "text": msg["content"],
                    })

                for tc in msg["tool_calls"]:
                    # tc is a dict with id, name, arguments (dict or string)
                    args = tc["arguments"]
                    if isinstance(args, str):
                        args = json.loads(args)

                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": args,
                    })

                request_messages.append({
                    "role": "assistant",
                    "content": content,
                })
            else:
                # Regular user/assistant messages: pass through mostly as-is
                if role == "system":
                    # Anthropic doesn't have a system role in messages; skip it
                    # (handled via system parameter)
                    continue

                request_messages.append(msg)

        # Prepare API call kwargs
        api_kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": request_messages,
        }

        # System prompt goes in the system parameter, not as a message
        if system_prompt:
            api_kwargs["system"] = system_prompt

        # Only include tools if non-empty
        if tools:
            api_kwargs["tools"] = tools

        # Call the API
        response = self.client.messages.create(**api_kwargs)

        # Parse response
        tool_calls_list: list[ToolCall] = []
        text_blocks = []

        # Extract content blocks
        for block in response.content:
            if block.type == "text":
                text_blocks.append(block.text)
            elif block.type == "tool_use":
                # block.input is already a dict from Anthropic
                tool_calls_list.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input,
                ))

        # Combine text blocks into single content string
        content = "\n".join(text_blocks) if text_blocks else None

        # Determine stop reason
        stop_reason = "end_turn"
        if response.stop_reason == "tool_use":
            stop_reason = "tool_use"
        elif response.stop_reason == "max_tokens":
            stop_reason = "max_tokens"

        return LLMResponse(
            content=content,
            tool_calls=tool_calls_list,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=stop_reason,
        )
