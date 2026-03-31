"""Internal exchange types — not exposed to SDK users."""

from __future__ import annotations
import threading
import time
import uuid
from pydantic import BaseModel, ConfigDict, Field

from exchange.market_log import MarketLog


class RegisteredAgent(BaseModel):
    agent_id: str
    callback_url: str = ""  # optional — empty if agent uses WebSocket/poll
    status: str = "active"
    registered_at: float = Field(default_factory=time.time)


class Submission(BaseModel):
    agent_id: str
    request_id: str
    bid: float  # USD
    work: str
    timestamp: float = Field(default_factory=time.time)
    score: int | None = None
    feedback: str | None = None
    revision: int = 0  # 0 = first attempt, 1+ = revisions


class Transaction(BaseModel):
    tx_id: str = Field(default_factory=lambda: f"tx_{uuid.uuid4().hex[:12]}")
    request_id: str
    buyer_id: str
    agent_id: str
    price: float  # USD
    exchange_fee: float  # USD
    buyer_charged: float  # USD
    score: int | None = None
    latency_ms: float = 0.0
    timestamp: float = Field(default_factory=time.time)


class GameState(BaseModel):
    """Tracks the state of a single request's competition. Thread-safe."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    request_id: str
    input: str
    max_price: float  # USD
    min_quality: int
    quality_criteria: list[str] = []  # buyer-defined scoring criteria
    buyer_id: str
    start_time: float = Field(default_factory=time.time)
    submissions: dict[str, Submission] = {}
    winner: str | None = None
    done: bool = False
    timeout: float = 60.0
    lock: threading.Lock = Field(default_factory=threading.Lock, exclude=True)
    market_log: MarketLog | None = Field(default=None, exclude=True)
