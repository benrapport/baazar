"""Agent registry — in-memory, thread-safe, no filtering."""

from __future__ import annotations
import threading
from urllib.parse import urlparse
from exchange.types import RegisteredAgent


class Registry:
    def __init__(self):
        self._agents: dict[str, RegisteredAgent] = {}
        self._lock = threading.Lock()

    def register(self, agent_id: str,
                 callback_url: str = "") -> RegisteredAgent:
        if callback_url:
            parsed = urlparse(callback_url)
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"Invalid callback_url scheme: {parsed.scheme}")
            if not parsed.netloc:
                raise ValueError(f"Invalid callback_url: missing host")

        agent = RegisteredAgent(
            agent_id=agent_id,
            callback_url=callback_url,
        )
        with self._lock:
            self._agents[agent_id] = agent
        return agent

    def unregister(self, agent_id: str) -> bool:
        with self._lock:
            return self._agents.pop(agent_id, None) is not None

    def get_active_agents(self) -> list[RegisteredAgent]:
        """Return ALL active agents. No filtering."""
        with self._lock:
            return [
                a for a in self._agents.values()
                if a.status == "active"
            ]

    def get_all_agents(self) -> list[RegisteredAgent]:
        with self._lock:
            return list(self._agents.values())

    def get_agent(self, agent_id: str) -> RegisteredAgent | None:
        with self._lock:
            return self._agents.get(agent_id)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._agents)
