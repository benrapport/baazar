"""Game engine — broadcast, collect, judge, select.

Broadcast full request to ALL agents. Agents submit work + price.
Judge scores as submissions arrive. First qualifier wins.
"""

from __future__ import annotations
import asyncio
import logging
import threading
import time
import uuid

import httpx

from agentx.types import BroadcastPayload, ExchangeResult
from exchange.judge import Judge
from exchange.registry import Registry
from exchange.settlement import Ledger
from exchange.types import GameState, RegisteredAgent, Submission

logger = logging.getLogger(__name__)

JUDGE_POLL_INTERVAL = 2.0
MAX_REVISIONS = 3
HARD_TIMEOUT = 60.0
MIN_TIMEOUT = 1.0
MAX_TIMEOUT = 300.0


async def run_game(
    capability: str,
    input_text: str,
    max_price: float,
    min_quality: int,
    buyer_id: str,
    registry: Registry,
    judge: Judge,
    ledger: Ledger,
    timeout: float = HARD_TIMEOUT,
    state: GameState | None = None,
) -> ExchangeResult:
    """Run a full game for one buyer request. Returns the winning result."""

    # Validate inputs
    if max_price <= 0:
        raise ValueError("max_price must be positive")
    min_quality = max(1, min(10, min_quality))
    timeout = max(MIN_TIMEOUT, min(MAX_TIMEOUT, timeout))

    agents = registry.get_agents_for_capability(capability)
    if not agents:
        raise ValueError(f"No agents registered for capability '{capability}'")

    if state is None:
        state = GameState(
            request_id=f"req_{uuid.uuid4().hex[:12]}",
            capability=capability,
            input=input_text,
            max_price=max_price,
            min_quality=min_quality,
            buyer_id=buyer_id,
            timeout=timeout,
        )

    request_id = state.request_id

    # Broadcast full request to ALL agents
    payload = BroadcastPayload(
        request_id=request_id,
        capability=capability,
        input=input_text,
        max_price=max_price,
        min_quality=min_quality,
        deadline_unix=deadline,
    )

    deadline = state.start_time + timeout
    logger.info(f"[{request_id}] Broadcasting to {len(agents)} agents")
    await _broadcast(payload, agents, deadline)

    # Poll for submissions until we have a winner or timeout
    result = await _judge_loop(state, judge, timeout)

    if result is None:
        raise TimeoutError(
            f"No qualifying submission within {timeout}s "
            f"({len(state.submissions)} submissions received)"
        )

    # Record transaction
    winner_sub = state.submissions[result.agent_id]
    tx = ledger.record(
        request_id=request_id,
        buyer_id=buyer_id,
        agent_id=result.agent_id,
        capability=capability,
        price=winner_sub.bid,
        buyer_max=max_price,
        score=winner_sub.score,
        latency_ms=result.latency_ms,
    )
    logger.info(
        f"[{request_id}] Winner: {result.agent_id} @ ${winner_sub.bid:.4f} "
        f"(score {winner_sub.score}/10, fee ${tx.exchange_fee:.4f})"
    )

    result.request_id = request_id
    return result


async def _broadcast(payload: BroadcastPayload,
                     agents: list[RegisteredAgent],
                     deadline: float) -> None:
    """Send full request to ALL agents. Fire-and-forget."""
    remaining = deadline - time.time()
    if remaining <= 0:
        return
    timeout_secs = min(5.0, remaining)
    semaphore = asyncio.Semaphore(50)  # limit concurrent broadcasts

    async def send_limited(agent):
        async with semaphore:
            await _send_to_agent(client, agent, payload)

    async with httpx.AsyncClient(timeout=timeout_secs) as client:
        tasks = [send_limited(agent) for agent in agents]
        await asyncio.gather(*tasks, return_exceptions=True)


async def _send_to_agent(client: httpx.AsyncClient,
                         agent: RegisteredAgent,
                         payload: BroadcastPayload) -> None:
    """Send request to a single agent's callback URL."""
    try:
        url = f"{agent.callback_url}/request"
        await client.post(url, json=payload.model_dump())
        logger.debug(f"Broadcast to {agent.agent_id} OK")
    except Exception as e:
        logger.warning(f"Broadcast to {agent.agent_id} failed: {e}")


async def _judge_loop(state: GameState, judge: Judge,
                      timeout: float) -> ExchangeResult | None:
    """Poll for submissions, score them, handle feedback. Return winner."""
    deadline = state.start_time + timeout
    scored_versions: dict[str, int] = {}  # agent_id -> last scored revision

    while time.time() < deadline and not state.done:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        await asyncio.sleep(min(JUDGE_POLL_INTERVAL, remaining))

        # Snapshot submissions (thread-safe read)
        with state.lock:
            current_subs = dict(state.submissions)

        if not current_subs:
            continue

        # Find new or revised submissions to score
        to_score: dict[str, Submission] = {}
        for agent_id, sub in current_subs.items():
            prev_rev = scored_versions.get(agent_id, -1)
            if sub.revision > prev_rev:
                to_score[agent_id] = sub

        if not to_score:
            qualifiers = _get_qualifiers(state)
            if qualifiers:
                return _select_winner(state, qualifiers)
            continue

        # Score new submissions (judge handles its own errors)
        logger.info(f"[{state.request_id}] Scoring {len(to_score)} submissions")
        if len(to_score) == 1:
            agent_id, sub = next(iter(to_score.items()))
            result = judge.score_submission(state.input, sub)
            with state.lock:
                if agent_id in state.submissions:
                    state.submissions[agent_id].score = result["score"]
                    state.submissions[agent_id].feedback = result["feedback"]
            scored_versions[agent_id] = sub.revision
        else:
            results = judge.score_batch(state.input, to_score)
            with state.lock:
                for agent_id in to_score:
                    if agent_id in results and agent_id in state.submissions:
                        state.submissions[agent_id].score = results[agent_id]["score"]
                        state.submissions[agent_id].feedback = results[agent_id]["feedback"]
                        scored_versions[agent_id] = to_score[agent_id].revision

        # Check for qualifiers
        qualifiers = _get_qualifiers(state)
        if qualifiers:
            return _select_winner(state, qualifiers)

    # Timeout — accept best available submission
    with state.lock:
        subs = dict(state.submissions)

    if subs:
        scored = [
            (aid, sub) for aid, sub in subs.items()
            if sub.score is not None
        ]
        if scored:
            best = min(scored, key=lambda x: (-x[1].score, x[1].bid))
            agent_id, sub = best
            with state.lock:
                state.winner = agent_id
                state.done = True
            return ExchangeResult(
                output=sub.work,
                agent_id=agent_id,
                price=sub.bid,
                latency_ms=(time.time() - state.start_time) * 1000,
                score=sub.score,
            )

    return None


def _get_qualifiers(state: GameState) -> list[str]:
    """Return agent IDs whose submissions meet quality threshold."""
    with state.lock:
        return [
            aid for aid, sub in state.submissions.items()
            if sub.score is not None
            and sub.score >= state.min_quality
            and sub.bid <= state.max_price
        ]


def _select_winner(state: GameState,
                   qualifiers: list[str]) -> ExchangeResult:
    """Pick lowest bid among qualifiers. Ties broken by timestamp."""
    with state.lock:
        winner = min(
            qualifiers,
            key=lambda aid: (
                state.submissions[aid].bid,
                state.submissions[aid].timestamp,
            ),
        )
        sub = state.submissions[winner]
        state.winner = winner
        state.done = True

    return ExchangeResult(
        output=sub.work,
        agent_id=winner,
        price=sub.bid,
        latency_ms=(time.time() - state.start_time) * 1000,
        score=sub.score,
    )


def receive_submission(state: GameState, agent_id: str,
                       bid: float, work: str) -> bool:
    """Called when an agent POSTs a submission. Returns True if accepted."""
    with state.lock:
        if state.done:
            return False
        if bid > state.max_price:
            return False
        if bid < 0:
            return False

        existing = state.submissions.get(agent_id)

        # Enforce max revisions
        if existing and existing.revision >= state.max_revisions:
            return False

        revision = (existing.revision + 1) if existing else 0

        state.submissions[agent_id] = Submission(
            agent_id=agent_id,
            request_id=state.request_id,
            bid=bid,
            work=work,
            revision=revision,
        )
        return True
