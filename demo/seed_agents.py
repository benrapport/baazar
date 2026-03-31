#!/usr/bin/env python3
"""Register 3 seed agents with the exchange.

Each agent uses a different OpenAI model with different cost/quality tradeoffs.
Run this AFTER starting the exchange (run_exchange.py).
"""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load env
for env_path in [Path(__file__).resolve().parent.parent / ".env",
                  Path.home() / "Desktop" / "meetrics" / ".env"]:
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

from openai import OpenAI
from agentx.provider import AgentProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

client = OpenAI()

# ── Agent definitions ─────────────────────────────────────────────────

def make_cheap_agent():
    """Fast and cheap agent using gpt-4o-mini. Bids low."""
    provider = AgentProvider(
        agent_id="cheap-agent",
        callback_port=9001,
    )

    @provider.handle("general")
    def handle(request):
        task = request["input"]
        max_price = request["max_price"]

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": (
                    "You are a fast, efficient AI agent competing in a marketplace. "
                    "Do the task well but concisely. You are cheap and fast."
                )},
                {"role": "user", "content": task},
            ],
        )
        work = resp.choices[0].message.content

        # Bid low — we're cheap
        bid = min(0.005, max_price * 0.3)
        return {"bid": bid, "work": work}

    return provider


def make_mid_agent():
    """Mid-tier agent using gpt-4.1-mini. Balanced."""
    provider = AgentProvider(
        agent_id="mid-agent",
        callback_port=9002,
    )

    @provider.handle("general")
    def handle(request):
        task = request["input"]
        max_price = request["max_price"]

        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=2048,
            messages=[
                {"role": "system", "content": (
                    "You are a capable AI agent competing in a marketplace. "
                    "Produce high-quality work. Be thorough and accurate."
                )},
                {"role": "user", "content": task},
            ],
        )
        work = resp.choices[0].message.content

        bid = min(0.015, max_price * 0.5)
        return {"bid": bid, "work": work}

    return provider


def make_premium_agent():
    """Premium agent using gpt-4.1. High quality, higher price."""
    provider = AgentProvider(
        agent_id="premium-agent",
        callback_port=9003,
    )

    @provider.handle("general")
    def handle(request):
        task = request["input"]
        max_price = request["max_price"]

        resp = client.chat.completions.create(
            model="gpt-4.1",
            max_tokens=4096,
            messages=[
                {"role": "system", "content": (
                    "You are a premium AI agent in a marketplace. "
                    "Produce the highest quality output possible. "
                    "Be comprehensive, accurate, and well-structured."
                )},
                {"role": "user", "content": task},
            ],
        )
        work = resp.choices[0].message.content

        bid = min(0.03, max_price * 0.7)
        return {"bid": bid, "work": work}

    return provider


if __name__ == "__main__":
    import threading

    print("Starting 3 seed agents...")
    agents = [make_cheap_agent(), make_mid_agent(), make_premium_agent()]

    threads = []
    for agent in agents:
        t = threading.Thread(target=agent.start, daemon=True)
        t.start()
        threads.append(t)
        print(f"  {agent.agent_id} on port {agent.callback_port}")

    print("\nAll agents running. Press Ctrl+C to stop.")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nStopping agents.")
