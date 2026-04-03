#!/usr/bin/env python3
"""Start seller agents that compete on the exchange.

Terminal 2:
    python3 sim/run_sellers.py                           # Default fleet (5 agents)
    python3 sim/run_sellers.py --agents nano mini         # Just 2 cheap agents
    python3 sim/run_sellers.py --exchange http://localhost:9000

Each agent:
  1. Registers with the exchange
  2. Listens for task broadcasts
  3. Assesses difficulty, decides fill/pass
  4. Solves task via multi-turn tool-calling loop (Claude Code pattern)
  5. Submits {work} back to exchange
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load API key
for key_path in [
    Path.home() / ".config" / "keys" / "openai",
    ROOT / ".env",
]:
    if key_path.exists():
        if key_path.name == "openai":
            os.environ.setdefault("OPENAI_API_KEY", key_path.read_text().strip())
        else:
            for line in key_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

from agent.runtime import AgentConfig
from constants.models import Model
from sim.fleet import Fleet, FleetMember

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

# Named agent presets — pick by name on CLI
AGENT_PRESETS: dict[str, FleetMember] = {
    "nano": FleetMember(
        "nano-agent",
        AgentConfig(
            model=Model.GPT_4O_MINI,
            system_prompt="You are a fast, cheap agent. Be concise and efficient. Minimize tool use.",
            max_turns=5,
            max_tokens=512,
        ),
        port=9001,
    ),
    "mini": FleetMember(
        "mini-agent",
        AgentConfig(
            model=Model.GPT_4_1_MINI,
            system_prompt="You are a balanced agent. Good quality at reasonable cost.",
            max_turns=8,
            max_tokens=1024,
        ),
        port=9002,
    ),
    "standard": FleetMember(
        "standard-agent",
        AgentConfig(
            model=Model.GPT_4_1,
            system_prompt="You are a premium agent. Produce excellent, thorough work.",
            max_turns=10,
            max_tokens=2048,
        ),
        port=9003,
    ),
    "fast": FleetMember(
        "fast-agent",
        AgentConfig(
            model=Model.GPT_4O,
            system_prompt="You are a fast, capable agent. Optimize for speed and accuracy.",
            max_turns=8,
            max_tokens=1024,
        ),
        port=9004,
    ),
    "reasoning": FleetMember(
        "reasoning-agent",
        AgentConfig(
            model=Model.O4_MINI,
            system_prompt="You are a reasoning-focused agent. Think step by step before answering.",
            max_turns=12,
            max_tokens=2048,
        ),
        port=9005,
    ),
    "claude-haiku": FleetMember(
        "claude-haiku-agent",
        AgentConfig(
            model=Model.CLAUDE_HAIKU,
            system_prompt="You are a fast Anthropic agent. Use tools effectively.",
            max_turns=6,
            max_tokens=1024,
        ),
        port=9006,
    ),
    "claude-sonnet": FleetMember(
        "claude-sonnet-agent",
        AgentConfig(
            model=Model.CLAUDE_SONNET,
            system_prompt="You are a premium Anthropic agent. Produce the highest quality work.",
            max_turns=10,
            max_tokens=2048,
        ),
        port=9007,
    ),
}


def main():
    parser = argparse.ArgumentParser(
        description="Start seller agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available agent presets: {', '.join(AGENT_PRESETS.keys())}",
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        default=["nano", "mini", "standard", "fast", "reasoning"],
        help="Agent presets to launch (default: nano mini standard fast reasoning)",
    )
    parser.add_argument("--exchange", default="http://localhost:8000", help="Exchange URL")
    parser.add_argument("--base-port", type=int, default=None, help="Override starting port")
    args = parser.parse_args()

    # Build fleet from presets
    members = []
    for i, name in enumerate(args.agents):
        if name not in AGENT_PRESETS:
            print(f"Unknown agent preset: {name}")
            print(f"Available: {', '.join(AGENT_PRESETS.keys())}")
            sys.exit(1)
        member = AGENT_PRESETS[name]
        if args.base_port:
            member = FleetMember(member.agent_id, member.config, port=args.base_port + i)
        members.append(member)

    print(f"Launching {len(members)} seller agents:")
    for m in members:
        print(f"  {m.agent_id:25s} model={m.config.model.value:25s} port={m.port}")
    print()

    fleet = Fleet(members=members, exchange_url=args.exchange)
    fleet.launch()

    # Wait a moment for agents to register
    time.sleep(2)
    print(f"\nAll agents running. Exchange: {args.exchange}")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(10)
            stats = fleet.get_agent_stats()
            for s in stats:
                cost = s["total_cost_usd"]
                remaining = s["budget_remaining_usd"]
                if cost > 0:
                    logger.info(f"{s['agent_id']:25s} spent=${cost:.4f} remaining=${remaining:.2f}")
    except KeyboardInterrupt:
        print("\nStopping agents.")
        fleet.stop()


if __name__ == "__main__":
    main()
