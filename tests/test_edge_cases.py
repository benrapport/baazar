"""Comprehensive edge case tests for the AI Agent Exchange."""

import sys
import json
import time
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from exchange.types import RegisteredAgent, Submission, GameState, Transaction
from exchange.registry import Registry
from exchange.settlement import Ledger, calc_exchange_fee
from exchange.judge import Judge, parse_json, _clamp_score, _truncate
from exchange.game import receive_submission, _get_qualifiers, _select_winner
from agentx.types import ExchangeResult, CallRequest, SubmissionPayload
from agentx.client import Exchange


# ═══════════════════════════════════════════════════════════════════════
# REGISTRY EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

class TestRegistry:
    def test_duplicate_registration_overwrites(self):
        reg = Registry()
        reg.register("a1", ["ocr"], "http://old")
        reg.register("a1", ["ocr", "translate"], "http://new")
        assert reg.count == 1
        agent = reg.get_agent("a1")
        assert agent.callback_url == "http://new"
        assert "translate" in agent.capabilities

    def test_empty_capabilities(self):
        reg = Registry()
        reg.register("a1", [], "http://x")
        assert reg.get_agents_for_capability("ocr") == []
        assert reg.count == 1

    def test_special_characters_in_agent_id(self):
        reg = Registry()
        reg.register("a!@#$%^&*()", ["ocr"], "http://x")
        agent = reg.get_agent("a!@#$%^&*()")
        assert agent is not None

    def test_long_agent_id(self):
        reg = Registry()
        long_id = "x" * 10000
        reg.register(long_id, ["ocr"], "http://x")
        assert reg.get_agent(long_id) is not None

    def test_unregister_nonexistent(self):
        reg = Registry()
        assert reg.unregister("ghost") is False

    def test_unregister_then_lookup(self):
        reg = Registry()
        reg.register("a1", ["ocr"], "http://x")
        reg.unregister("a1")
        assert reg.get_agent("a1") is None
        assert reg.get_agents_for_capability("ocr") == []

    def test_lookup_nonexistent_capability(self):
        reg = Registry()
        reg.register("a1", ["ocr"], "http://x")
        assert reg.get_agents_for_capability("legal") == []

    def test_returns_all_agents_no_filtering(self):
        """Key invariant: registry returns ALL agents, no filtering."""
        reg = Registry()
        for i in range(50):
            reg.register(f"a{i}", ["ocr"], f"http://host{i}")
        assert len(reg.get_agents_for_capability("ocr")) == 50

    def test_concurrent_registration(self):
        reg = Registry()
        errors = []

        def register_agent(i):
            try:
                reg.register(f"a{i}", ["ocr"], f"http://host{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_agent, args=(i,))
                   for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert reg.count == 100

    def test_concurrent_register_and_unregister(self):
        reg = Registry()
        for i in range(50):
            reg.register(f"a{i}", ["ocr"], f"http://host{i}")

        errors = []

        def unregister(i):
            try:
                reg.unregister(f"a{i}")
            except Exception as e:
                errors.append(e)

        def register_new(i):
            try:
                reg.register(f"new{i}", ["ocr"], f"http://new{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(50):
            threads.append(threading.Thread(target=unregister, args=(i,)))
            threads.append(threading.Thread(target=register_new, args=(i,)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert reg.count == 50  # 50 old removed, 50 new added

    def test_inactive_agent_not_returned(self):
        reg = Registry()
        agent = reg.register("a1", ["ocr"], "http://x")
        # Manually mark inactive
        agent.status = "inactive"
        assert reg.get_agents_for_capability("ocr") == []

    def test_multiple_capabilities_per_agent(self):
        reg = Registry()
        reg.register("a1", ["ocr", "translate", "summarize"], "http://x")
        assert len(reg.get_agents_for_capability("ocr")) == 1
        assert len(reg.get_agents_for_capability("translate")) == 1
        assert len(reg.get_agents_for_capability("summarize")) == 1
        assert len(reg.get_agents_for_capability("code")) == 0


# ═══════════════════════════════════════════════════════════════════════
# JUDGE EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

class TestParseJson:
    def test_plain_json(self):
        assert parse_json('{"score": 7}')["score"] == 7

    def test_fenced_json(self):
        assert parse_json('```json\n{"x": 1}\n```')["x"] == 1

    def test_fenced_no_closing(self):
        assert parse_json('```json\n{"x": 1}')["x"] == 1

    def test_preamble_json(self):
        assert parse_json('Here is my answer:\n{"x": 1}\nDone.')["x"] == 1

    def test_nested_json(self):
        r = parse_json('{"scores": {"a1": {"score": 8}}}')
        assert r["scores"]["a1"]["score"] == 8

    def test_deeply_nested(self):
        r = parse_json('{"a": {"b": {"c": {"d": 1}}}}')
        assert r["a"]["b"]["c"]["d"] == 1

    def test_unicode(self):
        r = parse_json('{"text": "中文"}')
        assert r["text"] == "中文"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_json("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            parse_json("   \n\t  ")

    def test_no_json_raises(self):
        with pytest.raises(ValueError):
            parse_json("just plain text, no json here")

    def test_multiple_json_objects_returns_first(self):
        r = parse_json('{"a": 1}\n{"b": 2}')
        assert "a" in r

    def test_json_with_trailing_text(self):
        r = parse_json('{"score": 7} and some more text after')
        assert r["score"] == 7

    def test_json_with_escaped_quotes(self):
        r = parse_json('{"text": "he said \\"hello\\""}')
        assert "hello" in r["text"]


class TestClampScore:
    def test_normal_range(self):
        assert _clamp_score(7) == 7

    def test_below_minimum(self):
        assert _clamp_score(0) == 1
        assert _clamp_score(-5) == 1

    def test_above_maximum(self):
        assert _clamp_score(15) == 10
        assert _clamp_score(100) == 10

    def test_boundary_values(self):
        assert _clamp_score(1) == 1
        assert _clamp_score(10) == 10

    def test_none_returns_1(self):
        assert _clamp_score(None) == 1

    def test_string_number(self):
        assert _clamp_score("7") == 7

    def test_string_non_number(self):
        assert _clamp_score("abc") == 1

    def test_float_truncated(self):
        assert _clamp_score(7.9) == 7

    def test_bool(self):
        assert _clamp_score(True) == 1  # int(True) == 1


class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("hello") == "hello"

    def test_long_text_truncated(self):
        result = _truncate("x" * 100, max_chars=50)
        assert len(result) < 100
        assert "truncated" in result

    def test_exactly_at_limit(self):
        text = "x" * 50
        assert _truncate(text, max_chars=50) == text

    def test_empty_string(self):
        assert _truncate("") == ""


class TestJudge:
    def _mock_judge(self, response_content: str):
        client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = response_content
        client.chat.completions.create.return_value = mock_resp
        return Judge(client=client)

    def test_normal_score(self):
        judge = self._mock_judge('{"score": 8, "feedback": "Good work"}')
        sub = Submission(agent_id="a1", request_id="r1",
                         bid=1.0, work="2+2=4")
        result = judge.score_submission("What is 2+2?", sub)
        assert result["score"] == 8
        assert result["feedback"] == "Good work"

    def test_score_out_of_range_clamped(self):
        judge = self._mock_judge('{"score": 15, "feedback": "wow"}')
        sub = Submission(agent_id="a1", request_id="r1",
                         bid=1.0, work="answer")
        result = judge.score_submission("task", sub)
        assert result["score"] == 10  # clamped

    def test_score_null_returns_1(self):
        judge = self._mock_judge('{"score": null, "feedback": "bad"}')
        sub = Submission(agent_id="a1", request_id="r1",
                         bid=1.0, work="answer")
        result = judge.score_submission("task", sub)
        assert result["score"] == 1

    def test_malformed_json_returns_fallback(self):
        judge = self._mock_judge("not json at all")
        sub = Submission(agent_id="a1", request_id="r1",
                         bid=1.0, work="answer")
        result = judge.score_submission("task", sub)
        assert result["score"] == 1
        assert "error" in result["feedback"].lower() or "Judge" in result["feedback"]

    def test_api_timeout_returns_fallback(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = TimeoutError("timeout")
        judge = Judge(client=client)
        sub = Submission(agent_id="a1", request_id="r1",
                         bid=1.0, work="answer")
        result = judge.score_submission("task", sub)
        assert result["score"] == 1
        assert "error" in result["feedback"].lower() or "timeout" in result["feedback"].lower()

    def test_api_generic_error_returns_fallback(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("API down")
        judge = Judge(client=client)
        sub = Submission(agent_id="a1", request_id="r1",
                         bid=1.0, work="answer")
        result = judge.score_submission("task", sub)
        assert result["score"] == 1

    def test_empty_work_string(self):
        judge = self._mock_judge('{"score": 2, "feedback": "Empty submission"}')
        sub = Submission(agent_id="a1", request_id="r1",
                         bid=1.0, work="")
        result = judge.score_submission("task", sub)
        assert result["score"] == 2

    def test_very_long_work_truncated(self):
        """Verify long work is truncated before sending to LLM."""
        client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = '{"score": 5, "feedback": "ok"}'
        client.chat.completions.create.return_value = mock_resp
        judge = Judge(client=client)

        long_work = "x" * 100_000
        sub = Submission(agent_id="a1", request_id="r1",
                         bid=1.0, work=long_work)
        judge.score_submission("task", sub)

        # Check the prompt sent to the LLM was truncated
        call_args = client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][1]["content"]
        assert len(prompt) < 100_000
        assert "truncated" in prompt

    def test_score_exactly_at_threshold(self):
        judge = self._mock_judge('{"score": 7, "feedback": "Meets threshold"}')
        sub = Submission(agent_id="a1", request_id="r1",
                         bid=1.0, work="answer")
        result = judge.score_submission("task", sub)
        assert result["score"] == 7

    def test_batch_scoring_normal(self):
        judge = self._mock_judge(
            '{"scores": {"a1": {"score": 8, "feedback": "good"}, '
            '"a2": {"score": 5, "feedback": "bad"}}}'
        )
        subs = {
            "a1": Submission(agent_id="a1", request_id="r1",
                             bid=1.0, work="good"),
            "a2": Submission(agent_id="a2", request_id="r1",
                             bid=0.5, work="bad"),
        }
        result = judge.score_batch("task", subs)
        assert result["a1"]["score"] == 8
        assert result["a2"]["score"] == 5

    def test_batch_scoring_missing_agent(self):
        """Judge only scores a1, not a2."""
        judge = self._mock_judge(
            '{"scores": {"a1": {"score": 8, "feedback": "good"}}}'
        )
        subs = {
            "a1": Submission(agent_id="a1", request_id="r1",
                             bid=1.0, work="good"),
            "a2": Submission(agent_id="a2", request_id="r1",
                             bid=0.5, work="bad"),
        }
        result = judge.score_batch("task", subs)
        assert result["a1"]["score"] == 8
        assert result["a2"]["score"] == 1  # fallback

    def test_batch_scoring_api_error(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("API down")
        judge = Judge(client=client)
        subs = {
            "a1": Submission(agent_id="a1", request_id="r1",
                             bid=1.0, work="x"),
        }
        result = judge.score_batch("task", subs)
        assert result["a1"]["score"] == 1


# ═══════════════════════════════════════════════════════════════════════
# SETTLEMENT EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

class TestSettlement:
    def test_exchange_fee_normal(self):
        # 20% of (0.10 - 0.06) = 20% of 0.04 = 0.008
        assert abs(calc_exchange_fee(0.10, 0.06) - 0.008) < 0.0001

    def test_exchange_fee_capped_at_1_cent(self):
        # 20% of (1.00 - 0.02) = 0.196, capped at $0.01
        assert abs(calc_exchange_fee(1.00, 0.02) - 0.01) < 0.0001

    def test_exchange_fee_zero_spread(self):
        assert calc_exchange_fee(0.05, 0.05) == 0.0

    def test_exchange_fee_negative_spread_defended(self):
        """Agent bids higher than max (shouldn't happen, but defend)."""
        assert calc_exchange_fee(0.03, 0.05) == 0.0

    def test_exchange_fee_very_small_spread(self):
        fee = calc_exchange_fee(0.01001, 0.01)
        assert fee == pytest.approx(0.000002, abs=0.000001)

    def test_exchange_fee_very_large(self):
        fee = calc_exchange_fee(999.0, 0.0)
        assert fee == 0.01  # capped at $0.01

    def test_ledger_record_and_query(self):
        ledger = Ledger()
        tx = ledger.record("r1", "b1", "a1", "ocr", 0.03, 0.05, 8, 200)
        assert tx.price == 0.03
        assert abs(tx.exchange_fee - 0.004) < 0.0001  # 20% of $0.02
        assert abs(tx.buyer_charged - 0.034) < 0.0001
        assert tx.tx_id.startswith("tx_")

    def test_ledger_query_by_buyer(self):
        ledger = Ledger()
        ledger.record("r1", "b1", "a1", "ocr", 3.0, 5.0, 8, 200)
        ledger.record("r2", "b2", "a2", "ocr", 2.0, 5.0, 7, 300)
        assert len(ledger.get_transactions(buyer_id="b1")) == 1
        assert len(ledger.get_transactions(buyer_id="b2")) == 1
        assert len(ledger.get_transactions(buyer_id="b3")) == 0

    def test_ledger_query_by_agent(self):
        ledger = Ledger()
        ledger.record("r1", "b1", "a1", "ocr", 3.0, 5.0, 8, 200)
        ledger.record("r2", "b2", "a1", "ocr", 2.0, 5.0, 7, 300)
        assert len(ledger.get_transactions(agent_id="a1")) == 2

    def test_ledger_totals_empty(self):
        ledger = Ledger()
        totals = ledger.get_totals()
        assert totals["total_transactions"] == 0
        assert totals["total_volume"] == 0

    def test_ledger_totals_multiple(self):
        ledger = Ledger()
        ledger.record("r1", "b1", "a1", "ocr", 0.03, 0.05, 8, 200)
        ledger.record("r2", "b1", "a2", "ocr", 0.02, 0.05, 7, 300)
        totals = ledger.get_totals()
        assert totals["total_transactions"] == 2
        assert abs(totals["total_volume"] - 0.05) < 0.001

    def test_ledger_concurrent_writes(self):
        ledger = Ledger()
        errors = []

        def write(i):
            try:
                ledger.record(f"r{i}", "b1", f"a{i}", "ocr",
                              float(i), 100.0, 7, 100)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write, args=(i,))
                   for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert ledger.get_totals()["total_transactions"] == 100


# ═══════════════════════════════════════════════════════════════════════
# GAME ENGINE EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

def _make_state(**kwargs) -> GameState:
    defaults = dict(
        request_id="r1", capability="ocr", input="test",
        max_price=5.0, min_quality=7, buyer_id="b1",
    )
    defaults.update(kwargs)
    return GameState(**defaults)


class TestReceiveSubmission:
    def test_normal_submission(self):
        state = _make_state()
        assert receive_submission(state, "a1", 3.0, "output") is True
        assert "a1" in state.submissions
        assert state.submissions["a1"].bid == 3.0
        assert state.submissions["a1"].revision == 0

    def test_reject_after_game_done(self):
        state = _make_state()
        state.done = True
        assert receive_submission(state, "a1", 3.0, "output") is False

    def test_reject_bid_over_max_price(self):
        state = _make_state(max_price=5.0)
        assert receive_submission(state, "a1", 6.0, "output") is False

    def test_reject_negative_bid(self):
        state = _make_state()
        assert receive_submission(state, "a1", -1.0, "output") is False

    def test_accept_zero_bid(self):
        state = _make_state()
        assert receive_submission(state, "a1", 0.0, "output") is True

    def test_accept_bid_at_exact_max_price(self):
        state = _make_state(max_price=5.0)
        assert receive_submission(state, "a1", 5.0, "output") is True

    def test_empty_work_accepted(self):
        state = _make_state()
        assert receive_submission(state, "a1", 1.0, "") is True

    def test_revision_increments(self):
        state = _make_state()
        receive_submission(state, "a1", 3.0, "v1")
        assert state.submissions["a1"].revision == 0
        receive_submission(state, "a1", 3.0, "v2")
        assert state.submissions["a1"].revision == 1
        assert state.submissions["a1"].work == "v2"

    def test_max_revisions_enforced(self):
        state = _make_state(max_revisions=2)
        receive_submission(state, "a1", 3.0, "v0")  # rev 0
        receive_submission(state, "a1", 3.0, "v1")  # rev 1
        receive_submission(state, "a1", 3.0, "v2")  # rev 2
        # revision 2 == max_revisions, so next should be rejected
        assert receive_submission(state, "a1", 3.0, "v3") is False
        assert state.submissions["a1"].work == "v2"

    def test_multiple_agents_submit(self):
        state = _make_state()
        receive_submission(state, "a1", 3.0, "work1")
        receive_submission(state, "a2", 2.0, "work2")
        receive_submission(state, "a3", 4.0, "work3")
        assert len(state.submissions) == 3

    def test_concurrent_submissions(self):
        state = _make_state()
        errors = []

        def submit(i):
            try:
                receive_submission(state, f"a{i}", float(i % 5), f"work{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=submit, args=(i,))
                   for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(state.submissions) == 50


class TestGetQualifiers:
    def test_no_submissions(self):
        state = _make_state()
        assert _get_qualifiers(state) == []

    def test_one_qualifier(self):
        state = _make_state(min_quality=7)
        state.submissions["a1"] = Submission(
            agent_id="a1", request_id="r1", bid=3.0,
            work="good", score=8)
        state.submissions["a2"] = Submission(
            agent_id="a2", request_id="r1", bid=2.0,
            work="bad", score=5)
        assert _get_qualifiers(state) == ["a1"]

    def test_multiple_qualifiers(self):
        state = _make_state(min_quality=7)
        state.submissions["a1"] = Submission(
            agent_id="a1", request_id="r1", bid=3.0,
            work="good", score=8)
        state.submissions["a2"] = Submission(
            agent_id="a2", request_id="r1", bid=1.0,
            work="ok", score=7)
        qualifiers = _get_qualifiers(state)
        assert set(qualifiers) == {"a1", "a2"}

    def test_score_exactly_at_threshold(self):
        state = _make_state(min_quality=7)
        state.submissions["a1"] = Submission(
            agent_id="a1", request_id="r1", bid=3.0,
            work="ok", score=7)
        assert _get_qualifiers(state) == ["a1"]

    def test_score_one_below_threshold(self):
        state = _make_state(min_quality=7)
        state.submissions["a1"] = Submission(
            agent_id="a1", request_id="r1", bid=3.0,
            work="ok", score=6)
        assert _get_qualifiers(state) == []

    def test_bid_over_max_excluded(self):
        state = _make_state(max_price=5.0, min_quality=7)
        state.submissions["a1"] = Submission(
            agent_id="a1", request_id="r1", bid=6.0,
            work="good", score=9)
        assert _get_qualifiers(state) == []

    def test_unscored_submission_excluded(self):
        state = _make_state(min_quality=7)
        state.submissions["a1"] = Submission(
            agent_id="a1", request_id="r1", bid=3.0,
            work="good", score=None)
        assert _get_qualifiers(state) == []


class TestSelectWinner:
    def test_lowest_bid_wins(self):
        state = _make_state()
        state.submissions["a1"] = Submission(
            agent_id="a1", request_id="r1", bid=3.0,
            work="good", score=8, timestamp=1.0)
        state.submissions["a2"] = Submission(
            agent_id="a2", request_id="r1", bid=1.0,
            work="ok", score=7, timestamp=2.0)
        result = _select_winner(state, ["a1", "a2"])
        assert result.agent_id == "a2"

    def test_same_bid_earliest_timestamp_wins(self):
        state = _make_state()
        state.submissions["a1"] = Submission(
            agent_id="a1", request_id="r1", bid=2.0,
            work="first", score=8, timestamp=100.0)
        state.submissions["a2"] = Submission(
            agent_id="a2", request_id="r1", bid=2.0,
            work="second", score=8, timestamp=200.0)
        result = _select_winner(state, ["a1", "a2"])
        assert result.agent_id == "a1"

    def test_sets_game_state_done(self):
        state = _make_state()
        state.submissions["a1"] = Submission(
            agent_id="a1", request_id="r1", bid=3.0,
            work="ok", score=7, timestamp=1.0)
        _select_winner(state, ["a1"])
        assert state.done is True
        assert state.winner == "a1"

    def test_single_qualifier(self):
        state = _make_state()
        state.submissions["a1"] = Submission(
            agent_id="a1", request_id="r1", bid=3.0,
            work="ok", score=7, timestamp=1.0)
        result = _select_winner(state, ["a1"])
        assert result.agent_id == "a1"


# ═══════════════════════════════════════════════════════════════════════
# SDK CLIENT EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

class TestExchangeClient:
    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="api_key"):
            Exchange(api_key="")

    def test_empty_server_url_raises(self):
        with pytest.raises(ValueError, match="server_url"):
            Exchange(api_key="demo", server_url="")

    def test_call_empty_capability_raises(self):
        ex = Exchange(api_key="demo")
        with pytest.raises(ValueError, match="capability"):
            ex.call(capability="", input="test", max_price=5.0)

    def test_call_negative_max_price_raises(self):
        ex = Exchange(api_key="demo")
        with pytest.raises(ValueError, match="max_price"):
            ex.call(capability="ocr", input="test", max_price=-1.0)

    def test_call_zero_max_price_raises(self):
        ex = Exchange(api_key="demo")
        with pytest.raises(ValueError, match="max_price"):
            ex.call(capability="ocr", input="test", max_price=0.0)

    def test_call_negative_timeout_raises(self):
        ex = Exchange(api_key="demo")
        with pytest.raises(ValueError, match="timeout"):
            ex.call(capability="ocr", input="test", max_price=5.0, timeout=-1.0)

    def test_call_zero_timeout_raises(self):
        ex = Exchange(api_key="demo")
        with pytest.raises(ValueError, match="timeout"):
            ex.call(capability="ocr", input="test", max_price=5.0, timeout=0.0)

    def test_server_not_running_raises_connection_error(self):
        ex = Exchange(api_key="demo", server_url="http://localhost:19999")
        with pytest.raises(ConnectionError, match="Cannot connect"):
            ex.call(capability="ocr", input="test", max_price=5.0, timeout=2.0)

    def test_min_quality_out_of_range_rejected(self):
        """min_quality outside 1-10 is rejected by Pydantic."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CallRequest(capability="ocr", input="test",
                        max_price=5.0, min_quality=0, timeout=5.0)
        with pytest.raises(ValidationError):
            CallRequest(capability="ocr", input="test",
                        max_price=5.0, min_quality=11, timeout=5.0)


# ═══════════════════════════════════════════════════════════════════════
# TYPES EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

class TestTypes:
    def test_game_state_lock_exists(self):
        state = _make_state()
        assert hasattr(state, "lock")
        # Should be acquirable
        state.lock.acquire()
        state.lock.release()

    def test_game_state_lock_not_serialized(self):
        state = _make_state()
        d = state.model_dump()
        assert "lock" not in d

    def test_transaction_auto_generates_tx_id(self):
        tx = Transaction(
            request_id="r1", buyer_id="b1", agent_id="a1",
            capability="ocr", price=3.0,
            exchange_fee=0.4, buyer_charged=3.4)
        assert tx.tx_id.startswith("tx_")

    def test_submission_defaults(self):
        sub = Submission(agent_id="a1", request_id="r1",
                         bid=1.0, work="hello")
        assert sub.score is None
        assert sub.feedback is None
        assert sub.revision == 0
        assert sub.timestamp > 0

    def test_exchange_result_optional_fields(self):
        r = ExchangeResult(output="x", agent_id="a1",
                           price=1.0, latency_ms=100)
        assert r.score is None
        assert r.request_id == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
