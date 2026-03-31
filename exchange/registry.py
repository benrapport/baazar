"""Agent registry — in-memory, thread-safe, no filtering."""

from __future__ import annotations
import threading
from exchange.types import RegisteredAgent


class Registry:
    def __init__(self):
        self._agents: dict[str, RegisteredAgent] = {}
        self._lock = threading.Lock()

    def register(self, agent_id: str, capabilities: list[str],
                 callback_url: str) -> RegisteredAgent:
        agent = RegisteredAgent(
            agent_id=agent_id,
            capabilities=capabilities,
            callback_url=callback_url,
        )
        with self._lock:
            self._agents[agent_id] = agent
        return agent

    def unregister(self, agent_id: str) -> bool:
        with self._lock:
            return self._agents.pop(agent_id, None) is not None

    def get_agents_for_capability(self, capability: str) -> list[RegisteredAgent]:
        """Return ALL active agents with this capability. No filtering."""
        with self._lock:
            return [
                a for a in self._agents.values()
                if capability in a.capabilities and a.status == "active"
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
