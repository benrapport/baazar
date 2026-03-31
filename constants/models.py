"""Model registry: enums, provider mapping, and token pricing."""

from enum import Enum


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Model(str, Enum):
    # OpenAI — cheap
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_1_MINI = "gpt-4.1-mini"
    # OpenAI — mid
    GPT_4O = "gpt-4o"
    GPT_4_1 = "gpt-4.1"
    # OpenAI — reasoning
    O4_MINI = "o4-mini"
    # OpenAI — nano (judge only)
    GPT_5_4_NANO = "gpt-5.4-nano"
    # Anthropic
    CLAUDE_HAIKU = "claude-haiku-4-5-20251001"
    CLAUDE_SONNET = "claude-sonnet-4-6-20250514"


MODEL_PROVIDER: dict[Model, ModelProvider] = {
    Model.GPT_4O_MINI: ModelProvider.OPENAI,
    Model.GPT_4_1_MINI: ModelProvider.OPENAI,
    Model.GPT_4O: ModelProvider.OPENAI,
    Model.GPT_4_1: ModelProvider.OPENAI,
    Model.O4_MINI: ModelProvider.OPENAI,
    Model.GPT_5_4_NANO: ModelProvider.OPENAI,
    Model.CLAUDE_HAIKU: ModelProvider.ANTHROPIC,
    Model.CLAUDE_SONNET: ModelProvider.ANTHROPIC,
}


# (input_cost_per_1M_tokens, output_cost_per_1M_tokens) in USD
MODEL_COSTS: dict[Model, tuple[float, float]] = {
    Model.GPT_4O_MINI: (0.15, 0.60),
    Model.GPT_4_1_MINI: (0.40, 1.60),
    Model.GPT_4O: (2.50, 10.00),
    Model.GPT_4_1: (2.00, 8.00),
    Model.O4_MINI: (1.10, 4.40),
    Model.GPT_5_4_NANO: (0.10, 0.40),
    Model.CLAUDE_HAIKU: (0.80, 4.00),
    Model.CLAUDE_SONNET: (3.00, 15.00),
}


def token_cost_usd(model: Model, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for a given token usage."""
    inp, out = MODEL_COSTS[model]
    return (input_tokens * inp + output_tokens * out) / 1_000_000
