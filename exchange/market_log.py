"""Market log — full event timeline for each request (market).

Each market is one buyer request. The log captures every event that happens
on the exchange for that request: broadcast, bids, rejections, judging,
winner selection, settlement.
"""

from __future__ import annotations
import json
import threading
import time
from pathlib import Path
from pydantic import BaseModel, Field


class MarketEvent(BaseModel):
    """Single event in a market's timeline."""
    type: str
    timestamp: float = Field(default_factory=time.time)
    data: dict = {}


class MarketLog(BaseModel):
    """Full log for one market (request)."""
    request_id: str
    input: str
    max_price: float
    min_quality: int
    quality_criteria: list[str] = []
    buyer_id: str
    agents_invited: list[str] = []
    opened_at: float = Field(default_factory=time.time)
    closed_at: float | None = None
    winner: str | None = None
    events: list[MarketEvent] = []

    def emit(self, event_type: str, **data):
        """Append an event to the log."""
        self.events.append(MarketEvent(type=event_type, data=data))

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return self.model_dump()


class MarketLogStore:
    """Thread-safe store for completed market logs. Optionally streams to JSONL."""

    def __init__(self, output_path: str | Path | None = None):
        self._logs: dict[str, MarketLog] = {}
        self._lock = threading.Lock()
        self._file = None
        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(p, "w")

    def store(self, log: MarketLog):
        """Store a completed market log and optionally write to JSONL."""
        with self._lock:
            self._logs[log.request_id] = log
            if self._file:
                self._file.write(json.dumps(log.to_dict()) + "\n")
                self._file.flush()

    def get(self, request_id: str) -> MarketLog | None:
        with self._lock:
            return self._logs.get(request_id)

    def get_all(self) -> list[MarketLog]:
        with self._lock:
            return list(self._logs.values())

    def close(self):
        if self._file:
            self._file.close()
            self._file = None
