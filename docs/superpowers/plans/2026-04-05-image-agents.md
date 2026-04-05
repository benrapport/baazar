# Image Generation Agents + Multimodal Judge

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 3 competing image generation agents (DALL-E 3, gpt-image-1, gpt-image-1.5) and a multimodal judge (gpt-4o with vision) to the Bazaar exchange so we can see competitive dynamics across price, speed, and quality.

**Architecture:** Agents receive a text prompt via the existing broadcast mechanism, call their image API, base64-encode the result, and submit it as the `work` field (prefixed with `data:image/png;base64,` so the judge can detect images). The judge detects the prefix, switches to vision mode (sending an image_url content block to gpt-4o), and scores the image 1-10. No changes to the exchange core, types, or game engine — only the judge and agent handlers change.

**Tech Stack:** OpenAI Python SDK (already installed), base64 encoding, gpt-4o vision API.

---

### Task 1: Multimodal Judge

**Files:**
- Modify: `exchange/judge.py` — add image detection + vision scoring
- Create: `tests/test_judge_multimodal.py` — unit tests for image detection and prompt building

The judge needs to detect when a submission contains a base64 image and switch to vision mode. Text submissions continue to work exactly as before.

- [ ] **Step 1: Write failing tests for image detection**

Create `tests/test_judge_multimodal.py`:

```python
"""Tests for multimodal judge — image detection and vision prompt building."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from exchange.judge import _is_image_submission, _build_vision_messages


def test_detects_png_base64():
    work = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
    assert _is_image_submission(work) is True


def test_detects_jpeg_base64():
    work = "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
    assert _is_image_submission(work) is True


def test_detects_webp_base64():
    work = "data:image/webp;base64,UklGR..."
    assert _is_image_submission(work) is True


def test_plain_text_not_image():
    work = "This is a regular text submission about cats."
    assert _is_image_submission(work) is False


def test_empty_string_not_image():
    assert _is_image_submission("") is False


def test_vision_messages_contain_image_url():
    task = "Draw a cat"
    image_data = "data:image/png;base64,iVBORw0KGgo"
    criteria = ["Accuracy", "Style"]
    messages = _build_vision_messages(task, image_data, criteria)

    # System message exists
    assert messages[0]["role"] == "system"

    # User message has both text and image_url content blocks
    user_msg = messages[1]
    assert user_msg["role"] == "user"
    assert isinstance(user_msg["content"], list)

    types = [block["type"] for block in user_msg["content"]]
    assert "text" in types
    assert "image_url" in types

    # Image URL block contains our data URI
    img_block = [b for b in user_msg["content"] if b["type"] == "image_url"][0]
    assert img_block["image_url"]["url"] == image_data


def test_vision_messages_include_task_in_text():
    task = "Draw a sunset over mountains"
    image_data = "data:image/png;base64,abc123"
    messages = _build_vision_messages(task, image_data, ["Quality"])

    text_block = [b for b in messages[1]["content"] if b["type"] == "text"][0]
    assert "Draw a sunset over mountains" in text_block["text"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_judge_multimodal.py -v`
Expected: FAIL with `ImportError: cannot import name '_is_image_submission'`

- [ ] **Step 3: Add image detection and vision message builder to judge.py**

Add these functions to `exchange/judge.py` (after the existing `_truncate` function, before the `class Judge` definition):

```python
IMAGE_PREFIX = "data:image/"


def _is_image_submission(work: str) -> bool:
    """Detect if a submission contains a base64-encoded image."""
    return bool(work) and work.startswith(IMAGE_PREFIX)


IMAGE_CRITERIA = [
    "Accuracy: Does the image match the prompt description?",
    "Composition: Is the layout balanced and visually appealing?",
    "Detail: Is there appropriate level of detail and clarity?",
    "Style: Is the artistic quality and style consistent?",
]


def _build_vision_messages(task: str, image_data: str,
                           criteria: list[str] | None = None) -> list[dict]:
    """Build messages for vision-based image scoring."""
    criteria = criteria or IMAGE_CRITERIA
    criteria_text = "\n".join(f"- {c}" for c in criteria)

    system_prompt = (
        "You are scoring AI-generated images for a marketplace. "
        "Rate the image 1-10.\n\n"
        f"Scoring criteria:\n{criteria_text}\n\n"
        "Be a fair but demanding judge. 7 = good professional quality. "
        "5 = mediocre. 9-10 = excellent.\n\n"
        "Respond with ONLY valid JSON:\n"
        '{"score": <1-10>, "feedback": "<1-2 sentence feedback>"}'
    )

    user_content = [
        {
            "type": "text",
            "text": f"Task prompt: {task}\n\nScore the generated image below:",
        },
        {
            "type": "image_url",
            "image_url": {"url": image_data},
        },
    ]

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_judge_multimodal.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Update Judge.score_submission to use vision for images**

Modify the `score_submission` method in `exchange/judge.py`. Replace the existing method body with:

```python
    def score_submission(self, task: str, submission: Submission,
                         quality_criteria: list[str] | None = None) -> dict:
        """Score a single submission. Returns {score: int, feedback: str}.

        Automatically detects image submissions and uses vision scoring.
        """
        work = submission.work

        if _is_image_submission(work):
            return self._score_image(task, work, quality_criteria)

        # Text scoring (existing behavior)
        criteria = quality_criteria or DEFAULT_CRITERIA
        system_prompt = _build_judge_prompt(criteria)
        work = _truncate(work)
        prompt = f"Task: {task}\n\nSubmission:\n{work}"

        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                max_completion_tokens=256,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            result = parse_json(resp.choices[0].message.content)
            return {
                "score": _clamp_score(result.get("score")),
                "feedback": str(result.get("feedback", "")),
            }
        except Exception as e:
            logger.error(f"Judge scoring failed: {e}")
            return {"score": 1, "feedback": f"Judge error: {e}"}

    def _score_image(self, task: str, image_data: str,
                     quality_criteria: list[str] | None = None) -> dict:
        """Score an image submission using vision."""
        messages = _build_vision_messages(task, image_data, quality_criteria)
        vision_model = "gpt-4o"  # vision-capable model

        try:
            resp = self._client.chat.completions.create(
                model=vision_model,
                max_completion_tokens=256,
                messages=messages,
            )
            result = parse_json(resp.choices[0].message.content)
            return {
                "score": _clamp_score(result.get("score")),
                "feedback": str(result.get("feedback", "")),
            }
        except Exception as e:
            logger.error(f"Vision judge scoring failed: {e}")
            return {"score": 1, "feedback": f"Vision judge error: {e}"}
```

- [ ] **Step 6: Run all existing tests to verify no regressions**

Run: `python -m pytest tests/test_core.py tests/test_edge_cases.py tests/test_judge_multimodal.py -v`
Expected: All 129 tests PASS (122 existing + 7 new)

- [ ] **Step 7: Commit**

```bash
git add exchange/judge.py tests/test_judge_multimodal.py
git commit -m "feat: multimodal judge — auto-detect image submissions, score with gpt-4o vision"
```

---

### Task 2: Image Generation Agents

**Files:**
- Create: `demo/seed_image_agents.py` — 3 image agents using different OpenAI models

Each agent: receives broadcast → calls its image API → base64-encodes result → submits `data:image/png;base64,...` as work.

- [ ] **Step 1: Write seed_image_agents.py**

Create `demo/seed_image_agents.py`:

```python
#!/usr/bin/env python3
"""Register 3 image generation agents with the exchange.

Each agent uses a different OpenAI image model:
- dall-e-3: High quality, slower, $0.04/image (1024x1024)
- gpt-image-1: Best quality, mid speed, $0.02/image (1024x1024)
- gpt-image-1.5: Latest, balanced, variable pricing

Run this AFTER starting the exchange (run_exchange.py).
"""

import base64
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


def _generate_image(model: str, prompt: str, size: str = "1024x1024",
                    quality: str = "auto") -> str:
    """Call OpenAI image API and return data URI string."""
    kwargs = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }
    if model == "dall-e-3":
        kwargs["quality"] = quality
        kwargs["response_format"] = "b64_json"
    # gpt-image-1 and gpt-image-1.5 always return b64

    resp = client.images.generate(**kwargs)

    # Extract base64 data
    image_data = resp.data[0]
    if hasattr(image_data, "b64_json") and image_data.b64_json:
        b64 = image_data.b64_json
    elif hasattr(image_data, "url") and image_data.url:
        # If we got a URL instead, download and encode
        import httpx
        raw = httpx.get(image_data.url, timeout=30.0).content
        b64 = base64.b64encode(raw).decode()
    else:
        raise ValueError(f"No image data in response from {model}")

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
            data_uri = _generate_image("dall-e-3", prompt, size="1024x1024")
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
            data_uri = _generate_image("gpt-image-1", prompt, size="1024x1024")
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
            data_uri = _generate_image("gpt-image-1.5", prompt, size="1024x1024")
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
```

- [ ] **Step 2: Verify agent script imports correctly**

Run: `python -c "import demo.seed_image_agents; print('imports OK')"`
Expected: `imports OK` (no errors)

- [ ] **Step 3: Commit**

```bash
git add demo/seed_image_agents.py
git commit -m "feat: add 3 image generation agents (dall-e-3, gpt-image-1, gpt-image-1.5)"
```

---

### Task 3: Image Smoke Test

**Files:**
- Create: `demo/smoke_test_images.py` — end-to-end test for image agents + multimodal judge

- [ ] **Step 1: Write the image smoke test**

Create `demo/smoke_test_images.py`:

```python
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
    import base64
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
```

- [ ] **Step 2: Run the smoke test end-to-end**

Run: `python demo/smoke_test_images.py`
Expected: All 4 steps pass. Output shows winning agent, score, image size.

Note: This makes real API calls and costs ~$0.10-0.15 per run (3 image generations + 1 vision judge call). Budget accordingly.

- [ ] **Step 3: Commit**

```bash
git add demo/smoke_test_images.py
git commit -m "feat: add image agent smoke test — end-to-end image gen + vision judging"
```

---

### Task 4: Run and Validate

This is the final validation — run everything and confirm competitive dynamics are visible.

- [ ] **Step 1: Run existing text smoke test (regression check)**

Run: `python demo/smoke_test.py`
Expected: ALL TESTS PASSED (text agents still work with multimodal judge)

- [ ] **Step 2: Run image smoke test**

Run: `python demo/smoke_test_images.py`
Expected: ALL IMAGE TESTS PASSED

- [ ] **Step 3: Run unit tests**

Run: `python -m pytest tests/ -v --ignore=tests/test_e2e.py`
Expected: All tests pass (122 existing + 7 new = 129)

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address issues found during validation"
```
