#!/usr/bin/env python3
"""Test suite for AI Exchange with token economics."""

import json
import os
import sys
import time
import threading
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bid

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
SKIP = "\033[93m⊘\033[0m"
results = {"pass": 0, "fail": 0, "skip": 0}


def check(name, fn):
    try:
        fn()
        print(f"  {PASS} {name}")
        results["pass"] += 1
    except Exception as e:
        print(f"  {FAIL} {name}: {e}")
        results["fail"] += 1


def skip_test(name, reason):
    print(f"  {SKIP} {name} (skipped: {reason})")
    results["skip"] += 1


def header(text):
    print(f"\n{'─' * 60}\n  {text}\n{'─' * 60}")


def _assert(cond, msg=""):
    assert cond, msg


def _raises(exc_types, fn):
    try:
        fn()
        assert False, f"expected {exc_types}"
    except exc_types:
        pass


def reset_state():
    """Reset global state between tests."""
    for n in bid.MODEL_NAMES:
        bid.budgets[n] = bid.STARTING_BUDGET_CENTS
        bid.token_spend[n] = 0.0
        bid.bid_spend[n] = 0.0
        bid.stats[n] = {"wins": 0, "losses": 0, "passes": 0,
                         "tokens_used": {"input": 0, "output": 0}}
    bid.exchange_revenue = 0.0


# ═══════════════════════════════════════════════════════════════════════
# UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════

def run_unit_tests():

    header("UNIT: parse_json")
    check("plain JSON", lambda: _assert(bid.parse_json('{"bid": 2.5}')["bid"] == 2.5))
    check("fenced JSON", lambda: _assert(bid.parse_json('```json\n{"x":1}\n```')["x"] == 1))
    check("preamble JSON", lambda: _assert(bid.parse_json('Here is my answer:\n{"x":1}\nDone.')["x"] == 1))
    check("nested JSON (judge scores)", lambda: _assert(
        bid.parse_json('{"scores":{"a":{"score":7,"feedback":"good"}}}')["scores"]["a"]["score"] == 7))
    check("empty → error", lambda: _raises(ValueError, lambda: bid.parse_json("")))
    check("no JSON → error", lambda: _raises((ValueError, json.JSONDecodeError),
                                              lambda: bid.parse_json("nope")))

    header("UNIT: token routing")
    check("reasoning model → max_completion_tokens",
          lambda: _assert("max_completion_tokens" in bid._token_kwarg({"reasoning": True}, 256)))
    check("standard model → max_tokens",
          lambda: _assert(bid._token_kwarg({"reasoning": False}, 256) == {"max_tokens": 256}))

    header("UNIT: system role")
    check("reasoning → developer", lambda: _assert(bid._system_role({"reasoning": True}) == "developer"))
    check("standard → system", lambda: _assert(bid._system_role({"reasoning": False}) == "system"))

    header("UNIT: model registry")
    check("6 models", lambda: _assert(len(bid.MODELS) == 6))
    check("2 reasoning + 4 standard",
          lambda: _assert(sum(1 for c in bid.MODELS.values() if c["reasoning"]) == 2))

    def test_all_models_have_pricing():
        for n, c in bid.MODELS.items():
            assert "input_per_m" in c, f"{n} missing input_per_m"
            assert "output_per_m" in c, f"{n} missing output_per_m"
            assert c["input_per_m"] > 0, f"{n} input cost must be positive"
            assert c["output_per_m"] > 0, f"{n} output cost must be positive"
    check("all models have token pricing", test_all_models_have_pricing)

    def test_pricing_order():
        # o3 should be most expensive, gpt-4o-mini cheapest
        assert bid.MODELS["o3"]["output_per_m"] > bid.MODELS["gpt-4o-mini"]["output_per_m"]
        assert bid.MODELS["o3"]["output_per_m"] > bid.MODELS["gpt-4.1"]["output_per_m"]
    check("o3 is most expensive model", test_pricing_order)

    header("UNIT: token cost calculation")

    def test_token_cost_cents():
        usage = MagicMock()
        usage.prompt_tokens = 1000
        usage.completion_tokens = 500
        # o3: 1000 * 10/1M + 500 * 40/1M = 0.01 + 0.02 = 0.03 dollars = 3.0 cents
        cost = bid.calc_token_cost_cents("o3", usage)
        assert abs(cost - 3.0) < 0.01, f"o3 cost should be ~3.0¢, got {cost}¢"
    check("o3: 1000 in + 500 out = ~3.0¢", test_token_cost_cents)

    def test_token_cost_cheap():
        usage = MagicMock()
        usage.prompt_tokens = 1000
        usage.completion_tokens = 500
        # gpt-4o-mini: 1000 * 0.15/1M + 500 * 0.60/1M = 0.00015 + 0.0003 = 0.00045 dollars = 0.045 cents
        cost = bid.calc_token_cost_cents("gpt-4o-mini", usage)
        assert abs(cost - 0.045) < 0.005, f"gpt-4o-mini should be ~0.045¢, got {cost}¢"
    check("gpt-4o-mini: 1000 in + 500 out = ~0.045¢", test_token_cost_cheap)

    def test_estimated_call_cost():
        o3_est = bid.estimated_call_cost_cents("o3")
        mini_est = bid.estimated_call_cost_cents("gpt-4o-mini")
        assert o3_est > mini_est * 10, f"o3 should be >10x gpt-4o-mini cost"
    check("o3 estimated cost >> gpt-4o-mini", test_estimated_call_cost)

    header("UNIT: deduct_tokens")

    def test_deduct_tokens():
        reset_state()
        usage = MagicMock()
        usage.prompt_tokens = 500
        usage.completion_tokens = 300
        before = bid.budgets["o3"]
        cost = bid.deduct_tokens("o3", usage)
        after = bid.budgets["o3"]
        assert cost > 0
        assert abs(after - (before - cost)) < 0.001
        assert bid.token_spend["o3"] == cost
        assert bid.stats["o3"]["tokens_used"]["input"] == 500
        assert bid.stats["o3"]["tokens_used"]["output"] == 300
        reset_state()
    check("deduct_tokens reduces budget + tracks spend", test_deduct_tokens)

    header("UNIT: task queue")

    def test_queue():
        assert len(bid.TASK_QUEUE) == 100, f"expected 100 tasks, got {len(bid.TASK_QUEUE)}"
        for item in bid.TASK_QUEUE:
            assert "task" in item and "buyer_price" in item and "min_score" in item
            assert 0.5 <= item["buyer_price"] <= 200.0, f"price out of range: {item['buyer_price']}"
            assert 1 <= item["min_score"] <= 10
    check("100 tasks with valid structure", test_queue)

    def test_price_tiers():
        prices = [t["buyer_price"] for t in bid.TASK_QUEUE]
        # Should have cheap (<5¢) and expensive (>50¢) tasks
        cheap = sum(1 for p in prices if p < 5)
        expensive = sum(1 for p in prices if p >= 50)
        assert cheap >= 15, f"need ≥15 cheap tasks, got {cheap}"
        assert expensive >= 5, f"need ≥5 expensive tasks, got {expensive}"
    check("mix of cheap and expensive tasks", test_price_tiers)

    header("UNIT: exchange fee (cents)")
    check("20% of spread", lambda: _assert(abs(bid.calc_exchange_fee(10.0, 6.0) - 0.80) < 0.001))
    check("capped at 1¢", lambda: _assert(abs(bid.calc_exchange_fee(100.0, 2.0) - 1.00) < 0.001))
    check("zero spread → zero fee", lambda: _assert(bid.calc_exchange_fee(5.0, 5.0) == 0.0))
    check("tiny spread", lambda: _assert(abs(bid.calc_exchange_fee(2.0, 1.5) - 0.10) < 0.001))

    header("UNIT: economics initialization")

    def test_economics_init():
        reset_state()
        assert all(bid.budgets[n] == bid.STARTING_BUDGET_CENTS for n in bid.MODEL_NAMES)
        assert all(bid.token_spend[n] == 0.0 for n in bid.MODEL_NAMES)
        assert all(bid.bid_spend[n] == 0.0 for n in bid.MODEL_NAMES)
        assert bid.STARTING_BUDGET_CENTS == 300.0
    check("budgets at 300¢, token/bid spend at 0", test_economics_init)

    header("UNIT: RoundState")

    def test_state_init():
        s = bid.RoundState("task", ["a", "b", "c"], 5.0, 7)
        assert s.buyer_price == 5.0
        assert s.min_score == 7
        assert all(n in s.token_costs for n in s.models)
    check("init with cents pricing + token tracking", test_state_init)

    def test_state_scoring():
        s = bid.RoundState("task", ["a", "b"], 5.0, 7)
        s.submit("a", 2.0, "work", True)
        s.set_score("a", 8, "good")
        assert s.scores["a"] == 8
    check("set_score stores score + feedback", test_state_scoring)

    header("UNIT: prompts include economics")

    def test_bidder_prompt_economics():
        rendered = bid.BIDDER_INITIAL_SYSTEM.format(
            model_name="test-model", n_competitors=5, game_state="test",
            task_text="Test task", buyer_price=10.0, min_score=7,
            budget=287.5, est_token_cost=1.7, rounds_remaining=50)
        assert "token" in rendered.lower()
        assert "287.5" in rendered or "287.50" in rendered
        assert "1.7" in rendered
        assert "STRATEGIC" in rendered
        assert "TASK FIT" in rendered
        assert "COMPETITION" in rendered
        assert "50" in rendered  # rounds remaining
    check("bidder prompt: economics + strategic reasoning", test_bidder_prompt_economics)

    def test_revision_prompt_economics():
        rendered = bid.BIDDER_REVISION_SYSTEM.format(
            score=5, min_score=7, feedback="needs work",
            budget=285.0, token_spent=15.0, est_token_cost=1.7,
            task="test", buyer_price=10.0, bid=3.0, attempt=2,
            max_turns=3, n_active=4)
        assert "285" in rendered
        assert "15" in rendered
        assert "1.7" in rendered
    check("revision prompt shows token economics", test_revision_prompt_economics)

    header("UNIT: game state string")

    def test_game_state():
        reset_state()
        gs = bid.build_game_state(1)
        assert "Round 1" in gs
        assert "Token" in gs
        for n in bid.MODEL_NAMES:
            assert n in gs
    check("build_game_state includes token spend", test_game_state)


# ═══════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════

def run_integration_tests():
    header("INTEGRATION: API")

    if not os.environ.get("OPENAI_API_KEY"):
        skip_test("all integration tests", "OPENAI_API_KEY not set")
        return

    check("API key valid", lambda: _assert(bool(
        bid.client.chat.completions.create(
            model="gpt-4.1-nano", max_tokens=5,
            messages=[{"role": "user", "content": "Say OK"}]
        ).choices[0].message.content)))

    header("INTEGRATION: token cost tracking")

    def test_real_token_cost():
        reset_state()
        resp = bid.client.chat.completions.create(
            model="gpt-4o-mini", max_tokens=50,
            messages=[{"role": "user", "content": "Say hello"}])
        cost = bid.deduct_tokens("gpt-4o-mini", resp.usage)
        assert cost > 0, "token cost must be positive"
        assert cost < 1.0, f"simple call should cost <1¢, got {cost}¢"
        assert bid.budgets["gpt-4o-mini"] < bid.STARTING_BUDGET_CENTS
        reset_state()
    check("real API call: token cost tracked + deducted", test_real_token_cost)

    header("INTEGRATION: bidder submission")

    for name in ["o4-mini", "gpt-4.1-mini"]:
        def test_bidder(name=name):
            reset_state()
            state = bid.RoundState("What is 2+2?",
                                   [name], 5.0, 5)
            t = threading.Thread(target=bid.bidder_work,
                                 args=(name, state, 1), daemon=True)
            t.start()
            deadline = time.time() + 45.0
            while time.time() < deadline:
                with state.lock:
                    if state.status[name] != "bidding":
                        break
                time.sleep(0.5)
            state.done.set()
            for ev in state.revision_ready.values():
                ev.set()
            t.join(timeout=5.0)

            with state.lock:
                status = state.status[name]
                sub = state.submissions.get(name)

            assert status in ("submitted", "passed"), f"status={status}"
            if status == "submitted":
                assert bid.MIN_BID_CENTS <= sub["bid"] < 5.0, f"bid={sub['bid']}¢"
                assert len(sub["work"]) > 0, f"work is empty"
            # Token cost was tracked (budget should have decreased from tokens)
            assert bid.budgets[name] < bid.STARTING_BUDGET_CENTS, \
                f"budget should decrease: {bid.budgets[name]} vs {bid.STARTING_BUDGET_CENTS}"
            reset_state()
        check(f"{name}: bid + work + token tracking", test_bidder)

    header("INTEGRATION: judge scoring")

    def test_judge_scores():
        state = bid.RoundState("What is 2+2?", ["gpt-4.1-mini", "gpt-4o-mini"], 3.0, 5)
        state.submit("gpt-4.1-mini", 1.5, "2+2 = 4", True)
        state.submit("gpt-4o-mini", 1.0, "The answer is 4.", True)
        scores = bid._judge_score(state, ["gpt-4.1-mini", "gpt-4o-mini"])
        for name in ["gpt-4.1-mini", "gpt-4o-mini"]:
            assert name in scores, f"{name} not in scores"
            assert "score" in scores[name]
            assert 1 <= scores[name]["score"] <= 10
    check("judge scores with cents pricing", test_judge_scores)

    header("INTEGRATION: edge cases")

    def test_all_pass():
        state = bid.RoundState("task", ["a", "b"], 3.0, 5)
        for n in ["a", "b"]:
            state.submit(n, 0, "", False)
            with state.lock:
                state.status[n] = "passed"
        jt = threading.Thread(target=bid.judge_work, args=(state,))
        jt.start()
        state.done.wait(timeout=15.0)
        jt.join(timeout=5.0)
        assert state.winner is None
        assert state.judge_action == "NO_CONTEST"
    check("all pass → no contest", test_all_pass)

    header("INTEGRATION: full round E2E")

    def test_full_round():
        reset_state()
        test_models = ["gpt-4.1-mini", "gpt-4o-mini"]
        state = bid.RoundState("What is 2+2?", test_models, 3.0, 5)
        threads = []
        for name in test_models:
            t = threading.Thread(target=bid.bidder_work,
                                 args=(name, state, 1), daemon=True)
            t.start()
            threads.append(t)
        jt = threading.Thread(target=bid.judge_work, args=(state,), daemon=True)
        jt.start()
        state.done.wait(timeout=90.0)
        assert state.done.is_set(), "round timed out"
        for t in threads:
            t.join(timeout=5.0)
        jt.join(timeout=5.0)
        assert state.judge_action in ("ACCEPT", "NO_CONTEST", "TIMEOUT")
        if state.winner:
            sub = state.submissions[state.winner]
            assert sub["bid"] < 3.0
            assert state.token_costs[state.winner] > 0
        reset_state()
    check("full round: 2 models + token tracking", test_full_round)

    header("INTEGRATION: expensive model economics")

    def test_o3_cost_awareness():
        """o3's estimated cost should be significantly higher."""
        o3_est = bid.estimated_call_cost_cents("o3")
        mini_est = bid.estimated_call_cost_cents("gpt-4o-mini")
        ratio = o3_est / mini_est
        assert ratio > 30, f"o3 should be >30x gpt-4o-mini, got {ratio:.1f}x"
    check("o3 cost >> gpt-4o-mini cost (>30x)", test_o3_cost_awareness)

    reset_state()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  AI EXCHANGE TEST SUITE — Token Economics                    ║")
    print(f"║  Mode: {mode:<55}║")
    print("╚══════════════════════════════════════════════════════════════╝")

    start = time.time()
    if mode in ("all", "unit"):
        run_unit_tests()
    if mode in ("all", "integration"):
        run_integration_tests()

    elapsed = time.time() - start
    header("RESULTS")
    print(f"  {PASS} {results['pass']} passed")
    if results["fail"]:
        print(f"  {FAIL} {results['fail']} failed")
    if results["skip"]:
        print(f"  {SKIP} {results['skip']} skipped")
    print(f"  ⏱  {elapsed:.1f}s")
    sys.exit(1 if results["fail"] else 0)
