#!/usr/bin/env python3
"""Smoke test: starts exchange + agents, runs one task, verifies result, exits.

Exit code 0 = everything works. Non-zero = something broke.
Usage: python demo/smoke_test.py
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load .env
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

PROCS: list[subprocess.Popen] = []


def cleanup():
    for p in PROCS:
        try:
            p.terminate()
            p.wait(timeout=3)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def fail(msg: str):
    print(f"FAIL: {msg}")
    cleanup()
    sys.exit(1)


def ok(msg: str):
    print(f"  OK: {msg}")


def main():
    print("=" * 60)
    print("  Bazaar Smoke Test")
    print("=" * 60)

    import httpx

    # ── Step 1: Start exchange ───────────────────────────────
    print("\n[1/5] Starting exchange server...")
    exchange = subprocess.Popen(
        [sys.executable, str(ROOT / "demo" / "run_exchange.py")],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    PROCS.append(exchange)

    for i in range(30):
        try:
            resp = httpx.get("http://localhost:8000/status", timeout=2.0)
            if resp.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        fail("Exchange did not start within 15s")

    ok("Exchange running")

    # ── Step 2: Start seed agents ────────────────────────────
    print("\n[2/5] Starting seed agents...")
    agents = subprocess.Popen(
        [sys.executable, str(ROOT / "demo" / "seed_agents.py")],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    PROCS.append(agents)
    time.sleep(3)

    resp = httpx.get("http://localhost:8000/status", timeout=5.0)
    status = resp.json()
    agent_count = status.get("agents_registered", 0)
    if agent_count == 0:
        fail("No agents registered")
    ok(f"{agent_count} agents registered")

    # ── Step 3: Submit a task via SDK ────────────────────────
    print("\n[3/5] Submitting task via bazaar SDK...")
    from bazaar.client import Exchange as BazaarExchange

    ex = BazaarExchange(api_key="demo")
    try:
        result = ex.call(
            llm={"input": "What is the capital of France? One word."},
            exchange={"max_price": 0.10, "timeout": 30.0},
        )
    except Exception as e:
        fail(f"SDK call failed: {e}")

    if not result.output:
        fail("Empty output from exchange")
    if not result.agent_id:
        fail("No agent_id in result")
    if result.score is None:
        fail("No score in result")

    ok(f"Got result: agent={result.agent_id}, score={result.score}, "
       f"latency={result.latency_ms:.0f}ms")
    ok(f"Output: {result.output[:80]}")

    # ── Step 4: Test MCP server protocol ─────────────────────
    print("\n[4/5] Testing MCP server protocol...")
    import json

    mcp_input = "\n".join([
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
        json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                     "params": {"name": "bazaar_status", "arguments": {}}}),
    ]) + "\n"

    mcp_proc = subprocess.run(
        [sys.executable, str(ROOT / "mcp" / "server.py")],
        input=mcp_input,
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(ROOT),
    )

    mcp_lines = [l for l in mcp_proc.stdout.strip().split("\n") if l.strip()]
    if len(mcp_lines) < 3:
        fail(f"MCP server returned {len(mcp_lines)} responses, expected 3")

    # Check initialize
    init_resp = json.loads(mcp_lines[0])
    if init_resp.get("result", {}).get("serverInfo", {}).get("name") != "bazaar":
        fail("MCP initialize returned wrong server name")
    ok("MCP initialize OK")

    # Check tools/list
    tools_resp = json.loads(mcp_lines[1])
    tool_names = [t["name"] for t in tools_resp.get("result", {}).get("tools", [])]
    if "bazaar_call" not in tool_names or "bazaar_status" not in tool_names:
        fail(f"MCP tools/list missing expected tools: {tool_names}")
    ok(f"MCP tools/list OK: {tool_names}")

    # Check bazaar_status result
    status_resp = json.loads(mcp_lines[2])
    status_text = status_resp.get("result", {}).get("content", [{}])[0].get("text", "")
    status_data = json.loads(status_text)
    if not status_data.get("running"):
        fail("MCP bazaar_status says exchange not running")
    ok(f"MCP bazaar_status OK: {status_data.get('agents_registered')} agents")

    # ── Step 5: Check exchange stats ─────────────────────────
    print("\n[5/5] Checking exchange stats...")
    resp = httpx.get("http://localhost:8000/status", timeout=5.0)
    final_status = resp.json()
    if final_status.get("completed_markets", 0) < 1:
        fail("No completed markets after test")
    ok(f"Markets completed: {final_status['completed_markets']}")
    ok(f"Total volume: ${final_status.get('total_volume', 0):.4f}")

    # ── Done ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED")
    print("=" * 60)
    cleanup()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: (cleanup(), sys.exit(1)))
    signal.signal(signal.SIGTERM, lambda *_: (cleanup(), sys.exit(1)))
    try:
        main()
    except Exception as e:
        print(f"\nFAIL: Unhandled exception: {e}")
        cleanup()
        sys.exit(1)
