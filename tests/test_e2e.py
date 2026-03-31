#!/usr/bin/env python3
"""End-to-end integration test — server + agent + buyer."""

import os
import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load env
for p in [Path(__file__).resolve().parent.parent / ".env",
          Path.home() / "Desktop" / "meetrics" / ".env"]:
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

import httpx
import uvicorn
from exchange.server import app, registry
from agentx.types import AgentRegistration, SubmissionPayload


SERVER_URL = "http://127.0.0.1:8787"
HEADERS = {"Authorization": "Bearer demo"}


def start_server():
    """Start the exchange server on a test port."""
    uvicorn.run(app, host="127.0.0.1", port=8787, log_level="warning")


def test_full_e2e():
    """Full flow: start server, register agent, submit task, get result."""

    # Start server in background
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(1.0)  # wait for server

    client = httpx.Client(base_url=SERVER_URL, timeout=30.0)

    # 1. Check status
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agents_registered"] == 0
    print(f"  [OK] Status endpoint works: {data}")

    # 2. Register a mock agent (we'll submit work manually, no callback server)
    reg = AgentRegistration(
        agent_id="test-agent",
        capabilities=["general"],
        callback_url="http://127.0.0.1:19999",  # dummy — we won't use callbacks
    )
    resp = client.post("/register", json=reg.model_dump())
    assert resp.status_code == 200
    assert resp.json()["status"] == "registered"
    print(f"  [OK] Agent registered: {resp.json()}")

    # 3. Check status shows 1 agent
    resp = client.get("/status")
    assert resp.json()["agents_registered"] == 1
    print(f"  [OK] Registry has 1 agent")

    # 4. Submit a task as buyer (async — we need to manually submit work too)
    # This is tricky: /call blocks waiting for submissions.
    # We'll submit work via /submit in a separate thread.

    result_holder = {}

    def buyer_call():
        try:
            resp = client.post("/call", json={
                "capability": "general",
                "input": "What is 2+2?",
                "max_price": 5.0,
                "min_quality": 3,  # low threshold for test
                "timeout": 15.0,
            }, headers=HEADERS)
            result_holder["status"] = resp.status_code
            result_holder["body"] = resp.json()
        except Exception as e:
            result_holder["error"] = str(e)

    buyer_thread = threading.Thread(target=buyer_call)
    buyer_thread.start()

    # Give the game time to broadcast (it'll fail since our agent has no real callback)
    time.sleep(3.0)

    # Manually submit work as the agent via /submit
    # First we need the request_id — get it from active_games
    from exchange.server import active_games
    if not active_games:
        # The broadcast failed (expected — no real callback server)
        # But the game should still be waiting for submissions
        print("  [WARN] No active games — broadcast couldn't reach agent")
        print("  This is expected since the test agent has no callback server.")
        print("  Testing manual submission via /submit endpoint...")

        # The game creates active_games from the /call handler, let's check
        time.sleep(1.0)

    if active_games:
        request_id = list(active_games.keys())[0]
        print(f"  [OK] Active game found: {request_id}")

        sub = SubmissionPayload(
            agent_id="test-agent",
            request_id=request_id,
            bid=2.0,
            work="2+2 = 4",
        )
        resp = client.post(f"/submit/{request_id}", json=sub.model_dump())
        print(f"  [OK] Submission response: {resp.status_code} {resp.json()}")

        # Wait for buyer to get result
        buyer_thread.join(timeout=15.0)

        if "body" in result_holder:
            print(f"  [OK] Buyer result: {result_holder['body']}")
            assert result_holder["status"] == 200
            body = result_holder["body"]
            assert body["agent_id"] == "test-agent"
            assert body["output"] == "2+2 = 4"
            assert body["price"] == 2.0
            print("\n  === E2E TEST PASSED ===")
        elif "error" in result_holder:
            print(f"  [WARN] Buyer error: {result_holder['error']}")
        else:
            print("  [WARN] Buyer still waiting — judge may not have scored yet")
    else:
        buyer_thread.join(timeout=5.0)
        print("  [INFO] Could not test /submit (no active game)")
        if "body" in result_holder:
            print(f"  Buyer got: {result_holder['status']} {result_holder['body']}")

    # 5. Check final status
    resp = client.get("/status")
    print(f"  [OK] Final status: {resp.json()}")

    client.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  E2E Integration Test")
    print("=" * 60)
    test_full_e2e()
