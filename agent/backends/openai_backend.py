"""OpenAI backend implementation for the LLM agent."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from agent.backends.base import LLMBackend, LLMResponse, ToolCall


class OpenAIBackend(LLMBackend):
    """OpenAI chat completions backend with function calling."""

    def __init__(self, model: str, client: OpenAI | None = None):
        """Initialize the OpenAI backend.

        Args:
            model: OpenAI model name (e.g., "gpt-4o", "gpt-4.1-mini")
            client: Optional OpenAI client. If None, creates a new one.
        """
        self.model = model
        self.client = client or OpenAI()

    def call(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """Call the OpenAI API.

        Args:
            messages: Conversation history in OpenAI format.
                     May include "tool" role messages from session.add_tool_result().
            tools: Tools in OpenAI format from tool_to_openai_schema().
            system_prompt: System instruction string.
            max_tokens: Maximum response tokens.
            temperature: Sampling temperature.

        Returns:
            LLMResponse with content, tool_calls, tokens, and stop_reason.
        """
        # Build final messages list
        request_messages = []

        # Add system prompt as first message if provided
        if system_prompt:
            request_messages.append({"role": "system", "content": system_prompt})

        # Convert and add conversation messages
        for msg in messages:
            role = msg["role"]

            if role == "tool":
                # Tool result messages stay as-is, but need tool_call_id and name
                request_messages.append({
                    "role": "tool",
                    "tool_call_id": msg["tool_call_id"],
                    "content": msg.get("content", ""),
                })
            elif role == "assistant" and "tool_calls" in msg:
                # Assistant message with tool calls: convert back to OpenAI format
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "tool_calls": [],
                }
                if msg.get("content"):
                    assistant_msg["content"] = msg["content"]

                for tc in msg["tool_calls"]:
                    # tc may be in OpenAI format (from runtime) or flat format
                    if "function" in tc:
                        # Already in OpenAI format: {id, type, function: {name, arguments}}
                        assistant_msg["tool_calls"].append(tc)
                    else:
                        # Flat format: {id, name, arguments}
                        args = tc["arguments"]
                        if isinstance(args, dict):
                            args = json.dumps(args)
                        assistant_msg["tool_calls"].append({
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": args,
                            },
                        })
                request_messages.append(assistant_msg)
            else:
                # Regular user/assistant messages
                request_messages.append(msg)

        # Prepare API call kwargs
        # o-series models (o1, o3, o4-mini, etc.) use max_completion_tokens
        # and don't support temperature
        is_o_series = self.model.startswith("o") and len(self.model) > 1 and self.model[1].isdigit()
        api_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": request_messages,
        }
        if is_o_series:
            api_kwargs["max_completion_tokens"] = max_tokens
        else:
            api_kwargs["max_tokens"] = max_tokens
            api_kwargs["temperature"] = temperature

        # Only include tools if non-empty
        if tools:
            api_kwargs["tools"] = tools

        # Call the API
        response = self.client.chat.completions.create(**api_kwargs)

        # Parse response
        choice = response.choices[0]
        tool_calls_list: list[ToolCall] = []
        content: str | None = choice.message.content

        # Extract tool calls if present
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                if tc.type == "function":
                    # Parse arguments: OpenAI gives us a JSON string
                    # May be truncated if response hit max_tokens
                    try:
                        args: dict = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        # Truncated response — skip this tool call
                        continue
                    tool_calls_list.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args,
                    ))

        # Determine stop reason
        stop_reason = "end_turn"
        if choice.finish_reason == "tool_calls":
            stop_reason = "tool_use"
        elif choice.finish_reason == "length":
            stop_reason = "max_tokens"

        return LLMResponse(
            content=content,
            tool_calls=tool_calls_list,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            stop_reason=stop_reason,
        )
