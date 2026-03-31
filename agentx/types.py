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


class ToolDef(BaseModel):
    """Tool definition the agent is allowed to use."""
    name: str
    description: str = ""
    input_schema: dict = {}  # JSON Schema for tool inputs


# ── Buyer → Exchange ──────────────────────────────────────────────────

class CallRequest(BaseModel):
    """What the buyer sends to the exchange."""

    # What work to do
    capability: str = Field(..., min_length=1, max_length=256)
    input: str = Field(..., max_length=10_000_000)  # 10MB
    instructions: str = ""  # system-level guidance for the agent
    attachments: list[Attachment] = []

    # Output requirements
    output_schema: dict | None = None  # JSON Schema for structured output
    output_format: str = "text"  # "text", "json", "markdown"
    stream: bool = False

    # Economics
    max_price: float = Field(..., gt=0)  # USD
    timeout: float = Field(30.0, gt=0, le=3600)  # up to 1 hour

    # Quality
    min_quality: int = Field(6, ge=1, le=10)
    quality_criteria: list[str] = []
    # e.g. ["Must include code examples", "Cite sources", "Under 500 words"]

    # Tool control
    tools: list[ToolDef] = []
    tool_choice: str = "auto"  # "auto", "any", "none"

    # Metadata
    user_id: str = ""
    idempotency_key: str = ""
    metadata: dict = {}


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
    capabilities: list[str] = Field(..., min_length=1)
    # No callback_url — agents connect via WebSocket or poll


class BroadcastPayload(BaseModel):
    """What the exchange sends to agents when a request arrives."""
    request_id: str
    capability: str
    input: str
    instructions: str = ""
    attachments: list[Attachment] = []
    max_price: float  # USD
    min_quality: int
    quality_criteria: list[str] = []
    tools: list[ToolDef] = []
    tool_choice: str = "auto"
    output_schema: dict | None = None
    output_format: str = "text"
    deadline_unix: float = 0.0
