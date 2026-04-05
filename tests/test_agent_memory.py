"""Tests for agent learning memory — replay buffer and few-shot context."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.memory import AgentMemory, Attempt


# ── Basic recording ──────────────────────────────────────────────────

def test_record_attempt_and_score():
    mem = AgentMemory()
    mem.record_attempt("req1", "draw a cat", "a fluffy cat in watercolor", "gpt-image-1")
    mem.record_score("req1", 8, "Good detail", won=True)
    assert len(mem.scored_attempts) == 1
    assert mem.scored_attempts[0].score == 8
    assert mem.scored_attempts[0].won is True


def test_unscored_attempt_not_in_scored():
    mem = AgentMemory()
    mem.record_attempt("req1", "draw a cat", "fluffy cat", "gpt-image-1")
    # Never score it
    assert len(mem.scored_attempts) == 0


def test_score_unknown_request_is_noop():
    mem = AgentMemory()
    mem.record_score("nonexistent", 8)
    assert len(mem.attempts) == 0


def test_eviction_at_max():
    mem = AgentMemory(max_entries=5)
    for i in range(10):
        mem.record_attempt(f"req{i}", f"task {i}", f"rewrite {i}", "model")
        mem.record_score(f"req{i}", i)
    assert len(mem.attempts) == 5
    # Should keep the last 5 (scores 5-9)
    assert mem.attempts[0].score == 5
    assert mem.attempts[-1].score == 9


# ── Best / worst selection ───────────────────────────────────────────

def test_get_best():
    mem = AgentMemory()
    for i, score in enumerate([3, 7, 9, 5, 8]):
        mem.record_attempt(f"req{i}", f"task", f"rewrite {i}", "model")
        mem.record_score(f"req{i}", score)
    best = mem.get_best(2)
    assert len(best) == 2
    assert best[0].score == 9
    assert best[1].score == 8


def test_get_worst():
    mem = AgentMemory()
    for i, score in enumerate([3, 7, 9, 5, 8]):
        mem.record_attempt(f"req{i}", f"task", f"rewrite {i}", "model")
        mem.record_score(f"req{i}", score)
    worst = mem.get_worst(2)
    assert len(worst) == 2
    assert worst[0].score == 3
    assert worst[1].score == 5


def test_get_best_empty_memory():
    mem = AgentMemory()
    assert mem.get_best(3) == []


# ── Stats ────────────────────────────────────────────────────────────

def test_avg_score():
    mem = AgentMemory()
    for i, score in enumerate([6, 8, 10]):
        mem.record_attempt(f"req{i}", "t", "r", "m")
        mem.record_score(f"req{i}", score)
    assert mem.get_avg_score() == 8.0


def test_avg_score_empty():
    mem = AgentMemory()
    assert mem.get_avg_score() is None


def test_win_rate():
    mem = AgentMemory()
    for i in range(4):
        mem.record_attempt(f"req{i}", "t", "r", "m")
        mem.record_score(f"req{i}", 7, won=(i < 1))
    assert mem.get_win_rate() == 0.25


def test_win_rate_empty():
    mem = AgentMemory()
    assert mem.get_win_rate() is None


# ── Context building ─────────────────────────────────────────────────

def test_build_context_empty():
    mem = AgentMemory()
    assert mem.build_context() == ""


def test_build_context_has_stats():
    mem = AgentMemory()
    for i in range(3):
        mem.record_attempt(f"req{i}", f"task {i}", f"rewrite {i}", "model")
        mem.record_score(f"req{i}", 7 + i, won=(i == 2))
    ctx = mem.build_context()
    assert "3 tasks scored" in ctx
    assert "avg score 8.0/10" in ctx
    assert "win rate 33%" in ctx


def test_build_context_has_best_examples():
    mem = AgentMemory()
    mem.record_attempt("req0", "draw a sunset", "golden sunset over ocean", "gpt-image-1")
    mem.record_score("req0", 9, "Beautiful composition", won=True)
    mem.record_attempt("req1", "draw a tree", "bare oak in winter", "gpt-image-1")
    mem.record_score("req1", 4, "Too simple")
    ctx = mem.build_context()
    assert "BEST rewrites" in ctx
    assert "golden sunset" in ctx
    assert "WORST rewrites" in ctx
    assert "bare oak" in ctx


def test_build_context_includes_judge_feedback():
    mem = AgentMemory()
    mem.record_attempt("req0", "cat", "fluffy cat", "m")
    mem.record_score("req0", 9, "Excellent detail and composition")
    ctx = mem.build_context()
    assert "Excellent detail" in ctx
