from agent.backends.base import LLMBackend, LLMResponse, ToolCall
from agent.backends.openai_backend import OpenAIBackend
from agent.backends.anthropic_backend import AnthropicBackend
from constants.models import Model, ModelProvider, MODEL_PROVIDER


def create_backend(model: Model) -> LLMBackend:
    """Factory: create the right backend for a given model."""
    provider = MODEL_PROVIDER[model]
    if provider == ModelProvider.OPENAI:
        return OpenAIBackend(model=model.value)
    elif provider == ModelProvider.ANTHROPIC:
        return AnthropicBackend(model=model.value)
    raise ValueError(f"Unknown provider for model {model}")
