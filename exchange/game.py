"""Game engine — broadcast, collect, judge, select.

Broadcast full request to ALL agents. Agents submit work.
Each submission triggers an immediate, concurrent judge evaluation.
Winner is the earliest-timestamped qualifying submission.
We never declare a winner while earlier submissions are still being judged.
RFQ model: buyer sets the fill price (max_price). No supply-side bidding.
"""

from __future__ import annotations
import asyncio
import logging
import time
import uuid

import httpx

from bazaar.types import BroadcastPayload, ExchangeResult, LLMConfig
from exchange.judge import Judge
from exchange.market_log import MarketLog, MarketLogStore
from exchange.registry import Registry
from exchange.settlement import Ledger
from exchange.types import GameState, RegisteredAgent, Submission

logger = logging.getLogger(__name__)

HARD_TIMEOUT = 60.0
CHECK_INTERVAL = 0.025  # 25ms


async def run_game(
    input_text: str,
    max_price: float,
    min_quality: int,
    buyer_id: str,
    registry: Registry,
    judge: Judge,
    ledger: Ledger,
    timeout: float = HARD_TIMEOUT,
    quality_criteria: list[str] | None = None,
    state: GameState | None = None,
    llm_config: LLMConfig | None = None,
    market_log_store: MarketLogStore | None = None,
) -> ExchangeResult:
    """Run a full game for one buyer request."""

    if max_price <= 0:
        raise ValueError("max_price must be positive")
    min_quality = max(1, min(10, min_quality))
    timeout = max(1.0, timeout)

    agents = registry.get_active_agents()
    if not agents:
        raise ValueError("No agents registered")

    if state is None:
        state = GameState(
            request_id=f"req_{uuid.uuid4().hex[:12]}",
            input=input_text,
            max_price=max_price,
            min_quality=min_quality,
            quality_criteria=quality_criteria or [],
            buyer_id=buyer_id,
            timeout=timeout,
        )

    request_id = state.request_id
    deadline = state.start_time + timeout

    # Initialize market log
    mlog = MarketLog(
        request_id=request_id,
        input=input_text,
        max_price=max_price,
        min_quality=min_quality,
        quality_criteria=quality_criteria or [],
        buyer_id=buyer_id,
        agents_invited=[a.agent_id for a in agents],
        opened_at=state.start_time,
    )
    state.market_log = mlog
    mlog.emit("market_opened", timeout=timeout)

    llm = llm_config
    payload = BroadcastPayload(
        request_id=request_id,
        input=input_text,
        instructions=llm.instructions if llm else "",
        attachments=llm.attachments if llm else [],
        response_format=llm.response_format if llm else None,
        max_tokens=llm.max_tokens if llm else None,
        temperature=llm.temperature if llm else None,
        top_p=llm.top_p if llm else None,
        max_price=max_price,
        min_quality=min_quality,
        quality_criteria=quality_criteria or [],
        deadline_unix=deadline,
    )

    logger.info(f"[{request_id}] Broadcasting to {len(agents)} agents")
    await _broadcast(payload, agents, deadline, mlog)

    result = await _wait_for_winner(state, judge, deadline)

    if result is None:
        mlog.emit(
            "market_timeout",
            submissions_received=len(state.submissions),
            timeout=timeout,
        )
        mlog.closed_at = time.time()
        if market_log_store:
            market_log_store.store(mlog)
        raise TimeoutError(
            f"No qualifying submission within {timeout}s "
            f"({len(state.submissions)} submissions received)"
        )

    winner_sub = state.submissions[result.agent_id]
    tx = ledger.record(
        request_id=request_id,
        buyer_id=buyer_id,
        agent_id=result.agent_id,
        price=max_price,
        score=winner_sub.score,
        latency_ms=result.latency_ms,
    )

    mlog.emit(
        "winner_selected",
        agent_id=result.agent_id,
        fill_price=max_price,
        score=winner_sub.score,
        latency_ms=result.latency_ms,
        reason="earliest qualifying submission",
    )
    mlog.emit(
        "market_settled",
        tx_id=tx.tx_id,
        agent_id=result.agent_id,
        fill_price=max_price,
        exchange_fee=tx.exchange_fee,
        buyer_charged=tx.buyer_charged,
    )
    mlog.winner = result.agent_id
    mlog.closed_at = time.time()

    if market_log_store:
        market_log_store.store(mlog)

    logger.info(
        f"[{request_id}] Winner: {result.agent_id} @ ${max_price:.4f} "
        f"(score {winner_sub.score}/10, fee ${tx.exchange_fee:.4f})"
    )

    result.request_id = request_id
    return result


# ── Broadcast ─────────────────────────────────────────────────────────

async def _broadcast(payload: BroadcastPayload,
                     agents: list[RegisteredAgent],
                     deadline: float,
                     mlog: MarketLog) -> None:
    """Send full request to ALL agents. Fire-and-forget."""
    remaining = deadline - time.time()
    if remaining <= 0:
        return
    timeout_secs = min(5.0, remaining)
    semaphore = asyncio.Semaphore(50)

    async def send_limited(agent):
        async with semaphore:
            await _send_to_agent(client, agent, payload, mlog)

    async with httpx.AsyncClient(timeout=timeout_secs) as client:
        tasks = [send_limited(agent) for agent in agents]
        await asyncio.gather(*tasks, return_exceptions=True)


async def _send_to_agent(client: httpx.AsyncClient,
                         agent: RegisteredAgent,
                         payload: BroadcastPayload,
                         mlog: MarketLog) -> None:
    try:
        url = f"{agent.callback_url}/request"
        await client.post(url, json=payload.model_dump())
        mlog.emit("broadcast_sent", agent_id=agent.agent_id, status="ok")
        logger.debug(f"Broadcast to {agent.agent_id} OK")
    except Exception as e:
        mlog.emit("broadcast_failed", agent_id=agent.agent_id, error=str(e))
        logger.warning(f"Broadcast to {agent.agent_id} failed: {e}")


# ── Concurrent Judge ──────────────────────────────────────────────────

async def _wait_for_winner(state: GameState, judge: Judge,
                           deadline: float) -> ExchangeResult | None:
    """Spawn a judge task per submission. Pick winner by arrival time.

    Rules:
    - Each submission gets its own concurrent judge task
    - Judges only SCORE — they don't pick winners
    - The main loop (every 25ms) checks scored submissions
    - Winner = earliest-timestamped submission that qualifies
    - We NEVER declare a winner while an earlier submission is still being judged
    """
    scored_versions: dict[str, int] = {}  # agent_id -> revision we sent to judge
    judging: set[str] = set()             # agent_ids currently being judged
    judge_tasks: list[asyncio.Task] = []
    mlog = state.market_log

    async def _score_one(agent_id: str, sub: Submission):
        """Score a submission. Only writes score — does NOT pick winner."""
        if mlog:
            mlog.emit("judge_started", agent_id=agent_id, revision=sub.revision)
        try:
            criteria = state.quality_criteria or None
            result = await asyncio.to_thread(
                judge.score_submission, state.input, sub, criteria
            )
            with state.lock:
                if agent_id in state.submissions:
                    state.submissions[agent_id].score = result["score"]
                    state.submissions[agent_id].feedback = result["feedback"]
            if mlog:
                mlog.emit(
                    "judge_completed",
                    agent_id=agent_id,
                    score=result["score"],
                    feedback=result["feedback"],
                    qualified=result["score"] >= state.min_quality,
                )
            logger.info(
                f"[{state.request_id}] {agent_id}: {result['score']}/10"
            )
        except Exception as e:
            if mlog:
                mlog.emit("judge_error", agent_id=agent_id, error=str(e))
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
            ]

        if qualifiers:
            # Sort by timestamp (earliest first — first to fill wins)
            qualifiers.sort(key=lambda x: x[1].timestamp)
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
                    price=state.max_price,
                    latency_ms=(time.time() - state.start_time) * 1000,
                    score=best_sub.score,
                )

    # Deadline passed — no qualifier found. Order not filled.
    with state.lock:
        state.done = True
    return None


# ── Helpers (used by tests + external callers) ────────────────────────

def _get_qualifiers(state: GameState) -> list[str]:
    """Return agent IDs whose submissions meet quality threshold."""
    with state.lock:
        return [
            aid for aid, sub in state.submissions.items()
            if sub.score is not None
            and sub.score >= state.min_quality
        ]


def _select_winner(state: GameState,
                   qualifiers: list[str]) -> ExchangeResult:
    """Pick earliest-timestamped qualifier. First to arrive wins."""
    with state.lock:
        winner = min(
            qualifiers,
            key=lambda aid: state.submissions[aid].timestamp,
        )
        sub = state.submissions[winner]
        state.winner = winner
        state.done = True

    return ExchangeResult(
        output=sub.work,
        agent_id=winner,
        price=state.max_price,
        latency_ms=(time.time() - state.start_time) * 1000,
        score=sub.score,
    )


def receive_submission(state: GameState, agent_id: str,
                       work: str) -> bool:
    """Called when an agent POSTs a submission. Returns True if accepted.

    RFQ model: no bid — buyer's max_price is the fill price.
    """
    mlog = state.market_log

    with state.lock:
        if state.done:
            if mlog:
                mlog.emit("submission_rejected", agent_id=agent_id,
                          reason="market closed")
            return False

        existing = state.submissions.get(agent_id)
        revision = (existing.revision + 1) if existing else 0

        state.submissions[agent_id] = Submission(
            agent_id=agent_id,
            request_id=state.request_id,
            work=work,
            revision=revision,
        )
        if mlog:
            mlog.emit("submission_received", agent_id=agent_id,
                       revision=revision)
        return True
