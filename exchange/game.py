"""Game engine — broadcast, collect, judge, select.

Broadcast full request to ALL agents. Agents submit work + price.
Each submission triggers an immediate, concurrent judge evaluation.
Winner is the earliest-timestamped qualifying submission.
We never declare a winner while earlier submissions are still being judged.
"""

from __future__ import annotations
import asyncio
import logging
import time
import uuid

import httpx

from agentx.types import BroadcastPayload, ExchangeResult
from exchange.judge import Judge
from exchange.registry import Registry
from exchange.settlement import Ledger
from exchange.types import GameState, RegisteredAgent, Submission

logger = logging.getLogger(__name__)

MAX_REVISIONS = 3
HARD_TIMEOUT = 60.0
MIN_TIMEOUT = 1.0
MAX_TIMEOUT = 300.0
CHECK_INTERVAL = 0.05  # 50ms


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
    """Run a full game for one buyer request."""

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
    deadline = state.start_time + timeout

    payload = BroadcastPayload(
        request_id=request_id,
        capability=capability,
        input=input_text,
        max_price=max_price,
        min_quality=min_quality,
        deadline_unix=deadline,
    )

    logger.info(f"[{request_id}] Broadcasting to {len(agents)} agents")
    await _broadcast(payload, agents, deadline)

    result = await _wait_for_winner(state, judge, deadline)

    if result is None:
        raise TimeoutError(
            f"No qualifying submission within {timeout}s "
            f"({len(state.submissions)} submissions received)"
        )

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


# ── Broadcast ─────────────────────────────────────────────────────────

async def _broadcast(payload: BroadcastPayload,
                     agents: list[RegisteredAgent],
                     deadline: float) -> None:
    """Send full request to ALL agents. Fire-and-forget."""
    remaining = deadline - time.time()
    if remaining <= 0:
        return
    timeout_secs = min(5.0, remaining)
    semaphore = asyncio.Semaphore(50)

    async def send_limited(agent):
        async with semaphore:
            await _send_to_agent(client, agent, payload)

    async with httpx.AsyncClient(timeout=timeout_secs) as client:
        tasks = [send_limited(agent) for agent in agents]
        await asyncio.gather(*tasks, return_exceptions=True)


async def _send_to_agent(client: httpx.AsyncClient,
                         agent: RegisteredAgent,
                         payload: BroadcastPayload) -> None:
    try:
        url = f"{agent.callback_url}/request"
        await client.post(url, json=payload.model_dump())
        logger.debug(f"Broadcast to {agent.agent_id} OK")
    except Exception as e:
        logger.warning(f"Broadcast to {agent.agent_id} failed: {e}")


# ── Concurrent Judge ──────────────────────────────────────────────────

async def _wait_for_winner(state: GameState, judge: Judge,
                           deadline: float) -> ExchangeResult | None:
    """Spawn a judge task per submission. Pick winner by arrival time.

    Rules:
    - Each submission gets its own concurrent judge task
    - Judges only SCORE — they don't pick winners
    - The main loop (every 50ms) checks scored submissions
    - Winner = earliest-timestamped submission that qualifies
    - We NEVER declare a winner while an earlier submission is still being judged
    """
    scored_versions: dict[str, int] = {}  # agent_id -> revision we sent to judge
    judging: set[str] = set()             # agent_ids currently being judged
    judge_tasks: list[asyncio.Task] = []

    async def _score_one(agent_id: str, sub: Submission):
        """Score a submission. Only writes score — does NOT pick winner."""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, judge.score_submission, state.input, sub
            )
            with state.lock:
                if agent_id in state.submissions:
                    state.submissions[agent_id].score = result["score"]
                    state.submissions[agent_id].feedback = result["feedback"]
            logger.info(
                f"[{state.request_id}] {agent_id}: {result['score']}/10"
            )
        except Exception as e:
            logger.error(f"[{state.request_id}] Judge error for {agent_id}: {e}")
        finally:
            judging.discard(agent_id)

    while time.time() < deadline and not state.done:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        await asyncio.sleep(min(CHECK_INTERVAL, remaining))

        with state.lock:
            subs_snapshot = dict(state.submissions)

        # Spawn judges for new/revised submissions
        for agent_id, sub in subs_snapshot.items():
            prev_rev = scored_versions.get(agent_id, -1)
            if sub.revision > prev_rev and agent_id not in judging:
                scored_versions[agent_id] = sub.revision
                judging.add(agent_id)
                task = asyncio.create_task(_score_one(agent_id, sub))
                judge_tasks.append(task)

        # Check for winner among scored submissions
        # Only consider if NO earlier-timestamped submission is still being judged
        with state.lock:
            qualifiers = [
                (aid, sub) for aid, sub in state.submissions.items()
                if sub.score is not None
                and sub.score >= state.min_quality
                and sub.bid <= state.max_price
            ]

        if qualifiers:
            # Sort by bid (lowest), then timestamp (earliest)
            qualifiers.sort(key=lambda x: (x[1].bid, x[1].timestamp))
            best_aid, best_sub = qualifiers[0]

            # Is there an unscored submission that arrived EARLIER than our best?
            # If so, wait — it might qualify and beat our current best.
            earlier_unscored = any(
                sub.score is None and sub.timestamp < best_sub.timestamp
                for sub in subs_snapshot.values()
            )

            if not earlier_unscored:
                with state.lock:
                    if not state.done:
                        state.winner = best_aid
                        state.done = True
                return ExchangeResult(
                    output=best_sub.work,
                    agent_id=best_aid,
                    price=best_sub.bid,
                    latency_ms=(time.time() - state.start_time) * 1000,
                    score=best_sub.score,
                )

    # Deadline passed — wait briefly for in-flight judges
    if judge_tasks:
        await asyncio.wait(judge_tasks, timeout=5.0)

    # Return best scored submission as fallback
    with state.lock:
        subs = dict(state.submissions)

    scored = [(aid, sub) for aid, sub in subs.items() if sub.score is not None]
    if scored:
        best_aid, best_sub = min(scored, key=lambda x: (-x[1].score, x[1].bid))
        with state.lock:
            state.winner = best_aid
            state.done = True
        return ExchangeResult(
            output=best_sub.work,
            agent_id=best_aid,
            price=best_sub.bid,
            latency_ms=(time.time() - state.start_time) * 1000,
            score=best_sub.score,
        )

    return None


# ── Helpers (used by tests + external callers) ────────────────────────

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
