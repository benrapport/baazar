#!/usr/bin/env python3
"""Start the Bazaar exchange server."""

import os
import sys
from pathlib import Path

# Add project root to path
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

import uvicorn

if __name__ == "__main__":
    print("Starting Bazaar Exchange on http://localhost:8000")
    print("Endpoints:")
    print("  POST /call         — buyer submits a task")
    print("  POST /register     — agent registers itself")
    print("  POST /submit/{id}  — agent submits work")
    print("  GET  /status       — exchange stats")
    print("  GET  /markets      — list completed market logs")
    print("  GET  /markets/{id} — full event log for a market")
    print()
    uvicorn.run(
        "exchange.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
