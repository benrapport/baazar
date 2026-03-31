#!/usr/bin/env python3
"""End-to-end integration test — replicates the full demo flow.

Starts the exchange server, registers real agents (with OpenAI calls),
submits buyer tasks, and verifies results. This catches:
- Registration/callback URL wiring
- OpenAI API parameter compatibility (max_completion_tokens, model names)
- Judge scoring pipeline
- Settlement/pricing
- The full broadcast → agent work → submit → judge → winner flow
"""

import os
import sys
import time
import socket
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

import httpx
import uvicorn
from openai import OpenAI
from bazaar import Exchange
from bazaar.provider import AgentProvider
from bazaar.types import AgentRegistration, SubmissionPayload


# ── Ports — use high ports to avoid collisions ──────────────────────

EXCHANGE_PORT = 18700
AGENT_PORTS = [18701, 18702]
EXCHANGE_URL = f"http://127.0.0.1:{EXCHANGE_PORT}"


def _wait_for_port(port: int, host: str = "127.0.0.1", timeout: float = 5.0):
    """Block until a port is accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.1)
    raise RuntimeError(f"Port {port} not ready after {timeout}s")


# ── Test: Full demo replication ──────────────────────────────────────

def test_demo_e2e():
    """Replicate the exact demo: exchange + 2 agents + buyer tasks.

    This is the test that would have caught:
    - max_tokens vs max_completion_tokens
    - Missing callback_url in registration
    - Nonexistent judge model
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or api_key == "sk-...":
        print("  [SKIP] No OPENAI_API_KEY set — skipping live e2e test")
        return

    # 1. Start exchange server
    from exchange.server import app as exchange_app

    def run_exchange():
        uvicorn.run(exchange_app, host="127.0.0.1", port=EXCHANGE_PORT,
                    log_level="warning")

    exchange_thread = threading.Thread(target=run_exchange, daemon=True)
    exchange_thread.start()
    _wait_for_port(EXCHANGE_PORT)
    print(f"  [OK] Exchange running on port {EXCHANGE_PORT}")

    # 2. Start 2 real agents with OpenAI calls
    client = OpenAI()
    agents = []

    def make_agent(agent_id: str, port: int, model: str, bid_frac: float):
        provider = AgentProvider(
            agent_id=agent_id,
            exchange_url=EXCHANGE_URL,
            callback_port=port,
        )

        @provider.handle()
        def handle(request):
            resp = client.chat.completions.create(
                model=model,
                max_completion_tokens=512,
                messages=[
                    {"role": "system", "content": "Answer concisely."},
                    {"role": "user", "content": request["input"]},
                ],
            )
            work = resp.choices[0].message.content
            bid = min(0.01, request["max_price"] * bid_frac)
            return {"bid": bid, "work": work}

        return provider

    agent_configs = [
        ("test-cheap", AGENT_PORTS[0], "gpt-4o-mini", 0.3),
        ("test-mid", AGENT_PORTS[1], "gpt-4o-mini", 0.5),
    ]

    for agent_id, port, model, bid_frac in agent_configs:
        provider = make_agent(agent_id, port, model, bid_frac)
        t = threading.Thread(target=provider.start, daemon=True)
        t.start()
        agents.append((agent_id, port))

    # Wait for all agent ports to be ready
    for agent_id, port in agents:
        _wait_for_port(port)
        print(f"  [OK] Agent {agent_id} running on port {port}")

    # Small delay for registration to complete
    time.sleep(0.5)

    # Verify agents registered
    resp = httpx.get(f"{EXCHANGE_URL}/status", timeout=5.0)
    assert resp.status_code == 200
    status = resp.json()
    assert status["agents_registered"] >= 2, (
        f"Expected >= 2 agents registered, got {status['agents_registered']}"
    )
    print(f"  [OK] {status['agents_registered']} agents registered")

    # 3. Submit tasks as buyer (using the SDK, just like the demo)
    ex = Exchange(api_key="demo", server_url=EXCHANGE_URL)

    tasks = [
        {"input": "What is 2+2?", "max_price": 0.05, "min_quality": 3},
        {"input": "Write a haiku about rain", "max_price": 0.05, "min_quality": 3},
    ]

    results = []
    for i, task in enumerate(tasks):
        print(f"\n  Task {i+1}: {task['input']}")
        try:
            result = ex.call(
                llm={"input": task["input"]},
                exchange={
                    "max_price": task["max_price"],
                    "judge": {"min_quality": task["min_quality"]},
                    "timeout": 30.0,
                },
            )
            results.append(result)
            print(f"  [OK] Winner: {result.agent_id}, "
                  f"score: {result.score}/10, "
                  f"price: ${result.price:.4f}")
            print(f"       Output: {result.output[:80]}...")

            # Verify result fields
            assert result.output, "Output should not be empty"
            assert result.agent_id in ("test-cheap", "test-mid")
            assert result.price > 0
            assert result.price <= task["max_price"]
            assert result.score is not None
            assert result.score >= task["min_quality"]
            assert result.latency_ms > 0

        except Exception as e:
            print(f"  [FAIL] Task failed: {e}")
            raise

    # 4. Verify settlement (account for transactions from earlier tests)
    resp = httpx.get(f"{EXCHANGE_URL}/status", timeout=5.0)
    status = resp.json()
    assert status["total_transactions"] >= len(tasks), (
        f"Expected >= {len(tasks)} transactions, got {status['total_transactions']}"
    )
    assert status["total_volume"] > 0
    print(f"\n  [OK] Settlement: {status['total_transactions']} transactions, "
          f"${status['total_volume']:.4f} volume")

    print("\n  === FULL E2E TEST PASSED ===")


# ── Test: Manual submission (no OpenAI needed) ───────────────────────

def test_manual_submission():
    """Test the submit path without real agents — no OpenAI key needed.

    Registers a dummy agent, posts /call in a thread, manually submits
    work via /submit, verifies the buyer gets a result.
    """
    from fastapi import FastAPI
    from exchange.server import registry, active_games, _get_judge, ledger
    from exchange.game import run_game, receive_submission
    from exchange.types import GameState

    PORT = 18710
    from exchange import server as srv

    # Fresh app to avoid port conflicts with test_demo_e2e
    test_app = FastAPI()

    # Re-register endpoints on the test app
    @test_app.get("/status")
    async def status():
        return {"agents_registered": registry.count}

    @test_app.post("/register")
    async def register(reg: AgentRegistration):
        agent = registry.register(agent_id=reg.agent_id,
                                  callback_url=reg.callback_url)
        return {"status": "registered", "agent_id": agent.agent_id}

    # Use a shared state so we can submit manually
    shared = {"state": None, "request_id": None}

    @test_app.post("/call")
    async def call_endpoint():
        import uuid
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        state = GameState(
            request_id=request_id, input="What is 1+1?",
            max_price=5.0, min_quality=1, buyer_id="demo",
        )
        shared["state"] = state
        shared["request_id"] = request_id

        result = await run_game(
            input_text="What is 1+1?", max_price=5.0, min_quality=1,
            buyer_id="demo", registry=registry, judge=_get_judge(),
            ledger=ledger, timeout=10.0, state=state,
        )
        return result.model_dump()

    @test_app.post("/submit/{request_id}")
    async def submit(request_id: str, sub: SubmissionPayload):
        state = shared["state"]
        if not state or state.request_id != request_id:
            return {"status": "no_game"}
        accepted = receive_submission(state, sub.agent_id, sub.bid, sub.work)
        return {"status": "accepted" if accepted else "rejected"}

    def run_server():
        uvicorn.run(test_app, host="127.0.0.1", port=PORT, log_level="warning")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    _wait_for_port(PORT)

    base = f"http://127.0.0.1:{PORT}"
    http = httpx.Client(base_url=base, timeout=30.0)

    # Register a dummy agent (callback URL won't be used)
    reg = AgentRegistration(agent_id="manual-agent",
                            callback_url="http://127.0.0.1:19999")
    resp = http.post("/register", json=reg.model_dump())
    assert resp.status_code == 200

    # Start buyer call in background
    result_box = {}

    def buyer():
        try:
            resp = http.post("/call", headers={"Authorization": "Bearer demo"})
            result_box["status"] = resp.status_code
            result_box["body"] = resp.json()
        except Exception as e:
            result_box["error"] = str(e)

    buyer_thread = threading.Thread(target=buyer)
    buyer_thread.start()

    # Wait for game to start, then submit work manually
    deadline = time.time() + 5.0
    while time.time() < deadline and shared["state"] is None:
        time.sleep(0.1)

    assert shared["state"] is not None, "Game never started"
    request_id = shared["request_id"]

    sub = SubmissionPayload(
        agent_id="manual-agent", request_id=request_id,
        bid=1.0, work="1+1 = 2",
    )
    resp = http.post(f"/submit/{request_id}", json=sub.model_dump())
    assert resp.status_code == 200

    buyer_thread.join(timeout=20.0)
    assert "body" in result_box, f"Buyer failed: {result_box.get('error')}"
    body = result_box["body"]
    assert body["agent_id"] == "manual-agent"
    assert body["output"] == "1+1 = 2"
    assert body["price"] == 1.0
    print("  [OK] Manual submission test passed")

    http.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  E2E Integration Tests")
    print("=" * 60)

    print("\n--- Test 1: Manual submission (no OpenAI) ---")
    test_manual_submission()

    print("\n--- Test 2: Full demo replication (live OpenAI) ---")
    test_demo_e2e()
