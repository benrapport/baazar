"""Centralized image generation tool — single source of truth for costs and API calls.

All agents import this module. It knows every model/size/quality combo,
their exact costs, and handles the actual API call.
"""

from __future__ import annotations
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# ── Cost catalog ─────────────────────────────────────────────────────
# Source: OpenAI pricing page, April 2026
# Format: (model, size, quality) → price in USD

COST_CATALOG: dict[tuple[str, str, str], float] = {
    # DALL-E 3
    ("dall-e-3", "1024x1024", "standard"): 0.040,
    ("dall-e-3", "1024x1024", "hd"):       0.080,
    ("dall-e-3", "1024x1792", "standard"): 0.080,
    ("dall-e-3", "1024x1792", "hd"):       0.120,
    ("dall-e-3", "1792x1024", "standard"): 0.080,
    ("dall-e-3", "1792x1024", "hd"):       0.120,
    # DALL-E 2
    ("dall-e-2", "1024x1024", "standard"): 0.020,
    ("dall-e-2", "512x512", "standard"):   0.018,
    ("dall-e-2", "256x256", "standard"):   0.016,
    # gpt-image-1
    ("gpt-image-1", "1024x1024", "auto"):  0.020,
    ("gpt-image-1", "1024x1792", "auto"):  0.030,
    ("gpt-image-1", "1792x1024", "auto"):  0.030,
    # gpt-image-1-mini
    ("gpt-image-1-mini", "1024x1024", "auto"): 0.009,
    ("gpt-image-1-mini", "1024x1792", "auto"): 0.013,
    ("gpt-image-1-mini", "1792x1024", "auto"): 0.013,
    # gpt-image-1.5
    ("gpt-image-1.5", "1024x1024", "auto"): 0.025,
    ("gpt-image-1.5", "1024x1792", "auto"): 0.038,
    ("gpt-image-1.5", "1792x1024", "auto"): 0.038,
}

# Prompt rewriting cost (gpt-4o-mini, ~200 input + 200 output tokens)
PROMPT_REWRITE_COST = 0.001

# ── Helper lookups ───────────────────────────────────────────────────

def get_cost(model: str, size: str = "1024x1024", quality: str = "auto") -> float:
    """Get the USD cost for a specific model/size/quality combo."""
    # Normalize quality for models that only support specific values
    if model.startswith("gpt-image"):
        quality = "auto"
    elif model == "dall-e-2":
        quality = "standard"
    return COST_CATALOG.get((model, size, quality), 999.0)


def get_affordable_options(budget: float) -> list[dict]:
    """Return all model configs that fit within budget (after prompt rewrite cost).

    Returns list of {model, size, quality, cost, margin} sorted by quality tier
    then by margin (most profitable first).
    """
    available = budget - PROMPT_REWRITE_COST
    options = []
    for (model, size, quality), cost in COST_CATALOG.items():
        if cost <= available:
            options.append({
                "model": model,
                "size": size,
                "quality": quality,
                "cost": cost,
                "margin": available - cost,
            })
    # Sort: cheapest first (most margin)
    options.sort(key=lambda x: x["cost"])
    return options


def get_best_option(budget: float, prefer: str = "balanced") -> dict | None:
    """Pick the best model config for a given budget and preference.

    prefer:
        "budget"   — cheapest option (maximize margin)
        "balanced" — mid-range option
        "premium"  — most expensive option that fits
    """
    options = get_affordable_options(budget)
    if not options:
        return None

    if prefer == "budget":
        return options[0]
    elif prefer == "premium":
        return options[-1]
    else:  # balanced
        mid = len(options) // 2
        return options[mid]


# ── Image generation ─────────────────────────────────────────────────

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def generate_image(prompt: str, model: str = "gpt-image-1",
                   size: str = "1024x1024",
                   quality: str = "auto") -> str:
    """Generate an image and return a data URI string.

    Args:
        prompt: The image generation prompt
        model: One of dall-e-2, dall-e-3, gpt-image-1, gpt-image-1-mini, gpt-image-1.5
        size: Image dimensions (1024x1024, 1024x1792, 1792x1024, etc.)
        quality: "standard", "hd", or "auto"

    Returns:
        data:image/png;base64,... string
    """
    client = _get_client()

    kwargs: dict = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }

    # DALL-E 3 supports quality param and needs response_format
    if model == "dall-e-3":
        kwargs["quality"] = quality if quality in ("standard", "hd") else "standard"
        kwargs["response_format"] = "b64_json"

    resp = client.images.generate(**kwargs)
    b64 = resp.data[0].b64_json
    if not b64:
        raise ValueError(f"No b64_json in response from {model}")

    return f"data:image/png;base64,{b64}"
