"""FastAPI exchange server — the gateway."""

from __future__ import annotations
import logging
import os
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException, Header
from openai import OpenAI

from agentx.types import (
    AgentRegistration, CallRequest, ExchangeResult, SubmissionPayload,
)
from exchange.game import receive_submission, run_game
from exchange.judge import Judge
from exchange.registry import Registry
from exchange.settlement import Ledger
from exchange.types import GameState

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="AgentX Exchange", version="0.1.0")

# Singletons — lazy init for OpenAI client (env may not be loaded at import)
registry = Registry()
ledger = Ledger()
active_games: dict[str, GameState] = {}
_games_lock = threading.Lock()
_judge: Judge | None = None


def _get_judge() -> Judge:
    global _judge
    if _judge is None:
        _judge = Judge(client=OpenAI())
    return _judge


# Simple API key auth (demo mode: "demo" key always works)
VALID_API_KEYS = {"demo", os.environ.get("AGENTX_API_KEY", "demo")}


def _check_auth(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")
    key = authorization.replace("Bearer ", "")
    if key not in VALID_API_KEYS:
        raise HTTPException(401, "Invalid API key")
    return key


# ── Buyer endpoint ────────────────────────────────────────────────────

@app.post("/call", response_model=ExchangeResult)
async def call_exchange(
    req: CallRequest,
    authorization: str | None = Header(None),
):
    """Buyer submits a task. Exchange runs the game, returns the winner."""
    buyer_id = _check_auth(authorization)

    # Create game state so agents can submit while game runs
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    state = GameState(
        request_id=request_id,
        capability=req.capability,
        input=req.input,
        max_price=req.max_price,
        min_quality=req.min_quality,
        buyer_id=buyer_id,
    )
    with _games_lock:
        active_games[request_id] = state

    try:
        result = await run_game(
            capability=req.capability,
            input_text=req.input,
            max_price=req.max_price,
            min_quality=req.min_quality,
            buyer_id=buyer_id,
            registry=registry,
            judge=_get_judge(),
            ledger=ledger,
            timeout=req.timeout,
            state=state,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    except TimeoutError as e:
        raise HTTPException(504, str(e))
    finally:
        with _games_lock:
            active_games.pop(request_id, None)

    return result


# ── Agent endpoints ───────────────────────────────────────────────────

@app.post("/register")
async def register_agent(reg: AgentRegistration):
    """Agent registers itself with the exchange."""
    agent = registry.register(
        agent_id=reg.agent_id,
        capabilities=reg.capabilities,
        callback_url=reg.callback_url,
    )
    logger.info(f"Registered agent: {agent.agent_id} ({reg.capabilities})")
    return {"status": "registered", "agent_id": agent.agent_id}


@app.post("/submit/{request_id}")
async def submit_work(request_id: str, sub: SubmissionPayload):
    """Agent submits work + price for an active request."""
    state = active_games.get(request_id)
    if not state:
        raise HTTPException(404, f"No active game for request {request_id}")

    accepted = receive_submission(state, sub.agent_id, sub.bid, sub.work)
    if not accepted:
        raise HTTPException(400, "Submission rejected (game done or bid too high)")

    logger.info(f"[{request_id}] Submission from {sub.agent_id}: ${sub.bid:.4f}")
    return {"status": "accepted", "agent_id": sub.agent_id}


@app.get("/feedback/{request_id}/{agent_id}")
async def get_feedback(request_id: str, agent_id: str):
    """Agent polls for judge feedback on their submission."""
    state = active_games.get(request_id)
    if not state:
        raise HTTPException(404, "No active game")

    sub = state.submissions.get(agent_id)
    if not sub:
        return {"status": "no_submission"}

    if sub.score is None:
        return {"status": "pending"}

    if sub.score >= state.min_quality:
        return {"status": "qualified", "score": sub.score}

    return {
        "status": "feedback",
        "score": sub.score,
        "feedback": sub.feedback,
        "can_revise": sub.revision < state.max_revisions,
    }


# ── Status endpoint ───────────────────────────────────────────────────

@app.get("/status")
async def exchange_status():
    """Exchange health and stats."""
    totals = ledger.get_totals()
    return {
        "agents_registered": registry.count,
        "active_games": len(active_games),
        **totals,
    }
