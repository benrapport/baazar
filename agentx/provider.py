"""Agent provider SDK — seller interface.

An agent developer uses this to register their agent and start
receiving requests from the exchange.
"""

from __future__ import annotations
import asyncio
import logging
import threading
from typing import Callable

import httpx
import uvicorn
from fastapi import FastAPI

from agentx.types import AgentRegistration, BroadcastPayload, SubmissionPayload

logger = logging.getLogger(__name__)


class AgentProvider:
    """SDK for agent developers to register and serve capabilities.

    Usage:
        provider = AgentProvider(
            exchange_url="http://localhost:8000",
            agent_id="my-ocr-agent",
            callback_port=9001,
        )

        @provider.handle("ocr")
        def handle_ocr(request):
            # Do the work, return bid + output
            return {"bid": 0.005, "work": "extracted text..."}

        provider.start()  # blocks, starts listening
    """

    def __init__(self, exchange_url: str = "http://localhost:8000",
                 agent_id: str = "agent",
                 callback_host: str = "127.0.0.1",
                 callback_port: int = 9001):
        self.exchange_url = exchange_url.rstrip("/")
        self.agent_id = agent_id
        self.callback_host = callback_host
        self.callback_port = callback_port
        self.callback_url = f"http://{callback_host}:{callback_port}"

        self._handlers: dict[str, Callable] = {}
        self._capabilities: list[str] = []
        self._app = FastAPI(title=f"Agent: {agent_id}")
        self._setup_routes()

    def handle(self, capability: str):
        """Decorator to register a handler for a capability.

        The handler receives a dict with {request_id, capability, input,
        max_price, min_quality} and must return a dict with
        {bid, work}. All prices in USD.
        """
        def decorator(fn: Callable):
            self._handlers[capability] = fn
            if capability not in self._capabilities:
                self._capabilities.append(capability)
            return fn
        return decorator

    def _setup_routes(self):
        @self._app.post("/request")
        async def receive_request(payload: BroadcastPayload):
            """Exchange broadcasts a request to us."""
            handler = self._handlers.get(payload.capability)
            if not handler:
                return {"status": "no_handler"}

            # Run handler (may be slow — do it in a thread)
            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(
                    None, handler, payload.model_dump()
                )
            except Exception as e:
                logger.error(f"Handler error: {e}")
                return {"status": "error", "detail": str(e)}

            if result is None:
                # Agent chose to pass
                return {"status": "pass"}

            bid = result.get("bid", 0)
            work = result.get("work", "")

            # POST submission back to exchange
            sub = SubmissionPayload(
                agent_id=self.agent_id,
                request_id=payload.request_id,
                bid=bid,
                work=work,
            )
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        f"{self.exchange_url}/submit/{payload.request_id}",
                        json=sub.model_dump(),
                    )
                    logger.info(
                        f"Submitted to {payload.request_id}: "
                        f"bid=${bid:.4f}, status={resp.status_code}"
                    )
            except Exception as e:
                logger.error(f"Failed to submit: {e}")

            return {"status": "submitted"}

        @self._app.get("/health")
        async def health():
            return {"agent_id": self.agent_id, "status": "ok"}

    def _register_with_exchange(self):
        """Register this agent with the exchange server."""
        reg = AgentRegistration(
            agent_id=self.agent_id,
            capabilities=self._capabilities,
            callback_url=self.callback_url,
        )
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(
                    f"{self.exchange_url}/register",
                    json=reg.model_dump(),
                )
                resp.raise_for_status()
                logger.info(
                    f"Registered with exchange: {self.agent_id} "
                    f"({self._capabilities})"
                )
        except Exception as e:
            logger.error(f"Failed to register: {e}")
            raise

    def start(self, register: bool = True):
        """Start the agent's callback server and register with exchange.

        Blocks until the server is stopped.
        """
        if register:
            server_thread = threading.Thread(
                target=self._run_server, daemon=True
            )
            server_thread.start()

            import time
            time.sleep(0.5)

            self._register_with_exchange()

            server_thread.join()
        else:
            self._run_server()

    def _run_server(self):
        uvicorn.run(
            self._app,
            host=self.callback_host,
            port=self.callback_port,
            log_level="warning",
        )
