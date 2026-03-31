"""Public types exposed to SDK users (buyers and sellers)."""

from __future__ import annotations
from pydantic import BaseModel


class ExchangeResult(BaseModel):
    """Returned to the buyer after a successful exchange call."""
    output: str
    agent_id: str
    price: float  # USD
    latency_ms: float
    score: int | None = None
    request_id: str = ""


class CallRequest(BaseModel):
    """What the buyer sends to the exchange."""
    capability: str
    input: str
    max_price: float  # USD
    min_quality: int = 6
    timeout: float = 30.0


class SubmissionPayload(BaseModel):
    """What an agent POSTs back to the exchange with its work."""
    agent_id: str
    request_id: str
    bid: float  # USD
    work: str


class AgentRegistration(BaseModel):
    """What an agent sends to register itself."""
    agent_id: str
    capabilities: list[str]
    callback_url: str


class BroadcastPayload(BaseModel):
    """What the exchange sends to agents when a request arrives."""
    request_id: str
    capability: str
    input: str
    max_price: float  # USD
    min_quality: int
