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
from agents.image_tool import generate_image, get_best_option, PROMPT_REWRITE_COST, estimate_thinking_cost
from agents.memory import AgentMemory

logger = logging.getLogger(__name__)

STRATEGIES_PATH = Path(__file__).parent / "strategies.json"
EXCHANGE_URL = os.environ.get("BAZAAR_EXCHANGE_URL", "http://localhost:8000")
REWRITE_MODEL = "gpt-4o-mini"
MAX_REVISIONS = 2  # max revision attempts per submission


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
        self._memories: dict[str, AgentMemory] = {
            s["id"]: AgentMemory() for s in self.strategies
        }
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
        """Rewrite prompt, generate image, submit, then revise if score is low.

        Revision loop:
        1. Submit initial image
        2. Poll for score (within the game window)
        3. If score < min_quality and market still open and budget allows:
           - LLM rewrites prompt incorporating judge feedback
           - Regenerate image and resubmit
        4. Up to MAX_REVISIONS revision attempts
        """
        max_price = payload.max_price
        user_prompt = payload.input
        request_id = payload.request_id
        min_quality = payload.min_quality
        memory = self._memories[agent_id]

        # Pick model config based on economic strategy
        option = get_best_option(max_price, prefer=strategy["economic_strategy"])
        if not option:
            logger.info(f"[{agent_id}] PASS — no affordable model for ${max_price}")
            await self._notify(request_id, agent_id, "pass", "no affordable model")
            return

        model = option["model"]
        size = option["size"]
        quality = option["quality"]
        has_memory = len(memory.scored_attempts) > 0
        thinking_cost = estimate_thinking_cost(has_memory)
        image_cost = option["cost"]
        cost_per_attempt = image_cost + thinking_cost
        total_cost = cost_per_attempt  # tracks cumulative cost across revisions

        if max_price - total_cost < 0:
            logger.info(f"[{agent_id}] PASS — negative margin at ${max_price}")
            await self._notify(request_id, agent_id, "pass", "negative margin")
            return

        logger.info(
            f"[{agent_id}] FILL — {model} {size} "
            f"cost=${cost_per_attempt:.4f} margin=${max_price - total_cost:.4f}"
        )
        await self._notify(request_id, agent_id, "fill")

        try:
            # Initial submission
            rewritten = await asyncio.to_thread(
                self._rewrite_prompt, strategy, user_prompt, model, memory
            )
            memory.record_attempt(request_id, user_prompt, rewritten, model)

            data_uri = await asyncio.to_thread(
                generate_image, rewritten, model, size, quality
            )
            await self._submit(request_id, agent_id, data_uri)

            # Revision loop: poll for score, revise if below threshold
            for revision in range(1, MAX_REVISIONS + 1):
                score_data = await self._poll_score_fast(request_id, agent_id)
                if not score_data:
                    break  # game ended or couldn't get score

                score = score_data.get("score", 0)
                feedback = score_data.get("feedback", "")
                won = score_data.get("won", False)

                if won or score >= min_quality:
                    # Good enough or already won — no revision needed
                    logger.info(
                        f"[{agent_id}] r{revision-1} Score: {score}/10"
                        + (" [WON]" if won else " [QUALIFIED]")
                    )
                    memory.record_score(request_id, score, feedback, won)
                    return

                # Check if revision is economically viable
                revised_total = total_cost + cost_per_attempt
                if revised_total >= max_price:
                    logger.info(
                        f"[{agent_id}] r{revision-1} Score: {score}/10 — "
                        f"skip revision (cost ${revised_total:.4f} >= ${max_price})"
                    )
                    memory.record_score(request_id, score, feedback, won)
                    return

                # Revise: rewrite prompt incorporating judge feedback
                logger.info(
                    f"[{agent_id}] r{revision-1} Score: {score}/10 — "
                    f"REVISING (judge: {feedback[:60]})"
                )

                rewritten = await asyncio.to_thread(
                    self._revise_prompt, strategy, user_prompt, rewritten,
                    score, feedback, model
                )

                data_uri = await asyncio.to_thread(
                    generate_image, rewritten, model, size, quality
                )
                await self._submit(request_id, agent_id, data_uri)
                total_cost = revised_total

            # After revision loop, do final async feedback poll for memory
            asyncio.create_task(
                self._poll_feedback_for_memory(request_id, agent_id, memory)
            )

        except Exception as e:
            logger.error(f"[{agent_id}] Failed: {e}")

    async def _poll_score_fast(self, request_id: str, agent_id: str,
                               ) -> dict | None:
        """Poll for score quickly during the game window (for revision decisions)."""
        for delay in [3, 4, 5, 6]:
            await asyncio.sleep(delay)
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        f"{self.exchange_url}/feedback/{request_id}/{agent_id}",
                        headers={"X-Agent-Id": agent_id},
                    )
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    if data.get("status") == "scored":
                        return data
                    if data.get("status") in ("not_found",):
                        return None  # game ended
            except Exception:
                pass
        return None

    async def _poll_feedback_for_memory(self, request_id: str, agent_id: str,
                                         memory: AgentMemory):
        """Final async poll to store score in memory (post-game)."""
        for delay in [2, 5, 10, 15]:
            await asyncio.sleep(delay)
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        f"{self.exchange_url}/feedback/{request_id}/{agent_id}",
                        headers={"X-Agent-Id": agent_id},
                    )
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    if data.get("status") == "scored":
                        memory.record_score(
                            request_id, data["score"],
                            data.get("feedback", ""), data.get("won", False))
                        return
                    if data.get("status") == "not_found":
                        return
            except Exception:
                pass

    def _rewrite_prompt(self, strategy: dict, user_prompt: str,
                        model: str, memory: AgentMemory | None = None) -> str:
        """Use LLM to rewrite the user prompt according to agent's strategy.

        If the agent has memory of past attempts, injects few-shot examples
        (best and worst scoring rewrites) so the LLM can learn what works.
        """
        context = memory.build_context() if memory else ""

        system_parts = [strategy["system_prompt"]]

        if context:
            system_parts.append(
                f"\n--- LEARNING FROM YOUR PAST RESULTS ---\n{context}\n"
                f"Use these results to improve. Do more of what scored well. "
                f"Avoid patterns that scored poorly."
            )

        system_parts.append(
            f"\nYou are rewriting an image generation prompt for the {model} model. "
            f"Output ONLY the rewritten prompt, nothing else. "
            f"Keep it under 500 characters."
        )

        system = "\n".join(system_parts)

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

    def _revise_prompt(self, strategy: dict, original_prompt: str,
                       previous_rewrite: str, score: int,
                       feedback: str, model: str) -> str:
        """Rewrite the prompt incorporating judge feedback on what was wrong."""
        system = (
            f"{strategy['system_prompt']}\n\n"
            f"You are REVISING an image generation prompt for the {model} model.\n\n"
            f"The original task was: \"{original_prompt}\"\n"
            f"Your previous prompt was: \"{previous_rewrite}\"\n"
            f"The judge scored it {score}/10 and said: \"{feedback}\"\n\n"
            f"Fix the issues the judge identified. Keep what worked. "
            f"Output ONLY the revised prompt, nothing else. "
            f"Keep it under 500 characters."
        )
        try:
            resp = self.llm_client.chat.completions.create(
                model=REWRITE_MODEL,
                max_completion_tokens=300,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Revise to fix: {feedback}"},
                ],
            )
            revised = resp.choices[0].message.content.strip()
            logger.debug(f"[{strategy['id']}] Revised: {revised[:80]}...")
            return revised
        except Exception as e:
            logger.warning(f"[{strategy['id']}] Revision failed: {e}")
            return previous_rewrite

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
