#!/usr/bin/env python3
"""Bazaar MCP server — exposes the exchange as tools for any MCP-capable AI assistant.

Tools:
    bazaar_call     — Submit a task to competing agents, get the winning result
    bazaar_status   — Check exchange health, registered agents, completed markets

Auto-starts the exchange server and seed agents if not already running.
"""

import json
import os
import signal
import subprocess
import sys
import time

# Project root (one level up from mcp/)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Load .env from project root
_env_path = os.path.join(ROOT, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

import httpx

EXCHANGE_URL = os.environ.get("BAZAAR_EXCHANGE_URL", "http://localhost:8000")
API_KEY = os.environ.get("BAZAAR_API_KEY", "demo")

# Track child processes for cleanup
_child_procs: list[subprocess.Popen] = []


def _log(msg: str):
    """Log to stderr (stdout is the MCP JSON-RPC channel)."""
    print(f"[bazaar-mcp] {msg}", file=sys.stderr, flush=True)


# ── Exchange lifecycle ───────────────────────────────────────────────

def _exchange_is_running() -> bool:
    try:
        resp = httpx.get(f"{EXCHANGE_URL}/status", timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False


def _start_exchange():
    """Start the exchange server as a subprocess."""
    _log("Starting exchange server...")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "demo", "run_exchange.py")],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _child_procs.append(proc)

    # Wait for it to be ready
    for _ in range(30):
        if _exchange_is_running():
            _log("Exchange server is ready")
            return
        time.sleep(0.5)
    _log("WARNING: Exchange server did not start within 15s")


def _start_seed_agents():
    """Start seed agents as a subprocess."""
    _log("Starting seed agents...")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "demo", "seed_agents.py")],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _child_procs.append(proc)
    # Give agents a moment to register
    time.sleep(2.0)
    _log("Seed agents started")


def _ensure_exchange():
    """Make sure exchange + agents are running."""
    if not _exchange_is_running():
        _start_exchange()
        _start_seed_agents()


def _cleanup_children(*_args):
    """Kill child processes on exit."""
    for proc in _child_procs:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    sys.exit(0)


signal.signal(signal.SIGTERM, _cleanup_children)
signal.signal(signal.SIGINT, _cleanup_children)


# ── Tool implementations ─────────────────────────────────────────────

def tool_bazaar_call(args: dict) -> dict:
    """Submit a task to the exchange and return the winning result."""
    _ensure_exchange()

    task_input = args.get("input", "").strip()
    if not task_input:
        return {"error": "input is required"}

    max_price = args.get("max_price", 0.10)
    min_quality = args.get("min_quality", 6)
    timeout = args.get("timeout", 30.0)
    top_n = args.get("top_n", 1)
    instructions = args.get("instructions", "")
    quality_criteria = args.get("quality_criteria", [])

    payload = {
        "llm": {
            "input": task_input,
            "instructions": instructions,
        },
        "exchange": {
            "max_price": max_price,
            "top_n": top_n,
            "judge": {
                "min_quality": min_quality,
                "criteria": quality_criteria,
            },
            "timeout": timeout,
        },
    }

    try:
        with httpx.Client(timeout=timeout + 10.0) as client:
            resp = client.post(
                f"{EXCHANGE_URL}/call",
                json=payload,
                headers={"Authorization": f"Bearer {API_KEY}"},
            )
    except httpx.ConnectError:
        return {"error": f"Cannot connect to exchange at {EXCHANGE_URL}"}
    except httpx.TimeoutException:
        return {"error": f"Request timed out after {timeout}s"}

    if resp.status_code == 200:
        return resp.json()
    else:
        detail = resp.json().get("detail", resp.text[:200]) if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:200]
        return {"error": f"Exchange returned {resp.status_code}: {detail}"}


def tool_bazaar_status(_args: dict) -> dict:
    """Check exchange health and stats."""
    if not _exchange_is_running():
        return {
            "running": False,
            "message": "Exchange is not running. Use bazaar_call to auto-start it.",
        }

    try:
        resp = httpx.get(f"{EXCHANGE_URL}/status", timeout=5.0)
        data = resp.json()
        data["running"] = True
        return data
    except Exception as e:
        return {"running": False, "error": str(e)}


# ── MCP JSON-RPC protocol ────────────────────────────────────────────

TOOLS = [
    {
        "name": "bazaar_call",
        "description": (
            "Submit a task to the Bazaar exchange where competing AI agents "
            "race to solve it. The exchange judges quality blindly and returns "
            "the winning result. Use this to delegate subtasks to a pool of "
            "specialized agents."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "The task for agents to complete",
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum price in USD (default 0.10)",
                    "default": 0.10,
                },
                "min_quality": {
                    "type": "integer",
                    "description": "Minimum quality score 1-10 (default 6)",
                    "default": 6,
                    "minimum": 1,
                    "maximum": 10,
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of winning results to return (default 1)",
                    "default": 1,
                    "minimum": 1,
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (default 30)",
                    "default": 30.0,
                },
                "instructions": {
                    "type": "string",
                    "description": "System instructions for agents (optional)",
                    "default": "",
                },
                "quality_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific quality criteria for judging (optional)",
                    "default": [],
                },
            },
            "required": ["input"],
        },
    },
    {
        "name": "bazaar_status",
        "description": (
            "Check if the Bazaar exchange is running, how many agents are "
            "registered, and how many markets have been completed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]

TOOL_HANDLERS = {
    "bazaar_call": tool_bazaar_call,
    "bazaar_status": tool_bazaar_status,
}


def handle_request(request: dict) -> dict:
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "bazaar", "version": "1.0.0"},
            },
        }

    if method == "notifications/initialized":
        return None  # no response for notifications

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }

        try:
            result = handler(args)
            text = json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": text}]
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {e}"}],
                    "isError": True,
                },
            }

    # Unknown method — return empty result
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {},
    }


def main():
    _log("Bazaar MCP server started")
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = handle_request(request)
                if response is not None:
                    print(json.dumps(response), flush=True)
            except json.JSONDecodeError:
                pass
            except Exception as e:
                _log(f"Error: {e}")
                print(
                    json.dumps({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32603, "message": str(e)},
                    }),
                    flush=True,
                )
    finally:
        _cleanup_children()


if __name__ == "__main__":
    main()
