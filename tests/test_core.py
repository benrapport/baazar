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
    assert r.exchange.top_n == 1

def test_call_request_top_n():
    r = CallRequest(
        llm=LLMConfig(input="img"),
        exchange=ExchangeConfig(max_price=5.0, top_n=3),
    )
    assert r.exchange.top_n == 3

def test_submission():
    s = Submission(agent_id="a1", request_id="r1", work="done")
    assert s.revision == 0
    assert s.score is None

def test_game_state():
    g = GameState(request_id="r1", input="img",
                  max_price=5.0, min_quality=7, buyer_id="b1")
    assert g.winner is None
    assert g.done is False
    assert g.quality_criteria == []
    assert g.top_n == 1
    assert g.winners == []

def test_game_state_multi_fill():
    g = GameState(request_id="r1", input="img",
                  max_price=5.0, min_quality=7, buyer_id="b1",
                  top_n=3)
    assert g.top_n == 3


# ── Centralized Config ────────────────────────────────────────────────

def test_exchange_config_fee_rate():
    from exchange.config import ExchangeDefaults
    assert ExchangeDefaults.EXCHANGE_FEE_RATE == 0.015

def test_exchange_config_defaults():
    from exchange.config import ExchangeDefaults
    assert ExchangeDefaults.DEFAULT_TIMEOUT == 30.0
    assert ExchangeDefaults.DEFAULT_MIN_QUALITY == 6
    assert ExchangeDefaults.JUDGE_MODEL == "gpt-4o-mini"
    assert ExchangeDefaults.DEFAULT_TOP_N == 1


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

def test_exchange_fee_1_5_percent_of_fill_price():
    # 1.5% of $0.10 = $0.0015
    assert abs(calc_exchange_fee(0.10) - 0.0015) < 0.00001

def test_exchange_fee_scales_with_price():
    # 1.5% of $1.00 = $0.015
    assert abs(calc_exchange_fee(1.00) - 0.015) < 0.00001

def test_exchange_fee_zero_price():
    assert calc_exchange_fee(0.0) == 0.0

def test_ledger_record_and_query():
    ledger = Ledger()
    tx = ledger.record(
        request_id="r1", buyer_id="b1", agent_id="a1",
        price=0.05,
        score=8, latency_ms=200,
    )
    assert tx.price == 0.05
    assert abs(tx.exchange_fee - 0.00075) < 0.00001  # 1.5% of $0.05
    assert abs(tx.buyer_charged - 0.05075) < 0.00001

    all_txns = ledger.get_transactions()
    assert len(all_txns) == 1

    buyer_txns = ledger.get_transactions(buyer_id="b1")
    assert len(buyer_txns) == 1

    other_txns = ledger.get_transactions(buyer_id="b2")
    assert len(other_txns) == 0

def test_ledger_totals():
    ledger = Ledger()
    ledger.record("r1", "b1", "a1", 0.05, 8, 200)
    ledger.record("r2", "b1", "a2", 0.05, 7, 300)
    totals = ledger.get_totals()
    assert totals["total_transactions"] == 2
    assert abs(totals["total_volume"] - 0.10) < 0.001


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

    assert receive_submission(state, "a1", "output") is True
    assert "a1" in state.submissions

def test_receive_submission_rejects_when_done():
    from exchange.game import receive_submission
    state = GameState(request_id="r1", input="img",
                      max_price=5.0, min_quality=7, buyer_id="b1")
    state.done = True
    assert receive_submission(state, "a1", "output") is False

def test_receive_revision_increments():
    from exchange.game import receive_submission
    state = GameState(request_id="r1", input="img",
                      max_price=5.0, min_quality=7, buyer_id="b1")
    receive_submission(state, "a1", "v1")
    assert state.submissions["a1"].revision == 0
    receive_submission(state, "a1", "v2")
    assert state.submissions["a1"].revision == 1
    assert state.submissions["a1"].work == "v2"

def test_get_qualifiers():
    from exchange.game import _get_qualifiers
    state = GameState(request_id="r1", input="img",
                      max_price=5.0, min_quality=7, buyer_id="b1")
    state.submissions["a1"] = Submission(
        agent_id="a1", request_id="r1",
        work="good", score=8)
    state.submissions["a2"] = Submission(
        agent_id="a2", request_id="r1",
        work="bad", score=5)
    state.submissions["a3"] = Submission(
        agent_id="a3", request_id="r1",
        work="ok", score=7)

    qualifiers = _get_qualifiers(state)
    assert set(qualifiers) == {"a1", "a3"}

def test_select_winner_picks_earliest_timestamp():
    from exchange.game import _select_winner
    from exchange.types import Submission
    state = GameState(request_id="r1", input="img",
                      max_price=5.0, min_quality=7, buyer_id="b1")
    state.submissions["a1"] = Submission(
        agent_id="a1", request_id="r1",
        work="good", score=8, timestamp=1.0)
    state.submissions["a3"] = Submission(
        agent_id="a3", request_id="r1",
        work="ok", score=7, timestamp=2.0)

    result = _select_winner(state, ["a1", "a3"])
    assert result.agent_id == "a1"  # arrived first
    assert result.price == 5.0  # fill price = max_price


def test_broadcast_payload_includes_top_n():
    p = BroadcastPayload(
        request_id="r1", input="test", max_price=1.0,
        min_quality=6, top_n=3, deadline_unix=100.0,
    )
    assert p.top_n == 3

def test_broadcast_payload_no_agent_info():
    """Broadcast must NOT contain any agent-identifying information."""
    p = BroadcastPayload(
        request_id="r1", input="test", max_price=1.0,
        min_quality=6, deadline_unix=100.0,
    )
    data = p.model_dump()
    # No agent_id, no agent list, no competitor info
    assert "agent_id" not in data
    assert "agents" not in data
    assert "agents_invited" not in data

def test_agent_notification_types():
    from bazaar.types import AgentNotification
    fill = AgentNotification(agent_id="a1", decision="fill")
    assert fill.decision == "fill"
    pas = AgentNotification(agent_id="a1", decision="pass", reason="too expensive")
    assert pas.reason == "too expensive"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
