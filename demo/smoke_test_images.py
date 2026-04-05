#!/usr/bin/env python3
"""Smoke test for image generation agents + multimodal judge.

Starts exchange + 3 image agents, submits an image task, verifies:
- All agents register
- Image is generated and returned as base64
- Multimodal judge scores the image
- Exchange stats reflect the completed market

Exit code 0 = everything works. Non-zero = something broke.
Usage: python demo/smoke_test_images.py
"""

import base64
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
    print("  Bazaar Image Agent Smoke Test")
    print("=" * 60)

    import httpx

    # ── Step 1: Start exchange ───────────────────────────────
    print("\n[1/4] Starting exchange server...")
    exchange = subprocess.Popen(
        [sys.executable, str(ROOT / "demo" / "run_exchange.py")],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    PROCS.append(exchange)

    for _ in range(30):
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

    # ── Step 2: Start image agents ───────────────────────────
    print("\n[2/4] Starting image generation agents...")
    agents = subprocess.Popen(
        [sys.executable, str(ROOT / "demo" / "seed_image_agents.py")],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    PROCS.append(agents)
    time.sleep(5)

    resp = httpx.get("http://localhost:8000/status", timeout=5.0)
    status = resp.json()
    agent_count = status.get("agents_registered", 0)
    if agent_count == 0:
        fail("No image agents registered")
    ok(f"{agent_count} image agents registered")

    # ── Step 3: Submit an image generation task ──────────────
    print("\n[3/4] Submitting image generation task...")
    print("       (this takes 10-30s — agents are generating images)")
    from bazaar.client import Exchange as BazaarExchange

    ex = BazaarExchange(api_key="demo")
    try:
        result = ex.call(
            llm={"input": "A friendly robot waving hello in a sunny park"},
            exchange={
                "max_price": 0.20,
                "timeout": 60.0,
                "judge": {
                    "min_quality": 4,
                    "criteria": [
                        "Accuracy: Does the image match the prompt?",
                        "Visual quality: Is the image clear and well-composed?",
                        "Creativity: Is the interpretation interesting?",
                    ],
                },
            },
        )
    except Exception as e:
        fail(f"Image task failed: {e}")

    if not result.output:
        fail("Empty output from exchange")
    if not result.output.startswith("data:image/"):
        fail(f"Output is not an image (starts with: {result.output[:30]})")
    if not result.agent_id:
        fail("No agent_id in result")
    if result.score is None:
        fail("No score — judge did not evaluate the image")

    # Check image data is valid base64
    try:
        _, b64_part = result.output.split(",", 1)
        img_bytes = base64.b64decode(b64_part)
        img_kb = len(img_bytes) / 1024
    except Exception as e:
        fail(f"Invalid base64 image: {e}")

    ok(f"Winner: {result.agent_id}")
    ok(f"Score: {result.score}/10")
    ok(f"Image size: {img_kb:.0f} KB")
    ok(f"Latency: {result.latency_ms:.0f}ms")

    # ── Step 4: Check exchange stats ─────────────────────────
    print("\n[4/4] Checking exchange stats...")
    resp = httpx.get("http://localhost:8000/status", timeout=5.0)
    final = resp.json()
    if final.get("completed_markets", 0) < 1:
        fail("No completed markets")
    ok(f"Markets completed: {final['completed_markets']}")
    ok(f"Total volume: ${final.get('total_volume', 0):.4f}")

    # ── Done ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ALL IMAGE TESTS PASSED")
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
