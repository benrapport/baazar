"""Launch a fleet of tool-calling agents for the simulation.

Each agent gets its own AgentProvider (HTTP server on a unique port),
wrapping a ClaudeCodeAgent with a specific model config.
"""

import logging
import threading
from dataclasses import dataclass, field

from agent.runtime import ClaudeCodeAgent, AgentConfig
from bazaar.provider import AgentProvider
from constants.models import Model
from sim.strategy import assess_difficulty, should_fill

logger = logging.getLogger(__name__)

@dataclass
class FleetMember:
    agent_id: str
    config: AgentConfig
    port: int


# ── Fleet generation ──────────────────────────────────────────────────

# Strategy archetypes: (name_suffix, min_margin, system_prompt_flavor)
# min_margin: how much profit margin required to fill (lower = more aggressive)
STRATEGIES = [
    ("agg", 0.1, "Be aggressive. Fill fast, accept thin margins. Speed wins."),
    ("bal", 0.5, "Balance cost and quality. Fill at reasonable margins."),
    ("con", 1.5, "Be conservative. Only fill when margins are large."),
    ("sniper", 0.05, "Fill everything you can. Accept razor-thin margins."),
    ("premium", 2.0, "Premium quality. Only fill high-margin tasks."),
]

# Model tiers for fleet composition
CHEAP_MODELS = [Model.GPT_4O_MINI, Model.GPT_4_1_MINI]
MID_MODELS = [Model.GPT_4O, Model.GPT_4_1]
PREMIUM_MODELS = [Model.O4_MINI]

MODEL_SHORT_NAMES = {
    Model.GPT_4O_MINI: "4omini",
    Model.GPT_4_1_MINI: "41mini",
    Model.GPT_4O: "4o",
    Model.GPT_4_1: "41",
    Model.O4_MINI: "o4m",
}

MODEL_TURNS = {
    Model.GPT_4O_MINI: 5,
    Model.GPT_4_1_MINI: 8,
    Model.GPT_4O: 8,
    Model.GPT_4_1: 10,
    Model.O4_MINI: 12,
}


def generate_fleet(size: int = 50, base_port: int = 9001) -> list[FleetMember]:
    """Generate a diverse fleet of agents.

    Cycles through models and strategies to create variety.
    Cheap models get more agents (they compete on volume).
    """
    # Weight: cheap models get 3x slots, mid get 2x, premium get 1x
    model_pool = (
        CHEAP_MODELS * 3 +   # 6 cheap model slots
        MID_MODELS * 2 +     # 4 mid model slots
        PREMIUM_MODELS * 1   # 1 premium model slot
    )  # 11 slots per cycle

    members = []
    for i in range(size):
        model = model_pool[i % len(model_pool)]
        strategy_name, min_margin, prompt_flavor = STRATEGIES[i % len(STRATEGIES)]
        model_name = MODEL_SHORT_NAMES[model]
        max_turns = MODEL_TURNS[model]

        agent_id = f"{model_name}-{strategy_name}-{i:02d}"
        system_prompt = (
            f"You are agent {agent_id}. {prompt_flavor} "
            "Be concise and efficient in your responses."
        )

        members.append(FleetMember(
            agent_id=agent_id,
            config=AgentConfig(
                model=model,
                system_prompt=system_prompt,
                max_turns=max_turns,
                min_margin=min_margin,
            ),
            port=base_port + i,
        ))

    return members


# Default fleet: 5 agents (backward compatible)
DEFAULT_FLEET: list[FleetMember] = [
    FleetMember("nano-agent", AgentConfig(model=Model.GPT_4O_MINI, system_prompt="You are a fast, cheap agent. Be concise and efficient.", max_turns=5), port=9001),
    FleetMember("mini-agent", AgentConfig(model=Model.GPT_4_1_MINI, system_prompt="You are a balanced agent. Good quality at reasonable cost.", max_turns=8), port=9002),
    FleetMember("standard-agent", AgentConfig(model=Model.GPT_4_1, system_prompt="You are a premium agent. Produce excellent, thorough work.", max_turns=10), port=9003),
    FleetMember("fast-agent", AgentConfig(model=Model.GPT_4O, system_prompt="You are a fast, capable agent. Optimize for speed and accuracy.", max_turns=8), port=9004),
    FleetMember("reasoning-agent", AgentConfig(model=Model.O4_MINI, system_prompt="You are a reasoning-focused agent. Think step by step.", max_turns=12), port=9005),
]


class Fleet:
    """Manages a fleet of agent servers."""

    def __init__(self, members: list[FleetMember] | None = None, exchange_url: str = "http://localhost:8000"):
        self.members = members or DEFAULT_FLEET
        self.exchange_url = exchange_url
        self._threads: list[threading.Thread] = []
        self._agents: dict[str, ClaudeCodeAgent] = {}  # agent_id -> agent instance

    def launch(self):
        """Start all agents in background threads."""
        for member in self.members:
            agent = ClaudeCodeAgent(member.config)
            self._agents[member.agent_id] = agent

            def make_handler(agent_id: str, agent: ClaudeCodeAgent, config: AgentConfig):
                margin = getattr(config, 'min_margin', 0.5)

                def handler(request: dict) -> dict | None:
                    """Handler for AgentProvider. Receives payload.model_dump() dict."""
                    try:
                        task_input = request["input"]
                        max_price = request["max_price"]
                        deadline_unix = request.get("deadline_unix", 0)

                        # Assess task difficulty
                        difficulty_info = assess_difficulty(task_input)

                        # Decide fill/pass
                        fill = should_fill(
                            difficulty=difficulty_info,
                            max_price=max_price,
                            model=config.model,
                            budget_remaining_cents=agent.budget_remaining_cents,
                            min_margin=margin,
                        )

                        if not fill:
                            return None

                        # Solve the task with deadline
                        logger.info(f"{agent_id} filling at max_price=${max_price:.4f}")
                        deadline = deadline_unix if deadline_unix > 0 else None
                        work = agent.solve(task_input, deadline=deadline)

                        return {"work": work}
                    except Exception as e:
                        logger.error(f"{agent_id} handler error: {e}", exc_info=True)
                        return None

                return handler

            handler = make_handler(member.agent_id, agent, member.config)

            # Create AgentProvider
            provider = AgentProvider(
                exchange_url=self.exchange_url,
                agent_id=member.agent_id,
                callback_host="127.0.0.1",
                callback_port=member.port
            )

            # Register the handler with the provider
            provider.handle()(handler)

            # Start provider in daemon thread
            def start_provider(p: AgentProvider, mid: str):
                try:
                    logger.info(f"Starting agent {mid}")
                    p.start(register=True)
                except Exception as e:
                    logger.error(f"Agent {mid} startup error: {e}", exc_info=True)

            thread = threading.Thread(
                target=start_provider,
                args=(provider, member.agent_id),
                daemon=True,
                name=f"fleet-{member.agent_id}"
            )
            thread.start()
            self._threads.append(thread)
            logger.info(f"Launched agent {member.agent_id} on port {member.port}")

    def stop(self):
        """Signal threads to stop. (Best-effort — daemon threads die with main.)"""
        logger.info(f"Stopping fleet ({len(self._threads)} agents)")
        # Daemon threads will be killed when main thread exits

    def get_agent_stats(self) -> list[dict]:
        """Return per-agent cost/budget stats."""
        stats = []
        for agent_id, agent in self._agents.items():
            stats.append({
                "agent_id": agent_id,
                "total_cost_usd": agent.total_cost_usd,
                "budget_remaining_cents": agent.budget_remaining_cents,
                "budget_remaining_usd": agent.budget_remaining_cents / 100.0,
            })
        return stats
