#!/usr/bin/env python3
"""Start the image agent fleet — 50 agents in one process.

Run AFTER starting the exchange (run_exchange.py).
Use --agents N to run fewer agents for testing.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load .env from project root
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from agents.fleet import ImageFleet

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Start image agent fleet")
    parser.add_argument("--agents", type=int, default=None,
                        help="Max agents to register (default: all 50)")
    parser.add_argument("--port", type=int, default=9100,
                        help="Port for fleet server (default: 9100)")
    args = parser.parse_args()

    fleet = ImageFleet(port=args.port, max_agents=args.agents)
    print(f"Starting image fleet ({len(fleet.strategies)} agents on port {args.port})...")

    try:
        fleet.start()
    except KeyboardInterrupt:
        print("\nStopping fleet.")


if __name__ == "__main__":
    main()
