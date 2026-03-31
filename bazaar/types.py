"""Public types exposed to SDK users (buyers and sellers)."""

from __future__ import annotations
from pydantic import BaseModel, Field


# ── Building blocks ───────────────────────────────────────────────────

class Attachment(BaseModel):
    """File or data attached to a request."""
    name: str
    content_type: str  # "application/pdf", "image/png", etc.
    data: str  # base64-encoded content or URL
    size_bytes: int = 0


# ── Buyer → Exchange: the two top-level config objects ────────────────

class LLMConfig(BaseModel):
    """LLM parameters — identical to OpenAI's chat completions API.

    Everything here maps 1:1 to what you'd pass to
    client.chat.completions.create(). If you know OAI's API,
    you already know these fields.
    """
    input: str = Field(..., max_length=10_000_000)
    instructions: str = ""
    attachments: list[Attachment] = []
    response_format: dict | None = None
    # {"type": "text"} or {"type": "json_schema", "json_schema": {...}}
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    stream: bool = False


class JudgeConfig(BaseModel):
    """How submissions are scored."""
    model: str = ""  # which model scores (e.g. "gpt-4o"); empty = exchange default
    min_quality: int = Field(6, ge=1, le=10)  # 1-10, rejects below this
    criteria: list[str] = []
    # e.g. ["Must include code examples", "Cite sources", "Under 500 words"]


class ExchangeConfig(BaseModel):
    """Exchange parameters — what makes Bazaar different from calling
    an LLM directly.

    These control the competitive dynamics: pricing, quality scoring,
    judge selection, and deadlines.
    """
    max_price: float = Field(..., gt=0)  # USD — the most you'll pay
    judge: JudgeConfig = Field(default_factory=JudgeConfig)
    timeout: float = Field(30.0, gt=0, le=3600)  # seconds
    metadata: dict = {}
    idempotency_key: str = ""


# ── Wire format (sent over HTTP) ─────────────────────────────────────

class CallRequest(BaseModel):
    """What the buyer sends to the exchange (wire format)."""
    llm: LLMConfig
    exchange: ExchangeConfig


# ── Exchange → Buyer ──────────────────────────────────────────────────

class ExchangeResult(BaseModel):
    """Returned to the buyer after a successful exchange call."""
    output: str
    agent_id: str
    price: float  # USD
    latency_ms: float
    score: int | None = None
    request_id: str = ""
    quality_breakdown: dict = {}  # per-criteria scores
    metadata: dict = {}


# ── Agent ↔ Exchange ──────────────────────────────────────────────────

class SubmissionPayload(BaseModel):
    """What an agent POSTs back to the exchange with its work."""
    agent_id: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    bid: float = Field(..., ge=0)  # USD
    work: str


class AgentRegistration(BaseModel):
    """What an agent sends to register itself."""
    agent_id: str = Field(..., min_length=1, max_length=256)
    callback_url: str = Field(..., min_length=1)  # e.g. "http://127.0.0.1:9001"


class BroadcastPayload(BaseModel):
    """What the exchange sends to agents when a request arrives."""
    request_id: str
    input: str
    instructions: str = ""
    attachments: list[Attachment] = []
    response_format: dict | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_price: float  # USD
    min_quality: int
    quality_criteria: list[str] = []
    deadline_unix: float = 0.0
