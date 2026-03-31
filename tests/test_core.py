"""Core unit tests for the exchange."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from exchange.types import RegisteredAgent, Submission, Transaction, GameState
from exchange.registry import Registry
from exchange.settlement import Ledger, calc_exchange_fee
from exchange.judge import parse_json
from bazaar.types import (
    ExchangeResult, CallRequest, LLMConfig, ExchangeConfig, BroadcastPayload,
)


# ── Types ─────────────────────────────────────────────────────────────

def test_exchange_result():
    r = ExchangeResult(output="hello", agent_id="a1", price=0.5, latency_ms=100)
    assert r.output == "hello"
    assert r.score is None

def test_call_request_defaults():
    r = CallRequest(
        llm=LLMConfig(input="img"),
        exchange=ExchangeConfig(max_price=5.0),
    )
    assert r.exchange.judge.min_quality == 6
    assert r.exchange.timeout == 30.0

def test_submission():
    s = Submission(agent_id="a1", request_id="r1", bid=1.0, work="done")
    assert s.revision == 0
    assert s.score is None

def test_game_state():
    g = GameState(request_id="r1", input="img",
                  max_price=5.0, min_quality=7, buyer_id="b1")
    assert g.winner is None
    assert g.done is False
    assert g.quality_criteria == []


# ── Registry ──────────────────────────────────────────────────────────

def test_registry_register_and_lookup():
    reg = Registry()
    reg.register("a1", "http://localhost:9001")
    reg.register("a2", "http://localhost:9002")
    reg.register("a3", "http://localhost:9003")

    agents = reg.get_active_agents()
    assert len(agents) == 3
    assert {a.agent_id for a in agents} == {"a1", "a2", "a3"}

def test_registry_unregister():
    reg = Registry()
    reg.register("a1", "http://localhost:9001")
    assert reg.count == 1
    reg.unregister("a1")
    assert reg.count == 0
    assert reg.get_active_agents() == []

def test_registry_returns_all_no_filtering():
    """Key test: registry returns ALL agents, no filtering."""
    reg = Registry()
    for i in range(20):
        reg.register(f"a{i}", f"http://localhost:{9000+i}")
    agents = reg.get_active_agents()
    assert len(agents) == 20


# ── Settlement ────────────────────────────────────────────────────────

def test_exchange_fee_20_percent_of_spread():
    # 20% of ($0.10 - $0.06) = 20% of $0.04 = $0.008
    assert abs(calc_exchange_fee(0.10, 0.06) - 0.008) < 0.0001

def test_exchange_fee_capped_at_1_cent():
    # 20% of ($1.00 - $0.02) = $0.196, capped at $0.01
    assert abs(calc_exchange_fee(1.00, 0.02) - 0.01) < 0.0001

def test_exchange_fee_zero_spread():
    assert calc_exchange_fee(0.05, 0.05) == 0.0

def test_ledger_record_and_query():
    ledger = Ledger()
    tx = ledger.record(
        request_id="r1", buyer_id="b1", agent_id="a1",
        price=0.03, buyer_ask=0.05,
        score=8, latency_ms=200,
    )
    assert tx.price == 0.03
    assert abs(tx.exchange_fee - 0.004) < 0.0001  # 20% of $0.02 spread
    assert abs(tx.buyer_charged - 0.034) < 0.0001

    all_txns = ledger.get_transactions()
    assert len(all_txns) == 1

    buyer_txns = ledger.get_transactions(buyer_id="b1")
    assert len(buyer_txns) == 1

    other_txns = ledger.get_transactions(buyer_id="b2")
    assert len(other_txns) == 0

def test_ledger_totals():
    ledger = Ledger()
    ledger.record("r1", "b1", "a1", 0.03, 0.05, 8, 200)
    ledger.record("r2", "b1", "a2", 0.02, 0.05, 7, 300)
    totals = ledger.get_totals()
    assert totals["total_transactions"] == 2
    assert abs(totals["total_volume"] - 0.05) < 0.001


# ── Judge (parse_json only — no API calls) ────────────────────────────

def test_parse_json_plain():
    assert parse_json('{"score": 7}')["score"] == 7

def test_parse_json_fenced():
    assert parse_json('```json\n{"x": 1}\n```')["x"] == 1

def test_parse_json_with_preamble():
    assert parse_json('Here is my answer:\n{"x": 1}\nDone.')["x"] == 1

def test_parse_json_nested():
    r = parse_json('{"scores": {"a1": {"score": 8, "feedback": "good"}}}')
    assert r["scores"]["a1"]["score"] == 8

def test_parse_json_empty_raises():
    try:
        parse_json("")
        assert False, "should raise"
    except ValueError:
        pass

def test_parse_json_no_json_raises():
    try:
        parse_json("no json here")
        assert False, "should raise"
    except (ValueError, Exception):
        pass


# ── Game logic (unit, no network) ─────────────────────────────────────

def test_receive_submission():
    from exchange.game import receive_submission
    state = GameState(request_id="r1", input="img",
                      max_price=5.0, min_quality=7, buyer_id="b1")

    assert receive_submission(state, "a1", 3.0, "output") is True
    assert "a1" in state.submissions
    assert state.submissions["a1"].bid == 3.0

def test_receive_submission_rejects_over_max_price():
    from exchange.game import receive_submission
    state = GameState(request_id="r1", input="img",
                      max_price=5.0, min_quality=7, buyer_id="b1")
    assert receive_submission(state, "a1", 6.0, "output") is False

def test_receive_submission_rejects_when_done():
    from exchange.game import receive_submission
    state = GameState(request_id="r1", input="img",
                      max_price=5.0, min_quality=7, buyer_id="b1")
    state.done = True
    assert receive_submission(state, "a1", 3.0, "output") is False

def test_receive_revision_increments():
    from exchange.game import receive_submission
    state = GameState(request_id="r1", input="img",
                      max_price=5.0, min_quality=7, buyer_id="b1")
    receive_submission(state, "a1", 3.0, "v1")
    assert state.submissions["a1"].revision == 0
    receive_submission(state, "a1", 3.0, "v2")
    assert state.submissions["a1"].revision == 1
    assert state.submissions["a1"].work == "v2"

def test_get_qualifiers():
    from exchange.game import _get_qualifiers
    state = GameState(request_id="r1", input="img",
                      max_price=5.0, min_quality=7, buyer_id="b1")
    state.submissions["a1"] = Submission(
        agent_id="a1", request_id="r1", bid=3.0,
        work="good", score=8)
    state.submissions["a2"] = Submission(
        agent_id="a2", request_id="r1", bid=2.0,
        work="bad", score=5)
    state.submissions["a3"] = Submission(
        agent_id="a3", request_id="r1", bid=1.0,
        work="ok", score=7)

    qualifiers = _get_qualifiers(state)
    assert set(qualifiers) == {"a1", "a3"}

def test_select_winner_picks_earliest_timestamp():
    from exchange.game import _select_winner
    from exchange.types import Submission
    state = GameState(request_id="r1", input="img",
                      max_price=5.0, min_quality=7, buyer_id="b1")
    state.submissions["a1"] = Submission(
        agent_id="a1", request_id="r1", bid=3.0,
        work="good", score=8, timestamp=1.0)
    state.submissions["a3"] = Submission(
        agent_id="a3", request_id="r1", bid=1.0,
        work="ok", score=7, timestamp=2.0)

    result = _select_winner(state, ["a1", "a3"])
    assert result.agent_id == "a1"  # arrived first
    assert result.price == 3.0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
