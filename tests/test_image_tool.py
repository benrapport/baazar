"""Tests for the centralized image tool — cost catalog and model selection."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.image_tool import (
    get_cost, get_affordable_options, get_best_option,
    COST_CATALOG, PROMPT_REWRITE_COST,
)


# ── Cost catalog ─────────────────────────────────────────────────────

def test_catalog_has_entries():
    assert len(COST_CATALOG) > 10


def test_gpt_image_1_cost():
    assert get_cost("gpt-image-1", "1024x1024") == 0.020


def test_gpt_image_1_mini_cheapest():
    assert get_cost("gpt-image-1-mini", "1024x1024") == 0.009


def test_dalle3_standard():
    assert get_cost("dall-e-3", "1024x1024", "standard") == 0.040


def test_dalle3_hd():
    assert get_cost("dall-e-3", "1024x1024", "hd") == 0.080


def test_unknown_model_returns_high():
    assert get_cost("nonexistent-model") == 999.0


def test_quality_normalized_for_gpt_image():
    # gpt-image models always use "auto" regardless of what's passed
    assert get_cost("gpt-image-1", "1024x1024", "hd") == 0.020


# ── Affordable options ───────────────────────────────────────────────

def test_affordable_with_large_budget():
    options = get_affordable_options(1.0)
    assert len(options) == len(COST_CATALOG)


def test_affordable_with_tiny_budget():
    # $0.005 — nothing is affordable (cheapest is $0.009 + $0.001 rewrite)
    options = get_affordable_options(0.005)
    assert len(options) == 0


def test_affordable_sorted_by_cost():
    options = get_affordable_options(0.50)
    costs = [o["cost"] for o in options]
    assert costs == sorted(costs)


def test_affordable_includes_margin():
    options = get_affordable_options(0.10)
    for opt in options:
        assert opt["margin"] >= 0
        assert opt["margin"] == (0.10 - PROMPT_REWRITE_COST) - opt["cost"]


def test_affordable_excludes_expensive():
    # Budget $0.025 — should exclude dall-e-3 standard ($0.04)
    options = get_affordable_options(0.025)
    models = [o["model"] for o in options]
    assert "dall-e-3" not in models


# ── Best option ──────────────────────────────────────────────────────

def test_best_budget_picks_cheapest():
    opt = get_best_option(0.50, prefer="budget")
    assert opt is not None
    cheapest = min(COST_CATALOG.values())
    assert opt["cost"] == cheapest


def test_best_premium_picks_most_expensive_that_fits():
    opt = get_best_option(0.50, prefer="premium")
    assert opt is not None
    affordable = [c for c in COST_CATALOG.values() if c <= 0.50 - PROMPT_REWRITE_COST]
    assert opt["cost"] == max(affordable)


def test_best_balanced_picks_middle():
    opt = get_best_option(0.50, prefer="balanced")
    assert opt is not None
    # Should be somewhere in the middle, not cheapest or most expensive
    options = get_affordable_options(0.50)
    assert opt != options[0] or len(options) == 1
    assert opt != options[-1] or len(options) == 1


def test_best_returns_none_when_too_poor():
    assert get_best_option(0.005) is None


# ── Strategies file ──────���────────────────────────────��──────────────

def test_strategies_file_loads():
    import json
    path = Path(__file__).parent.parent / "agents" / "strategies.json"
    with open(path) as f:
        strategies = json.load(f)
    assert len(strategies) == 50


def test_strategies_have_required_fields():
    import json
    path = Path(__file__).parent.parent / "agents" / "strategies.json"
    with open(path) as f:
        strategies = json.load(f)
    for s in strategies:
        assert "id" in s
        assert "name" in s
        assert "aesthetic" in s
        assert "economic_strategy" in s
        assert "system_prompt" in s
        assert s["economic_strategy"] in ("budget", "balanced", "premium")
        assert len(s["system_prompt"]) > 50


def test_strategies_unique_ids():
    import json
    path = Path(__file__).parent.parent / "agents" / "strategies.json"
    with open(path) as f:
        strategies = json.load(f)
    ids = [s["id"] for s in strategies]
    assert len(ids) == len(set(ids))
