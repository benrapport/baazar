"""Image agent fleet — 50 agents in one process, path-based routing.

Each agent shares the centralized image tool but has a unique prompt-rewriting
strategy and economic preference. One FastAPI server handles all agents.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI
from openai import OpenAI

from bazaar.types import AgentRegistration, BroadcastPayload, SubmissionPayload, AgentNotification
from agents.image_tool import generate_image, get_best_option, PROMPT_REWRITE_COST

logger = logging.getLogger(__name__)

STRATEGIES_PATH = Path(__file__).parent / "strategies.json"
EXCHANGE_URL = os.environ.get("BAZAAR_EXCHANGE_URL", "http://localhost:8000")
REWRITE_MODEL = "gpt-4o-mini"


def load_strategies() -> list[dict]:
    with open(STRATEGIES_PATH) as f:
        return json.load(f)


class ImageFleet:
    """Runs N image agents in a single process on a single port."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9100,
                 exchange_url: str = EXCHANGE_URL,
                 max_agents: int | None = None):
        self.host = host
        self.port = port
        self.exchange_url = exchange_url
        self.strategies = load_strategies()
        if max_agents:
            self.strategies = self.strategies[:max_agents]

        self._llm_client: OpenAI | None = None
        self._pending_tasks: set[asyncio.Task] = set()
        self._app = FastAPI(title="Image Agent Fleet")
        self._setup_routes()

    @property
    def llm_client(self) -> OpenAI:
        if self._llm_client is None:
            self._llm_client = OpenAI()
        return self._llm_client

    def _setup_routes(self):
        @self._app.post("/agent/{agent_id}/request")
        async def receive_request(agent_id: str, payload: BroadcastPayload):
            """Exchange broadcasts a request. Route to the right strategy."""
            strategy = self._get_strategy(agent_id)
            if not strategy:
                logger.warning(f"Unknown agent: {agent_id}")
                return {"status": "unknown_agent"}

            task = asyncio.create_task(
                self._handle_request(agent_id, strategy, payload)
            )
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)
            return {"status": "accepted"}

        @self._app.get("/health")
        async def health():
            return {
                "agents": len(self.strategies),
                "status": "ok",
            }

    def _get_strategy(self, agent_id: str) -> dict | None:
        for s in self.strategies:
            if s["id"] == agent_id:
                return s
        return None

    async def _handle_request(self, agent_id: str, strategy: dict,
                              payload: BroadcastPayload):
        """Rewrite prompt using strategy, pick model, generate image, submit."""
        max_price = payload.max_price
        user_prompt = payload.input
        request_id = payload.request_id

        # Pick model config based on economic strategy
        option = get_best_option(max_price, prefer=strategy["economic_strategy"])
        if not option:
            logger.info(f"[{agent_id}] PASS — no affordable model for ${max_price}")
            await self._notify(request_id, agent_id, "pass", "no affordable model")
            return

        model = option["model"]
        size = option["size"]
        quality = option["quality"]
        cost = option["cost"] + PROMPT_REWRITE_COST

        logger.info(
            f"[{agent_id}] FILL — {model} {size} ${cost:.3f} "
            f"(margin ${max_price - cost:.3f})"
        )
        await self._notify(request_id, agent_id, "fill")

        try:
            # Rewrite prompt using agent's strategy
            rewritten = await asyncio.to_thread(
                self._rewrite_prompt, strategy, user_prompt, model
            )

            # Generate image
            data_uri = await asyncio.to_thread(
                generate_image, rewritten, model, size, quality
            )

            # Submit to exchange
            await self._submit(request_id, agent_id, data_uri)

        except Exception as e:
            logger.error(f"[{agent_id}] Failed: {e}")

    def _rewrite_prompt(self, strategy: dict, user_prompt: str,
                        model: str) -> str:
        """Use LLM to rewrite the user prompt according to agent's strategy."""
        system = (
            f"{strategy['system_prompt']}\n\n"
            f"You are rewriting an image generation prompt for the {model} model. "
            f"Output ONLY the rewritten prompt, nothing else. "
            f"Keep it under 500 characters."
        )
        try:
            resp = self.llm_client.chat.completions.create(
                model=REWRITE_MODEL,
                max_completion_tokens=300,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
            )
            rewritten = resp.choices[0].message.content.strip()
            logger.debug(f"[{strategy['id']}] Rewritten: {rewritten[:80]}...")
            return rewritten
        except Exception as e:
            logger.warning(f"[{strategy['id']}] Rewrite failed, using original: {e}")
            return user_prompt

    async def _submit(self, request_id: str, agent_id: str, work: str):
        """POST work submission to exchange."""
        sub = SubmissionPayload(
            agent_id=agent_id,
            request_id=request_id,
            work=work,
        )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.exchange_url}/submit/{request_id}",
                    json=sub.model_dump(),
                    headers={"X-Agent-Id": agent_id},
                )
                if resp.status_code == 404:
                    logger.warning(f"[{agent_id}] Market {request_id} already closed")
                elif resp.status_code >= 400:
                    logger.warning(f"[{agent_id}] Submission rejected: {resp.status_code}")
                else:
                    logger.info(f"[{agent_id}] Submitted to {request_id}")
        except Exception as e:
            logger.error(f"[{agent_id}] Submit failed: {e}")

    async def _notify(self, request_id: str, agent_id: str,
                      decision: str, reason: str = ""):
        """POST fill/pass notification to exchange."""
        notification = AgentNotification(
            agent_id=agent_id,
            decision=decision,
            reason=reason,
        )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{self.exchange_url}/notify/{request_id}",
                    json=notification.model_dump(),
                    headers={"X-Agent-Id": agent_id},
                )
        except Exception:
            pass

    def register_all(self):
        """Register all agents with the exchange."""
        for strategy in self.strategies:
            agent_id = strategy["id"]
            callback_url = f"http://{self.host}:{self.port}/agent/{agent_id}"
            reg = AgentRegistration(
                agent_id=agent_id,
                callback_url=callback_url,
            )
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(
                        f"{self.exchange_url}/register",
                        json=reg.model_dump(),
                    )
                    resp.raise_for_status()
                    logger.info(f"Registered: {agent_id}")
            except Exception as e:
                logger.error(f"Failed to register {agent_id}: {e}")
                raise

    def start(self):
        """Start the fleet server, register all agents, block."""
        import socket
        import threading
        import time

        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()

        # Wait for server to be ready
        for _ in range(30):
            try:
                with socket.create_connection((self.host, self.port), timeout=0.5):
                    break
            except (ConnectionRefusedError, OSError):
                time.sleep(0.2)

        self.register_all()
        print(f"\n{len(self.strategies)} image agents running on port {self.port}")
        server_thread.join()

    def _run_server(self):
        uvicorn.run(
            self._app,
            host=self.host,
            port=self.port,
            log_level="warning",
        )
