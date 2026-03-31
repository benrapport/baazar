"""Public types exposed to SDK users (buyers and sellers)."""

from __future__ import annotations
from pydantic import BaseModel, Field


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
    capability: str = Field(..., min_length=1, max_length=256)
    input: str = Field(..., max_length=1_000_000)
    max_price: float = Field(..., gt=0)  # USD
    min_quality: int = Field(6, ge=1, le=10)
    timeout: float = Field(30.0, gt=0, le=300)


class SubmissionPayload(BaseModel):
    """What an agent POSTs back to the exchange with its work."""
    agent_id: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    bid: float = Field(..., ge=0)  # USD
    work: str


class AgentRegistration(BaseModel):
    """What an agent sends to register itself."""
    agent_id: str = Field(..., min_length=1, max_length=256)
    capabilities: list[str] = Field(..., min_length=1)
    callback_url: str = Field(..., min_length=5)


class BroadcastPayload(BaseModel):
    """What the exchange sends to agents when a request arrives."""
    request_id: str
    capability: str
    input: str
    max_price: float  # USD
    min_quality: int
    deadline_unix: float = 0.0  # when the game ends
