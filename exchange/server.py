"""FastAPI exchange server — the gateway."""

from __future__ import annotations
import asyncio
import concurrent.futures
import logging
import os
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException, Header
from openai import OpenAI

from bazaar.types import (
    AgentRegistration, CallRequest, ExchangeResult, SubmissionPayload,
)
from exchange.game import receive_submission, run_game
from exchange.judge import Judge
from exchange.market_log import MarketLogStore
from exchange.registry import Registry
from exchange.settlement import Ledger
from exchange.types import GameState

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Bazaar Exchange", version="0.1.0")

@app.on_event("startup")
def _expand_thread_pool():
    """Judge scoring is I/O bound (OpenAI API calls). Default pool ~16 threads
    bottlenecks when many submissions arrive concurrently."""
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=64)
    asyncio.get_event_loop().set_default_executor(pool)


@app.on_event("shutdown")
def _shutdown():
    """Flush and close market log file handle."""
    market_log_store.close()


# Singletons — lazy init for OpenAI client (env may not be loaded at import)
registry = Registry()
ledger = Ledger()
_market_log_path = os.environ.get("MARKET_LOG_PATH", "")
market_log_store = MarketLogStore(output_path=_market_log_path or None)
active_games: dict[str, GameState] = {}
_games_lock = threading.Lock()
_judge: Judge | None = None


def _get_judge() -> Judge:
    global _judge
    if _judge is None:
        _judge = Judge(client=OpenAI())
    return _judge


def configure_market_log_path(path: str):
    """Set the JSONL output path for market logs. Called before server starts."""
    global market_log_store
    market_log_store = MarketLogStore(output_path=path)


# Simple API key auth (demo mode: "demo" key always works)
VALID_API_KEYS = {"demo", os.environ.get("BAZAAR_API_KEY", "demo")}


def _check_auth(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or malformed Authorization header")
    key = authorization[7:]  # strip "Bearer " prefix
    if not key or key not in VALID_API_KEYS:
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

    llm = req.llm
    exc = req.exchange

    # Create game state so agents can submit while game runs
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    state = GameState(
        request_id=request_id,
        input=llm.input,
        max_price=exc.max_price,
        min_quality=exc.judge.min_quality,
        quality_criteria=exc.judge.criteria,
        buyer_id=buyer_id,
    )
    with _games_lock:
        active_games[request_id] = state

    try:
        result = await run_game(
            input_text=llm.input,
            max_price=exc.max_price,
            min_quality=exc.judge.min_quality,
            buyer_id=buyer_id,
            registry=registry,
            judge=_get_judge(),
            ledger=ledger,
            timeout=exc.timeout,
            quality_criteria=exc.judge.criteria,
            state=state,
            llm_config=llm,
            market_log_store=market_log_store,
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
        callback_url=reg.callback_url,
    )
    logger.info(f"Registered agent: {agent.agent_id} @ {agent.callback_url}")
    return {"status": "registered", "agent_id": agent.agent_id}


@app.post("/submit/{request_id}")
async def submit_work(request_id: str, sub: SubmissionPayload):
    """Agent submits work + price for an active request."""
    state = active_games.get(request_id)
    if not state:
        raise HTTPException(404, f"No active game for request {request_id}")

    accepted = receive_submission(state, sub.agent_id, sub.work)
    if not accepted:
        raise HTTPException(400, "Submission rejected (market closed)")

    logger.info(f"[{request_id}] Submission from {sub.agent_id}")
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
        "can_revise": not state.done,
    }


# ── Market log endpoints ─────────────────────────────────────────────

@app.get("/markets")
async def list_markets():
    """List all completed market logs."""
    logs = market_log_store.get_all()
    return [
        {
            "request_id": log.request_id,
            "winner": log.winner,
            "agents_invited": log.agents_invited,
            "num_events": len(log.events),
            "opened_at": log.opened_at,
            "closed_at": log.closed_at,
        }
        for log in logs
    ]


@app.get("/markets/{request_id}")
async def get_market(request_id: str):
    """Get full market log for a request."""
    log = market_log_store.get(request_id)
    if not log:
        raise HTTPException(404, f"No market log for {request_id}")
    return log.to_dict()


# ── Status endpoint ───────────────────────────────────────────────────

@app.get("/status")
async def exchange_status():
    """Exchange health and stats."""
    totals = ledger.get_totals()
    return {
        "agents_registered": registry.count,
        "active_games": len(active_games),
        "completed_markets": len(market_log_store.get_all()),
        **totals,
    }
