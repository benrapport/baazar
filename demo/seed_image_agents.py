#!/usr/bin/env python3
"""Register 3 image generation agents with the exchange.

Each agent uses a different OpenAI image model:
- dall-e-3: High quality, slower, $0.04/image (1024x1024)
- gpt-image-1: Best quality, mid speed, $0.02/image (1024x1024)
- gpt-image-1.5: Latest, balanced, variable pricing

Run this AFTER starting the exchange (run_exchange.py).
"""

import logging
import os
import sys
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

from openai import OpenAI
from bazaar.provider import AgentProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

client = OpenAI()


def _generate_image(model: str, prompt: str, size: str = "1024x1024") -> str:
    """Call OpenAI image API and return data URI string."""
    resp = client.images.generate(
        model=model,
        prompt=prompt,
        n=1,
        size=size,
    )
    b64 = resp.data[0].b64_json
    if not b64:
        raise ValueError(f"No b64_json in response from {model}")
    return f"data:image/png;base64,{b64}"


def make_dalle3_agent():
    """DALL-E 3 agent — high quality, $0.04/image at 1024x1024."""
    provider = AgentProvider(
        agent_id="dalle3-agent",
        callback_port=9010,
    )

    @provider.handle()
    def handle(request):
        prompt = request["input"]
        logger.info(f"[dalle3] Generating: {prompt[:60]}...")
        try:
            data_uri = _generate_image("dall-e-3", prompt)
            return {"work": data_uri}
        except Exception as e:
            logger.error(f"[dalle3] Failed: {e}")
            return None  # pass

    return provider


def make_gpt_image_agent():
    """gpt-image-1 agent — best quality, $0.02/image at 1024x1024."""
    provider = AgentProvider(
        agent_id="gpt-image-1-agent",
        callback_port=9011,
    )

    @provider.handle()
    def handle(request):
        prompt = request["input"]
        logger.info(f"[gpt-image-1] Generating: {prompt[:60]}...")
        try:
            data_uri = _generate_image("gpt-image-1", prompt)
            return {"work": data_uri}
        except Exception as e:
            logger.error(f"[gpt-image-1] Failed: {e}")
            return None

    return provider


def make_gpt_image_15_agent():
    """gpt-image-1.5 agent — latest model, balanced quality/speed."""
    provider = AgentProvider(
        agent_id="gpt-image-1.5-agent",
        callback_port=9012,
    )

    @provider.handle()
    def handle(request):
        prompt = request["input"]
        logger.info(f"[gpt-image-1.5] Generating: {prompt[:60]}...")
        try:
            data_uri = _generate_image("gpt-image-1.5", prompt)
            return {"work": data_uri}
        except Exception as e:
            logger.error(f"[gpt-image-1.5] Failed: {e}")
            return None

    return provider


if __name__ == "__main__":
    import threading

    print("Starting 3 image generation agents...")
    agents = [make_dalle3_agent(), make_gpt_image_agent(), make_gpt_image_15_agent()]

    threads = []
    for agent in agents:
        t = threading.Thread(target=agent.start, daemon=True)
        t.start()
        threads.append(t)
        print(f"  {agent.agent_id} on port {agent.callback_port}")

    print("\nAll image agents running. Press Ctrl+C to stop.")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nStopping agents.")
