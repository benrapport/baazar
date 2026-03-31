#!/usr/bin/env python3
"""Start the exchange server.

Terminal 1:
    python3 sim/run_exchange.py
    python3 sim/run_exchange.py --port 9000
"""

import os
import sys
from pathlib import Path

# Add project root to path
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

import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Start the exchange server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print(f"Starting exchange on http://{args.host}:{args.port}")
    print("Endpoints:")
    print("  POST /call           — buyer submits a task")
    print("  POST /register       — agent registers itself")
    print("  POST /submit/{{id}}   — agent submits work")
    print("  GET  /feedback/{{id}} — agent polls for score")
    print("  GET  /status         — exchange stats")
    print()

    uvicorn.run(
        "exchange.server:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
