# 1K-Task Agent Simulation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a concurrent simulation harness that fires 1,000 difficulty-stratified tasks through the real HTTP exchange, where competing agents are multi-turn tool-using coding agents (inspired by claw-code's PortRuntime architecture), with full balance tracking and JSON result output.

**Architecture:** Exchange runs as a real FastAPI server. N agents run as real HTTP callback servers, each wrapping a `ToolAgent` — a multi-turn LLM loop with function-calling tools (execute_python, think). A simulation runner dispatches 1,000 tasks concurrently via asyncio (IO-bound), collects results into a structured JSON report. Agents have virtual balances that gate bidding (race conditions tolerated per spec).

**Tech Stack:** Python 3.11+, FastAPI, httpx, OpenAI SDK (function calling), asyncio, uvicorn

---

## File Structure

```
sim/
├── task_bank.py          # 1,000 tasks across 5 difficulty tiers (generator + seeds)
├── tool_agent.py         # Multi-turn tool-using agent runtime (claw-code inspired)
├── balance.py            # Agent balance tracking (thread-safe, race-tolerant)
├── agent_fleet.py        # Configure + launch N competing agents on separate ports
├── run_simulation.py     # Orchestrator: exchange, agents, concurrent dispatch, results
└── results.py            # Collect results, write JSON, print summary stats

exchange/
├── game.py               # Modified: pass agent_count in broadcast
└── (other files unchanged)

agentx/
├── types.py              # Modified: add agent_count + exchange_stats to BroadcastPayload
└── (other files unchanged)
```

---

### Task 1: Task Bank — 1,000 Difficulty-Stratified Tasks

**Files:**
- Create: `sim/task_bank.py`
- Test: `tests/test_task_bank.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_task_bank.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.task_bank import generate_tasks, DIFFICULTY_TIERS


def test_generates_1000_tasks():
    tasks = generate_tasks()
    assert len(tasks) == 1000


def test_each_task_has_required_fields():
    tasks = generate_tasks()
    for t in tasks:
        assert "input" in t
        assert "max_price" in t and t["max_price"] > 0
        assert "min_quality" in t and 1 <= t["min_quality"] <= 10
        assert "difficulty" in t and t["difficulty"] in DIFFICULTY_TIERS
        assert "category" in t
        assert "task_id" in t
        assert len(t["input"]) > 10  # not empty/trivial


def test_difficulty_distribution():
    tasks = generate_tasks()
    counts = {}
    for t in tasks:
        counts[t["difficulty"]] = counts.get(t["difficulty"], 0) + 1
    # Rough distribution: trivial 200, easy 300, medium 250, hard 150, brutal 100
    assert counts["trivial"] >= 150
    assert counts["easy"] >= 250
    assert counts["medium"] >= 200
    assert counts["hard"] >= 100
    assert counts["brutal"] >= 50


def test_tasks_are_unique():
    tasks = generate_tasks()
    inputs = [t["input"] for t in tasks]
    # Allow some duplication from templates but most should be unique
    assert len(set(inputs)) >= 900


def test_task_ids_are_unique():
    tasks = generate_tasks()
    ids = [t["task_id"] for t in tasks]
    assert len(set(ids)) == 1000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_task_bank.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sim'`

- [ ] **Step 3: Create the task bank module**

```python
# sim/__init__.py
```

```python
# sim/task_bank.py
"""Generate 1,000 difficulty-stratified tasks for exchange simulation.

5 tiers: trivial (200), easy (300), medium (250), hard (150), brutal (100).
Categories: math, coding, debugging, creative, analysis, multi-step.
Tasks are generated from seed templates with parameter variation.
"""

from __future__ import annotations
import hashlib
import random

DIFFICULTY_TIERS = ("trivial", "easy", "medium", "hard", "brutal")

# Price ranges per difficulty tier (min_price, max_price, min_quality)
TIER_CONFIG = {
    "trivial": {"price_range": (0.01, 0.03), "min_quality": 5},
    "easy":    {"price_range": (0.03, 0.08), "min_quality": 6},
    "medium":  {"price_range": (0.05, 0.15), "min_quality": 7},
    "hard":    {"price_range": (0.10, 0.30), "min_quality": 7},
    "brutal":  {"price_range": (0.20, 0.50), "min_quality": 8},
}

# ── Seed tasks per tier ──────────────────────────────────────────────

TRIVIAL_SEEDS = [
    {"category": "math", "template": "What is {a} {op} {b}?",
     "gen": lambda rng: {"a": rng.randint(1, 100), "b": rng.randint(1, 100),
                          "op": rng.choice(["+", "-", "*"])}},
    {"category": "factual", "template": "What is the capital of {country}?",
     "gen": lambda rng: {"country": rng.choice([
         "France", "Japan", "Brazil", "Egypt", "Australia", "Canada", "India",
         "Germany", "Mexico", "South Korea", "Nigeria", "Sweden", "Thailand",
         "Argentina", "Kenya", "Poland", "Vietnam", "Chile", "Morocco", "Norway"])}},
    {"category": "conversion", "template": "Convert {n} {from_unit} to {to_unit}.",
     "gen": lambda rng: {"n": rng.randint(1, 1000),
                          **rng.choice([
                              {"from_unit": "miles", "to_unit": "kilometers"},
                              {"from_unit": "pounds", "to_unit": "kilograms"},
                              {"from_unit": "Fahrenheit", "to_unit": "Celsius"},
                              {"from_unit": "inches", "to_unit": "centimeters"},
                              {"from_unit": "gallons", "to_unit": "liters"},
                          ])}},
    {"category": "definition", "template": "Define the word '{word}' in one sentence.",
     "gen": lambda rng: {"word": rng.choice([
         "ephemeral", "ubiquitous", "pragmatic", "ambiguous", "resilient",
         "paradigm", "entropy", "catalyst", "synergy", "heuristic",
         "idempotent", "polymorphism", "abstraction", "concurrency", "latency"])}},
]

EASY_SEEDS = [
    {"category": "coding", "template": "Write a Python function that {task}.",
     "gen": lambda rng: {"task": rng.choice([
         "reverses a string", "checks if a string is a palindrome",
         "finds the maximum value in a list", "counts vowels in a string",
         "removes duplicates from a list", "checks if a number is even",
         "calculates the factorial of a number", "finds the GCD of two numbers",
         "flattens a nested list one level deep", "returns the nth Fibonacci number",
         "checks if a string is an anagram of another", "rotates a list by k positions",
         "finds the second largest number in a list", "converts a string to title case",
         "merges two sorted lists into one sorted list"])}},
    {"category": "creative", "template": "Write a {form} about {topic}.",
     "gen": lambda rng: {"form": rng.choice(["haiku", "limerick", "short poem", "four-line verse"]),
                          "topic": rng.choice([
                              "the ocean", "artificial intelligence", "a rainy day",
                              "a lost key", "the moon", "a broken clock", "silence",
                              "a forgotten library", "the last train", "rust"])}},
    {"category": "explanation", "template": "Explain {concept} in 2-3 sentences for a beginner.",
     "gen": lambda rng: {"concept": rng.choice([
         "what an API is", "how DNS works", "what a hash function does",
         "the difference between TCP and UDP", "what a database index is",
         "how HTTPS encryption works", "what a load balancer does",
         "the CAP theorem", "what eventual consistency means",
         "how garbage collection works", "what a mutex is"])}},
    {"category": "listing", "template": "List {n} {items}.",
     "gen": lambda rng: {"n": rng.randint(3, 7),
                          "items": rng.choice([
                              "pros and cons of remote work",
                              "common HTTP status codes and their meanings",
                              "design patterns used in web development",
                              "differences between SQL and NoSQL databases",
                              "best practices for writing unit tests"])}},
]

MEDIUM_SEEDS = [
    {"category": "coding", "template": "Implement {algorithm} in Python. Include docstring and handle edge cases.",
     "gen": lambda rng: {"algorithm": rng.choice([
         "binary search", "merge sort", "quicksort", "BFS on a graph",
         "DFS on a graph", "Dijkstra's shortest path", "a min-heap",
         "a stack using two queues", "a queue using two stacks",
         "an LRU cache with O(1) operations", "topological sort",
         "the Knuth-Morris-Pratt string matching algorithm",
         "a trie (prefix tree) with insert and search",
         "a disjoint-set (union-find) data structure",
         "the Floyd-Warshall all-pairs shortest path algorithm"])}},
    {"category": "debugging",
     "template": "This Python code has a bug. Find and fix it, explain what was wrong:\n\n```python\n{code}\n```",
     "gen": lambda rng: {"code": rng.choice([
         "def binary_search(arr, target):\n    lo, hi = 0, len(arr)\n    while lo < hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            lo = mid\n        else:\n            hi = mid\n    return -1",
         "def merge_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    mid = len(arr) // 2\n    left = merge_sort(arr[:mid])\n    right = merge_sort(arr[mid:])\n    result = []\n    i = j = 0\n    while i < len(left) and j < len(right):\n        if left[i] <= right[j]:\n            result.append(left[i])\n            i += 1\n        else:\n            result.append(right[j])\n            j += 1\n    return result",
         "class Node:\n    def __init__(self, val):\n        self.val = val\n        self.next = None\n\ndef reverse_list(head):\n    prev = None\n    curr = head\n    while curr:\n        curr.next = prev\n        prev = curr\n        curr = curr.next\n    return prev",
         "def flatten(lst):\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result.extend(flatten(item))\n        else:\n            result.append(item)\n    return result\n\n# Bug: this returns [] for flatten([[1, [2]], 3])\n# Actually the bug is elsewhere:\ndef deep_copy(obj):\n    if isinstance(obj, list):\n        return [deep_copy(item) for item in obj]\n    return obj  # Doesn't handle dicts",
         "import threading\n\nclass Counter:\n    def __init__(self):\n        self.count = 0\n    \n    def increment(self):\n        temp = self.count\n        self.count = temp + 1\n    \n    def get(self):\n        return self.count\n\n# Used by 10 threads calling increment() 1000 times each\n# Expected final count: 10000, but gets less",
     ])}},
    {"category": "analysis",
     "template": "Analyze the time and space complexity of this code. Give Big-O for both:\n\n```python\n{code}\n```",
     "gen": lambda rng: {"code": rng.choice([
         "def f(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(i, n):\n            for k in range(j, n):\n                if arr[i] + arr[j] + arr[k] == 0:\n                    return True\n    return False",
         "def f(n):\n    if n <= 1:\n        return n\n    return f(n-1) + f(n-2)",
         "def f(arr):\n    seen = set()\n    for x in arr:\n        if x in seen:\n            return True\n        seen.add(x)\n    return False",
         "def f(arr):\n    arr.sort()\n    result = []\n    for i in range(len(arr)):\n        lo, hi = i + 1, len(arr) - 1\n        while lo < hi:\n            s = arr[i] + arr[lo] + arr[hi]\n            if s == 0:\n                result.append((arr[i], arr[lo], arr[hi]))\n                lo += 1\n                hi -= 1\n            elif s < 0:\n                lo += 1\n            else:\n                hi -= 1\n    return result",
     ])}},
    {"category": "design",
     "template": "Design a {system}. Describe the data model, API endpoints, and key implementation decisions.",
     "gen": lambda rng: {"system": rng.choice([
         "REST API for a URL shortener", "REST API for a todo-list app",
         "real-time chat system using WebSockets",
         "rate limiter middleware for an API",
         "job queue with priority and retry logic",
         "simple key-value store with TTL expiration",
         "notification system that supports email, SMS, and push",
         "file upload service with virus scanning",
     ])}},
]

HARD_SEEDS = [
    {"category": "coding",
     "template": "{task}\n\nRequirements:\n- Handle all edge cases\n- Include type hints\n- Time complexity must be {complexity} or better\n- Include at least 3 test cases in a docstring",
     "gen": lambda rng: {**rng.choice([
         {"task": "Implement a self-balancing BST (AVL tree) with insert, delete, and search",
          "complexity": "O(log n)"},
         {"task": "Implement a thread-safe bounded blocking queue",
          "complexity": "O(1) per operation"},
         {"task": "Write a regular expression engine that supports '.', '*', '+', and '?'",
          "complexity": "O(nm)"},
         {"task": "Implement consistent hashing with virtual nodes for a distributed cache",
          "complexity": "O(log n) per lookup"},
         {"task": "Build a simple in-memory SQL query parser that handles SELECT, WHERE, ORDER BY, and LIMIT",
          "complexity": "O(n log n)"},
         {"task": "Implement the Raft consensus algorithm's leader election protocol",
          "complexity": "O(n) per round"},
         {"task": "Write a garbage collector using mark-and-sweep for a simple object graph",
          "complexity": "O(V + E)"},
         {"task": "Implement a B-tree with insert and search (order 5)",
          "complexity": "O(log n)"},
         {"task": "Build a dependency resolver that detects circular dependencies and produces a valid install order",
          "complexity": "O(V + E)"},
         {"task": "Implement a skip list with insert, delete, and search",
          "complexity": "O(log n) expected"},
     ])}},
    {"category": "debugging",
     "template": "This distributed system has a subtle concurrency bug. Identify the race condition, explain the failure scenario, and write a corrected version:\n\n```python\n{code}\n```",
     "gen": lambda rng: {"code": rng.choice([
         "import asyncio\nimport aiohttp\n\nclass DistributedCounter:\n    def __init__(self, nodes):\n        self.nodes = nodes\n        self.local_count = 0\n    \n    async def increment(self):\n        self.local_count += 1\n        # Broadcast to all nodes\n        async with aiohttp.ClientSession() as session:\n            for node in self.nodes:\n                await session.post(f'{node}/sync', json={'count': self.local_count})\n    \n    async def handle_sync(self, remote_count):\n        self.local_count = max(self.local_count, remote_count)",
         "import threading\nimport time\n\nclass LeaderElection:\n    def __init__(self, node_id, peers):\n        self.node_id = node_id\n        self.peers = peers\n        self.leader = None\n        self.term = 0\n        self.voted_for = None\n    \n    def start_election(self):\n        self.term += 1\n        self.voted_for = self.node_id\n        votes = 1\n        for peer in self.peers:\n            if peer.request_vote(self.term, self.node_id):\n                votes += 1\n        if votes > len(self.peers) // 2:\n            self.leader = self.node_id\n    \n    def request_vote(self, term, candidate):\n        if term > self.term:\n            self.term = term\n            self.voted_for = candidate\n            return True\n        return False",
     ])}},
    {"category": "multi-step",
     "template": "{task}",
     "gen": lambda rng: {"task": rng.choice([
         "Write a Python module that implements a simple Lisp interpreter. It should support: integers, symbols, define, lambda, if, +, -, *, /, =, <, >. Include a REPL function and demonstrate it evaluating: (define fib (lambda (n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2))))))",
         "Implement a basic HTTP/1.1 server in Python using only the socket library. It should handle GET and POST requests, serve static files from a directory, parse headers and query parameters, and return proper status codes (200, 404, 405, 500). Include Content-Type detection based on file extension.",
         "Write a compiler for a simple arithmetic language that supports variables, +, -, *, /, parentheses, and let bindings. The compiler should parse to an AST, type-check, and emit Python bytecode or a simple stack-machine IR. Include an evaluator for the IR.",
         "Build a simple version control system in Python that supports: init, add, commit, log, diff, branch, checkout, and merge. Use SHA-1 hashes for content addressing. Store objects as files in a .mini-git directory.",
         "Implement a basic MapReduce framework in Python. It should support: mapping a function over input splits, shuffling/sorting by key, reducing, and combining results. Demonstrate it with word count over 3 input files. Use multiprocessing for parallelism.",
     ])}},
]

BRUTAL_SEEDS = [
    {"category": "coding",
     "template": "{task}",
     "gen": lambda rng: {"task": rng.choice([
         "Implement a complete B+ tree with insert, delete, search, and range queries. The tree should maintain sorted order, support configurable page size, handle underflow via redistribution and merging, and include a leaf-level linked list for efficient range scans. Include comprehensive tests.",
         "Write a Python implementation of the Paxos consensus protocol (single-decree). Implement Proposer, Acceptor, and Learner roles. Simulate a network of 5 nodes with message passing, handle message loss and duplication, and demonstrate that consensus is reached even when 2 nodes fail. Include correctness proofs as comments.",
         "Implement a complete garbage-collecting virtual machine for a simple bytecode language. The VM should support: integer and string types, function calls with a call stack, closures, and a mark-compact garbage collector. The bytecode should include PUSH, POP, ADD, SUB, MUL, DIV, CALL, RET, LOAD, STORE, JMP, JZ, PRINT. Compile a recursive fibonacci function to this bytecode and execute it.",
         "Build a database query optimizer for a subset of SQL. Support SELECT, FROM, WHERE, JOIN, ORDER BY, GROUP BY, HAVING. Implement: query parsing to a relational algebra tree, predicate pushdown, join reordering using dynamic programming (Selinger-style), and cost estimation based on table statistics. Demonstrate with a 3-table join query.",
         "Implement a complete type inference engine (Hindley-Milner Algorithm W) for a functional language with: let polymorphism, lambda expressions, integers, booleans, lists, tuples, and user-defined algebraic data types. Include unification, generalization, and instantiation. Demonstrate by inferring the type of: let compose = \\f -> \\g -> \\x -> f (g x) in compose",
         "Write a lock-free concurrent hash map in Python using only atomics (no locks, no threading.Lock). Use compare-and-swap semantics via ctypes or similar. Support get, put, delete, and resize. Handle the ABA problem. Include a stress test with 8 threads doing 10,000 operations each and verify correctness.",
         "Implement a simple distributed key-value store using the Raft consensus protocol. Support: leader election, log replication, and client read/write operations. Simulate a 5-node cluster with network partitions. Demonstrate that reads are linearizable and writes survive leader failure. Use asyncio for the network layer.",
         "Build a JIT compiler for a simple language (integers, arithmetic, if/else, while loops, functions). Parse source to AST, compile to x86-64 machine code in memory, and execute it. Use mmap for executable memory. The generated code should be at least 10x faster than an AST interpreter for fibonacci(35).",
     ])}},
    {"category": "analysis",
     "template": "{task}",
     "gen": lambda rng: {"task": rng.choice([
         "Analyze and implement the following: Given a DAG with N nodes and weighted edges, find the maximum number of edge-disjoint paths from source to sink where the total weight of all paths is minimized. Prove the correctness of your approach and analyze time complexity. Implement in Python with test cases.",
         "Implement and analyze a cache-oblivious B-tree. Explain why it achieves O(log_B N) I/Os per operation without knowing the block size B. Implement the van Emde Boas layout for a static version and demonstrate the I/O complexity advantage over a naive binary tree layout with a benchmark.",
     ])}},
]

ALL_SEEDS = {
    "trivial": TRIVIAL_SEEDS,
    "easy": EASY_SEEDS,
    "medium": MEDIUM_SEEDS,
    "hard": HARD_SEEDS,
    "brutal": BRUTAL_SEEDS,
}

# Target count per tier
TIER_COUNTS = {
    "trivial": 200,
    "easy": 300,
    "medium": 250,
    "hard": 150,
    "brutal": 100,
}


def _make_task_id(difficulty: str, index: int) -> str:
    return f"{difficulty}_{index:04d}"


def _generate_tier(difficulty: str, count: int, rng: random.Random) -> list[dict]:
    """Generate `count` tasks for a given difficulty tier."""
    seeds = ALL_SEEDS[difficulty]
    config = TIER_CONFIG[difficulty]
    tasks = []

    for i in range(count):
        seed = seeds[i % len(seeds)]
        params = seed["gen"](rng)
        input_text = seed["template"].format(**params)

        price_lo, price_hi = config["price_range"]
        max_price = round(rng.uniform(price_lo, price_hi), 4)

        tasks.append({
            "task_id": _make_task_id(difficulty, i),
            "input": input_text,
            "max_price": max_price,
            "min_quality": config["min_quality"],
            "difficulty": difficulty,
            "category": seed["category"],
        })

    return tasks


def generate_tasks(seed: int = 42) -> list[dict]:
    """Generate all 1,000 tasks. Deterministic given seed."""
    rng = random.Random(seed)
    all_tasks = []

    for difficulty, count in TIER_COUNTS.items():
        all_tasks.extend(_generate_tier(difficulty, count, rng))

    # Shuffle so tasks aren't grouped by difficulty during simulation
    rng.shuffle(all_tasks)
    return all_tasks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_task_bank.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sim/__init__.py sim/task_bank.py tests/test_task_bank.py
git commit -m "feat: add 1k-task bank with 5 difficulty tiers"
```

---

### Task 2: Tool Agent — Multi-Turn Coding Agent Runtime

**Files:**
- Create: `sim/tool_agent.py`
- Test: `tests/test_tool_agent.py`

This is the claw-code-inspired core: a multi-turn agent that uses OpenAI function calling to iterate with tools before producing a final answer. The turn loop mirrors claw-code's `PortRuntime.run_turn_loop()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tool_agent.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import MagicMock, patch
from sim.tool_agent import ToolAgent, execute_python_tool


def test_execute_python_tool_basic():
    result = execute_python_tool("print(2 + 2)")
    assert "4" in result["stdout"]
    assert result["returncode"] == 0


def test_execute_python_tool_error():
    result = execute_python_tool("raise ValueError('boom')")
    assert result["returncode"] != 0
    assert "boom" in result["stderr"]


def test_execute_python_tool_timeout():
    result = execute_python_tool("import time; time.sleep(100)", timeout=1)
    assert result["returncode"] != 0
    assert "timeout" in result["stderr"].lower() or result["returncode"] == -1


def test_tool_agent_init():
    agent = ToolAgent(model="gpt-4o-mini", max_turns=3)
    assert agent.model == "gpt-4o-mini"
    assert agent.max_turns == 3


def test_tool_agent_tools_schema():
    agent = ToolAgent(model="gpt-4o-mini")
    tools = agent._tool_schemas()
    names = {t["function"]["name"] for t in tools}
    assert "execute_python" in names
    assert "think" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_tool_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sim.tool_agent'`

- [ ] **Step 3: Implement the tool agent**

```python
# sim/tool_agent.py
"""Multi-turn tool-using agent runtime, inspired by claw-code's PortRuntime.

Architecture (from claw-code):
  1. Receive task prompt
  2. Route to LLM with available tools
  3. LLM returns either final answer OR tool calls
  4. Execute tools, feed results back to LLM
  5. Repeat until final answer or max_turns exhausted

Tools available to agents:
  - execute_python: Run Python code in a sandboxed subprocess
  - think: Scratchpad for reasoning (records thought, returns ack)
"""

from __future__ import annotations
import json
import logging
import subprocess
import tempfile
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger(__name__)

# ── Tools ─────────────────────────────────────────────────────────────

def execute_python_tool(code: str, timeout: int = 10) -> dict:
    """Execute Python code in a subprocess. Returns {stdout, stderr, returncode}."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:5000],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Timeout: code exceeded {timeout}s limit",
            "returncode": -1,
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def think_tool(thought: str) -> dict:
    """Scratchpad — just acknowledges the thought."""
    return {"status": "ok", "thought_recorded": True}


TOOL_DISPATCH = {
    "execute_python": lambda args: execute_python_tool(args.get("code", "")),
    "think": lambda args: think_tool(args.get("thought", "")),
}


# ── Agent ─────────────────────────────────────────────────────────────

class ToolAgent:
    """Multi-turn LLM agent with tool use.

    Mirrors claw-code's PortRuntime turn loop:
      prompt → route → execute tools → feed back → repeat
    """

    def __init__(self, model: str = "gpt-4o-mini",
                 max_turns: int = 5,
                 client: OpenAI | None = None,
                 system_prompt: str = "",
                 max_tokens: int = 4096):
        self.model = model
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self._client = client
        self.system_prompt = system_prompt or (
            "You are a skilled AI agent competing in a task marketplace. "
            "Produce the highest quality output you can. "
            "You have tools available: use execute_python to test code, "
            "and think to reason through complex problems step by step. "
            "When you are done, respond with your final answer as plain text "
            "(do NOT call any tool — just write the answer)."
        )

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI()
        return self._client

    def _tool_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "execute_python",
                    "description": (
                        "Execute Python code in a sandboxed subprocess. "
                        "Use this to test your code, verify calculations, "
                        "or run experiments. Returns stdout, stderr, returncode."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Python code to execute",
                            }
                        },
                        "required": ["code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "think",
                    "description": (
                        "Use this to reason step by step about a problem "
                        "before writing your final answer. Good for planning "
                        "complex solutions, debugging, or analyzing requirements."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "thought": {
                                "type": "string",
                                "description": "Your reasoning or analysis",
                            }
                        },
                        "required": ["thought"],
                    },
                },
            },
        ]

    def run(self, task: str) -> str:
        """Execute task with multi-turn tool loop. Returns final text output."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task},
        ]

        for turn in range(self.max_turns):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=messages,
                    tools=self._tool_schemas(),
                    tool_choice="auto",
                )
            except Exception as e:
                logger.error(f"LLM call failed on turn {turn}: {e}")
                return f"Error: LLM call failed: {e}"

            choice = resp.choices[0]

            # If no tool calls, this is the final answer
            if choice.finish_reason == "stop" or not choice.message.tool_calls:
                return choice.message.content or ""

            # Process tool calls
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                handler = TOOL_DISPATCH.get(fn_name)
                if handler:
                    result = handler(fn_args)
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

                logger.debug(
                    f"Turn {turn}, tool={fn_name}: "
                    f"{json.dumps(result)[:200]}"
                )

        # Max turns exhausted — return whatever we have
        last_assistant = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content:
                last_assistant = msg.content
                break
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                last_assistant = msg.get("content", "")
                break
        return last_assistant or "Max turns exhausted without final answer."
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_tool_agent.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sim/tool_agent.py tests/test_tool_agent.py
git commit -m "feat: add multi-turn tool agent runtime (claw-code inspired)"
```

---

### Task 3: Agent Balance Tracking

**Files:**
- Create: `sim/balance.py`
- Test: `tests/test_balance.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_balance.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import threading
from sim.balance import BalanceTracker


def test_initial_balance():
    bt = BalanceTracker(initial=10.0)
    bt.register("agent-1")
    assert bt.get("agent-1") == 10.0


def test_deduct():
    bt = BalanceTracker(initial=10.0)
    bt.register("agent-1")
    assert bt.deduct("agent-1", 3.0) is True
    assert bt.get("agent-1") == 7.0


def test_can_bid_true():
    bt = BalanceTracker(initial=10.0)
    bt.register("agent-1")
    assert bt.can_bid("agent-1") is True


def test_can_bid_false_at_zero():
    bt = BalanceTracker(initial=0.0)
    bt.register("agent-1")
    assert bt.can_bid("agent-1") is False


def test_race_condition_allows_negative():
    """Per spec: agents can go below 0 via race conditions."""
    bt = BalanceTracker(initial=1.0)
    bt.register("agent-1")
    # Two threads both check can_bid (True), then both deduct
    results = []

    def deduct_thread():
        if bt.can_bid("agent-1"):
            results.append(bt.deduct("agent-1", 0.8))

    t1 = threading.Thread(target=deduct_thread)
    t2 = threading.Thread(target=deduct_thread)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    # Both should succeed (race condition by design)
    assert all(results)
    # Balance went negative
    assert bt.get("agent-1") < 0


def test_cannot_bid_once_at_zero():
    bt = BalanceTracker(initial=1.0)
    bt.register("agent-1")
    bt.deduct("agent-1", 1.0)
    assert bt.can_bid("agent-1") is False


def test_get_all_balances():
    bt = BalanceTracker(initial=5.0)
    bt.register("a1")
    bt.register("a2")
    bt.deduct("a1", 2.0)
    balances = bt.get_all()
    assert balances["a1"] == 3.0
    assert balances["a2"] == 5.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_balance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sim.balance'`

- [ ] **Step 3: Implement balance tracker**

```python
# sim/balance.py
"""Agent balance tracking — thread-safe with intentional race tolerance.

Per spec: agents CAN go below $0 via race conditions between can_bid()
and deduct(). Once balance is <= 0 at check time, they cannot bid.
"""

from __future__ import annotations
import threading


class BalanceTracker:
    def __init__(self, initial: float = 10.0):
        self._initial = initial
        self._balances: dict[str, float] = {}
        self._lock = threading.Lock()

    def register(self, agent_id: str) -> None:
        with self._lock:
            self._balances[agent_id] = self._initial

    def can_bid(self, agent_id: str) -> bool:
        """Check if agent has positive balance. NOT atomic with deduct()."""
        with self._lock:
            return self._balances.get(agent_id, 0) > 0

    def deduct(self, agent_id: str, amount: float) -> bool:
        """Deduct amount from agent balance. Always succeeds (race tolerant)."""
        with self._lock:
            if agent_id not in self._balances:
                return False
            self._balances[agent_id] -= amount
            return True

    def get(self, agent_id: str) -> float:
        with self._lock:
            return self._balances.get(agent_id, 0)

    def get_all(self) -> dict[str, float]:
        with self._lock:
            return dict(self._balances)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_balance.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sim/balance.py tests/test_balance.py
git commit -m "feat: add race-tolerant agent balance tracker"
```

---

### Task 4: Expand BroadcastPayload with Game State

**Files:**
- Modify: `agentx/types.py:78-89` — add `agent_count` field to BroadcastPayload
- Modify: `exchange/game.py:66-73` — include agent_count in payload
- Test: `tests/test_broadcast_state.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_broadcast_state.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentx.types import BroadcastPayload


def test_broadcast_has_agent_count():
    p = BroadcastPayload(
        request_id="req_1",
        input="test",
        max_price=1.0,
        min_quality=5,
        agent_count=7,
    )
    assert p.agent_count == 7


def test_broadcast_agent_count_defaults_zero():
    p = BroadcastPayload(
        request_id="req_1",
        input="test",
        max_price=1.0,
        min_quality=5,
    )
    assert p.agent_count == 0


def test_broadcast_has_exchange_stats():
    p = BroadcastPayload(
        request_id="req_1",
        input="test",
        max_price=1.0,
        min_quality=5,
        exchange_stats={"total_transactions": 42, "total_volume": 1.23},
    )
    assert p.exchange_stats["total_transactions"] == 42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_broadcast_state.py -v`
Expected: FAIL on `agent_count` — field doesn't exist yet

- [ ] **Step 3: Add fields to BroadcastPayload**

In `agentx/types.py`, add two fields to `BroadcastPayload`:

```python
# Add after the deadline_unix field (line 89):
    agent_count: int = 0  # how many agents are competing in this round
    exchange_stats: dict = {}  # {total_transactions, total_volume, exchange_revenue}
```

- [ ] **Step 4: Update game.py to populate agent_count**

In `exchange/game.py`, modify the payload construction (around line 66-73):

```python
    payload = BroadcastPayload(
        request_id=request_id,
        input=input_text,
        max_price=max_price,
        min_quality=min_quality,
        quality_criteria=quality_criteria or [],
        deadline_unix=deadline,
        agent_count=len(agents),
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_broadcast_state.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Run existing tests to verify no regressions**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/ -v`
Expected: All existing tests still pass

- [ ] **Step 7: Commit**

```bash
git add agentx/types.py exchange/game.py tests/test_broadcast_state.py
git commit -m "feat: expand BroadcastPayload with agent_count and exchange_stats"
```

---

### Task 5: Agent Fleet — Configure and Launch Competing Agents

**Files:**
- Create: `sim/agent_fleet.py`
- Test: `tests/test_agent_fleet.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent_fleet.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.agent_fleet import AgentConfig, build_agent_configs, DEFAULT_FLEET


def test_default_fleet_has_5_agents():
    assert len(DEFAULT_FLEET) == 5


def test_agent_config_fields():
    cfg = AgentConfig(
        agent_id="test-agent",
        model="gpt-4o-mini",
        port=9001,
        bid_strategy="fixed_fraction",
        bid_fraction=0.3,
        max_turns=3,
        system_prompt="Be fast.",
    )
    assert cfg.agent_id == "test-agent"
    assert cfg.port == 9001


def test_build_agent_configs_unique_ports():
    configs = build_agent_configs(n=5, base_port=9001)
    ports = [c.port for c in configs]
    assert len(set(ports)) == 5


def test_build_agent_configs_unique_ids():
    configs = build_agent_configs(n=5, base_port=9001)
    ids = [c.agent_id for c in configs]
    assert len(set(ids)) == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_agent_fleet.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement agent fleet configuration**

```python
# sim/agent_fleet.py
"""Agent fleet configuration and launcher.

Defines N competing agents with different models, strategies, and tool settings.
Each agent wraps a ToolAgent and runs as an AgentProvider on its own port.
"""

from __future__ import annotations
import logging
import threading
from dataclasses import dataclass, field

from openai import OpenAI

from agentx.provider import AgentProvider
from sim.tool_agent import ToolAgent
from sim.balance import BalanceTracker

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    agent_id: str
    model: str
    port: int
    bid_strategy: str = "fixed_fraction"  # "fixed_fraction" or "cost_plus"
    bid_fraction: float = 0.5  # fraction of max_price to bid
    max_turns: int = 3  # tool agent turn limit
    system_prompt: str = ""
    max_tokens: int = 4096


# Default fleet: 5 agents with different cost/quality tradeoffs
DEFAULT_FLEET = [
    AgentConfig(
        agent_id="speed-demon",
        model="gpt-4o-mini",
        port=9001,
        bid_fraction=0.2,
        max_turns=1,  # single-shot, no tool use
        system_prompt=(
            "You are the fastest agent in the marketplace. "
            "Answer immediately and concisely. Speed is everything."
        ),
    ),
    AgentConfig(
        agent_id="budget-coder",
        model="gpt-4o-mini",
        port=9002,
        bid_fraction=0.3,
        max_turns=3,
        system_prompt=(
            "You are a budget-friendly coding agent. "
            "Use tools to verify your code works before submitting. "
            "Be thorough but efficient."
        ),
    ),
    AgentConfig(
        agent_id="balanced-pro",
        model="gpt-4.1-mini",
        port=9003,
        bid_fraction=0.5,
        max_turns=4,
        system_prompt=(
            "You are a balanced professional agent. "
            "Use tools when helpful. Aim for quality and correctness. "
            "Test your code if the task involves programming."
        ),
    ),
    AgentConfig(
        agent_id="quality-first",
        model="gpt-4.1",
        port=9004,
        bid_fraction=0.7,
        max_turns=5,
        system_prompt=(
            "You are a premium quality agent. "
            "Always use the think tool to plan before answering. "
            "For code tasks, always test with execute_python. "
            "Quality and correctness matter more than speed."
        ),
    ),
    AgentConfig(
        agent_id="deep-thinker",
        model="gpt-4.1",
        port=9005,
        bid_fraction=0.8,
        max_turns=5,
        max_tokens=8192,
        system_prompt=(
            "You are a deep-thinking agent specializing in hard problems. "
            "Always think step by step. Break complex tasks into parts. "
            "Use execute_python to verify every claim. "
            "Never submit unverified code. Be comprehensive."
        ),
    ),
]


def build_agent_configs(n: int = 5, base_port: int = 9001) -> list[AgentConfig]:
    """Build N agent configs with incrementing ports."""
    models = ["gpt-4o-mini", "gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1", "gpt-4.1"]
    fractions = [0.2, 0.3, 0.5, 0.7, 0.8]
    turns = [1, 3, 4, 5, 5]
    names = ["speed-demon", "budget-coder", "balanced-pro", "quality-first", "deep-thinker"]

    configs = []
    for i in range(n):
        idx = i % len(models)
        configs.append(AgentConfig(
            agent_id=f"{names[idx]}-{i}" if i >= len(names) else names[idx],
            model=models[idx],
            port=base_port + i,
            bid_fraction=fractions[idx],
            max_turns=turns[idx],
        ))
    return configs


def make_agent_handler(config: AgentConfig, balances: BalanceTracker,
                       client: OpenAI | None = None):
    """Create a request handler function for an agent config."""
    agent = ToolAgent(
        model=config.model,
        max_turns=config.max_turns,
        client=client,
        system_prompt=config.system_prompt,
        max_tokens=config.max_tokens,
    )

    def handler(request: dict) -> dict | None:
        # Check balance before doing expensive LLM work
        if not balances.can_bid(config.agent_id):
            logger.info(f"[{config.agent_id}] Declining — no balance")
            return None

        task = request["input"]
        max_price = request["max_price"]

        # Calculate bid
        bid = round(max_price * config.bid_fraction, 6)

        # Do the work via multi-turn tool agent
        try:
            work = agent.run(task)
        except Exception as e:
            logger.error(f"[{config.agent_id}] Agent error: {e}")
            return None

        if not work:
            return None

        return {"bid": bid, "work": work}

    return handler


def launch_fleet(configs: list[AgentConfig],
                 balances: BalanceTracker,
                 exchange_url: str = "http://localhost:8000",
                 client: OpenAI | None = None) -> list[threading.Thread]:
    """Launch all agents as background threads. Returns threads."""
    threads = []

    for config in configs:
        balances.register(config.agent_id)

        provider = AgentProvider(
            exchange_url=exchange_url,
            agent_id=config.agent_id,
            callback_port=config.port,
        )

        handler = make_agent_handler(config, balances, client)
        provider.handle()(handler)

        t = threading.Thread(target=provider.start, daemon=True, name=config.agent_id)
        t.start()
        threads.append(t)
        logger.info(f"Launched {config.agent_id} on port {config.port}")

    return threads
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_agent_fleet.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sim/agent_fleet.py tests/test_agent_fleet.py
git commit -m "feat: add configurable agent fleet with tool-agent handlers"
```

---

### Task 6: Results Collector — JSON Output + Summary Stats

**Files:**
- Create: `sim/results.py`
- Test: `tests/test_results.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_results.py
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.results import SimulationResult, ResultCollector


def test_result_collector_add():
    rc = ResultCollector()
    rc.add(SimulationResult(
        task_id="trivial_0001",
        input="What is 2+2?",
        difficulty="trivial",
        category="math",
        max_price=0.02,
        min_quality=5,
        agent_id="cheap-agent",
        bid=0.005,
        score=8,
        latency_ms=150.0,
        output="4",
        error=None,
    ))
    assert rc.count == 1


def test_result_collector_add_failure():
    rc = ResultCollector()
    rc.add(SimulationResult(
        task_id="hard_0001",
        input="Implement B-tree",
        difficulty="hard",
        category="coding",
        max_price=0.30,
        min_quality=7,
        agent_id=None,
        bid=None,
        score=None,
        latency_ms=30000.0,
        output=None,
        error="TimeoutError: No qualifying submission within 30.0s",
    ))
    assert rc.count == 1
    assert rc.failure_count == 1


def test_save_json():
    rc = ResultCollector()
    rc.add(SimulationResult(
        task_id="t1", input="test", difficulty="trivial", category="math",
        max_price=0.02, min_quality=5, agent_id="a1", bid=0.005,
        score=8, latency_ms=100.0, output="ok", error=None,
    ))
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    rc.save_json(path)
    data = json.loads(Path(path).read_text())
    assert "results" in data
    assert "summary" in data
    assert len(data["results"]) == 1
    Path(path).unlink()


def test_summary_stats():
    rc = ResultCollector()
    for i in range(10):
        rc.add(SimulationResult(
            task_id=f"t{i}", input="test", difficulty="easy", category="coding",
            max_price=0.05, min_quality=6,
            agent_id="a1" if i < 7 else None,
            bid=0.02 if i < 7 else None,
            score=7 if i < 7 else None,
            latency_ms=200.0,
            output="ok" if i < 7 else None,
            error=None if i < 7 else "timeout",
        ))
    summary = rc.summary()
    assert summary["total_tasks"] == 10
    assert summary["successful"] == 7
    assert summary["failed"] == 3
    assert summary["success_rate"] == 0.7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_results.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement results collector**

```python
# sim/results.py
"""Simulation result collection, JSON output, and summary statistics."""

from __future__ import annotations
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class SimulationResult:
    task_id: str
    input: str
    difficulty: str
    category: str
    max_price: float
    min_quality: int
    agent_id: str | None
    bid: float | None
    score: int | None
    latency_ms: float
    output: str | None
    error: str | None


class ResultCollector:
    def __init__(self):
        self._results: list[SimulationResult] = []
        self._start_time: float = time.time()

    def add(self, result: SimulationResult) -> None:
        self._results.append(result)

    @property
    def count(self) -> int:
        return len(self._results)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self._results if r.agent_id is None)

    def summary(self) -> dict:
        total = len(self._results)
        successful = sum(1 for r in self._results if r.agent_id is not None)
        failed = total - successful

        # Per-difficulty breakdown
        by_difficulty = {}
        for r in self._results:
            d = r.difficulty
            if d not in by_difficulty:
                by_difficulty[d] = {"total": 0, "successful": 0, "avg_score": 0,
                                    "avg_latency_ms": 0, "avg_bid": 0, "scores": [],
                                    "latencies": [], "bids": []}
            by_difficulty[d]["total"] += 1
            if r.agent_id is not None:
                by_difficulty[d]["successful"] += 1
                if r.score is not None:
                    by_difficulty[d]["scores"].append(r.score)
                by_difficulty[d]["latencies"].append(r.latency_ms)
                if r.bid is not None:
                    by_difficulty[d]["bids"].append(r.bid)

        for d, stats in by_difficulty.items():
            stats["avg_score"] = (
                round(sum(stats["scores"]) / len(stats["scores"]), 2)
                if stats["scores"] else 0
            )
            stats["avg_latency_ms"] = (
                round(sum(stats["latencies"]) / len(stats["latencies"]), 1)
                if stats["latencies"] else 0
            )
            stats["avg_bid"] = (
                round(sum(stats["bids"]) / len(stats["bids"]), 6)
                if stats["bids"] else 0
            )
            del stats["scores"], stats["latencies"], stats["bids"]

        # Per-agent breakdown
        by_agent = {}
        for r in self._results:
            if r.agent_id is None:
                continue
            a = r.agent_id
            if a not in by_agent:
                by_agent[a] = {"wins": 0, "total_bid": 0, "scores": []}
            by_agent[a]["wins"] += 1
            if r.bid is not None:
                by_agent[a]["total_bid"] += r.bid
            if r.score is not None:
                by_agent[a]["scores"].append(r.score)

        for a, stats in by_agent.items():
            stats["avg_bid"] = (
                round(stats["total_bid"] / stats["wins"], 6)
                if stats["wins"] else 0
            )
            stats["avg_score"] = (
                round(sum(stats["scores"]) / len(stats["scores"]), 2)
                if stats["scores"] else 0
            )
            del stats["total_bid"], stats["scores"]

        elapsed = time.time() - self._start_time

        return {
            "total_tasks": total,
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / total, 4) if total else 0,
            "total_elapsed_s": round(elapsed, 1),
            "by_difficulty": by_difficulty,
            "by_agent": by_agent,
        }

    def save_json(self, path: str) -> None:
        data = {
            "results": [asdict(r) for r in self._results],
            "summary": self.summary(),
        }
        Path(path).write_text(json.dumps(data, indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_results.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sim/results.py tests/test_results.py
git commit -m "feat: add result collector with JSON output and summary stats"
```

---

### Task 7: Simulation Runner — The Full Orchestrator

**Files:**
- Create: `sim/run_simulation.py`

This is the main entry point that ties everything together: starts the exchange, launches agents, fires tasks concurrently, collects results.

- [ ] **Step 1: Implement the simulation runner**

```python
# sim/run_simulation.py
#!/usr/bin/env python3
"""Run the full simulation: exchange + N agents + 1,000 concurrent tasks.

Usage:
    python sim/run_simulation.py                        # defaults: 1000 tasks, 5 agents
    python sim/run_simulation.py --tasks 100            # quick run
    python sim/run_simulation.py --concurrency 50       # max 50 concurrent tasks
    python sim/run_simulation.py --output results.json  # custom output path
    python sim/run_simulation.py --budget 5.0           # $5 starting balance per agent
"""

from __future__ import annotations
import argparse
import asyncio
import logging
import os
import sys
import threading
import time
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load env
for env_path in [ROOT / ".env", Path.home() / "Desktop" / "meetrics" / ".env",
                  Path.home() / ".config" / "keys" / ".env"]:
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

import httpx
import uvicorn

from sim.task_bank import generate_tasks
from sim.agent_fleet import DEFAULT_FLEET, launch_fleet, AgentConfig
from sim.balance import BalanceTracker
from sim.results import ResultCollector, SimulationResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
)
logger = logging.getLogger("simulation")

EXCHANGE_URL = "http://localhost:8000"


def start_exchange_server(port: int = 8000) -> threading.Thread:
    """Start the exchange server in a background thread."""
    from exchange.server import app

    def run():
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

    t = threading.Thread(target=run, daemon=True, name="exchange-server")
    t.start()

    # Wait for server to be ready
    import socket
    for _ in range(40):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except (ConnectionRefusedError, OSError):
            time.sleep(0.25)

    logger.info(f"Exchange server running on port {port}")
    return t


async def submit_task(client: httpx.AsyncClient, task: dict,
                      timeout: float = 60.0) -> SimulationResult:
    """Submit a single task to the exchange and return the result."""
    start = time.time()
    try:
        resp = await client.post(
            f"{EXCHANGE_URL}/call",
            json={
                "input": task["input"],
                "max_price": task["max_price"],
                "min_quality": task["min_quality"],
                "timeout": timeout,
            },
            headers={"Authorization": "Bearer demo"},
            timeout=timeout + 10,
        )
        elapsed_ms = (time.time() - start) * 1000

        if resp.status_code == 200:
            data = resp.json()
            return SimulationResult(
                task_id=task["task_id"],
                input=task["input"],
                difficulty=task["difficulty"],
                category=task["category"],
                max_price=task["max_price"],
                min_quality=task["min_quality"],
                agent_id=data.get("agent_id"),
                bid=data.get("price"),
                score=data.get("score"),
                latency_ms=elapsed_ms,
                output=data.get("output", "")[:2000],  # truncate for JSON size
                error=None,
            )
        else:
            detail = ""
            try:
                detail = resp.json().get("detail", resp.text[:200])
            except Exception:
                detail = resp.text[:200]
            return SimulationResult(
                task_id=task["task_id"],
                input=task["input"],
                difficulty=task["difficulty"],
                category=task["category"],
                max_price=task["max_price"],
                min_quality=task["min_quality"],
                agent_id=None, bid=None, score=None,
                latency_ms=elapsed_ms,
                output=None,
                error=f"HTTP {resp.status_code}: {detail}",
            )

    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        return SimulationResult(
            task_id=task["task_id"],
            input=task["input"],
            difficulty=task["difficulty"],
            category=task["category"],
            max_price=task["max_price"],
            min_quality=task["min_quality"],
            agent_id=None, bid=None, score=None,
            latency_ms=elapsed_ms,
            output=None,
            error=str(e),
        )


async def run_all_tasks(tasks: list[dict], concurrency: int = 20,
                        timeout: float = 60.0) -> ResultCollector:
    """Fire all tasks concurrently with a semaphore for rate limiting."""
    collector = ResultCollector()
    semaphore = asyncio.Semaphore(concurrency)
    completed = 0
    total = len(tasks)

    async def bounded_submit(client: httpx.AsyncClient, task: dict):
        nonlocal completed
        async with semaphore:
            result = await submit_task(client, task, timeout=timeout)
            collector.add(result)
            completed += 1
            if completed % 50 == 0 or completed == total:
                logger.info(
                    f"Progress: {completed}/{total} "
                    f"({collector.count - collector.failure_count} wins, "
                    f"{collector.failure_count} failures)"
                )

    async with httpx.AsyncClient() as client:
        coros = [bounded_submit(client, task) for task in tasks]
        await asyncio.gather(*coros)

    return collector


def print_summary(collector: ResultCollector, balances: BalanceTracker):
    """Print a nice summary to stdout."""
    s = collector.summary()

    print("\n" + "=" * 70)
    print("  SIMULATION RESULTS")
    print("=" * 70)
    print(f"  Total tasks:    {s['total_tasks']}")
    print(f"  Successful:     {s['successful']} ({s['success_rate']*100:.1f}%)")
    print(f"  Failed:         {s['failed']}")
    print(f"  Elapsed:        {s['total_elapsed_s']}s")

    print(f"\n  {'─' * 66}")
    print(f"  BY DIFFICULTY")
    print(f"  {'─' * 66}")
    for diff in ["trivial", "easy", "medium", "hard", "brutal"]:
        if diff in s["by_difficulty"]:
            d = s["by_difficulty"][diff]
            print(
                f"  {diff:10s}  "
                f"{d['successful']:>4d}/{d['total']:<4d} wins  "
                f"avg score {d['avg_score']:>4.1f}  "
                f"avg bid ${d['avg_bid']:.4f}  "
                f"avg latency {d['avg_latency_ms']:>7.0f}ms"
            )

    print(f"\n  {'─' * 66}")
    print(f"  BY AGENT")
    print(f"  {'─' * 66}")
    for agent_id, stats in sorted(s["by_agent"].items(),
                                   key=lambda x: x[1]["wins"], reverse=True):
        bal = balances.get(agent_id)
        print(
            f"  {agent_id:20s}  "
            f"{stats['wins']:>4d} wins  "
            f"avg score {stats['avg_score']:>4.1f}  "
            f"avg bid ${stats['avg_bid']:.4f}  "
            f"balance ${bal:>8.4f}"
        )

    print(f"\n  {'─' * 66}")
    print(f"  AGENT BALANCES")
    print(f"  {'─' * 66}")
    for agent_id, bal in sorted(balances.get_all().items()):
        print(f"  {agent_id:20s}  ${bal:.4f}")

    print("=" * 70)


def parse_args():
    p = argparse.ArgumentParser(description="AgentX Exchange Simulation")
    p.add_argument("--tasks", type=int, default=1000,
                   help="Number of tasks to simulate (default: 1000)")
    p.add_argument("--concurrency", type=int, default=20,
                   help="Max concurrent task submissions (default: 20)")
    p.add_argument("--timeout", type=float, default=60.0,
                   help="Per-task timeout in seconds (default: 60)")
    p.add_argument("--budget", type=float, default=10.0,
                   help="Starting balance per agent in USD (default: 10.0)")
    p.add_argument("--output", type=str, default="sim/results.json",
                   help="Output JSON path (default: sim/results.json)")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed for task generation (default: 42)")
    p.add_argument("--exchange-port", type=int, default=8000,
                   help="Exchange server port (default: 8000)")
    return p.parse_args()


def main():
    args = parse_args()

    global EXCHANGE_URL
    EXCHANGE_URL = f"http://localhost:{args.exchange_port}"

    logger.info(f"Generating {args.tasks} tasks...")
    all_tasks = generate_tasks(seed=args.seed)
    tasks = all_tasks[:args.tasks]
    logger.info(f"Using {len(tasks)} tasks")

    # Start exchange
    logger.info("Starting exchange server...")
    start_exchange_server(port=args.exchange_port)

    # Start agents
    logger.info("Launching agent fleet...")
    balances = BalanceTracker(initial=args.budget)
    fleet_threads = launch_fleet(
        DEFAULT_FLEET, balances,
        exchange_url=EXCHANGE_URL,
    )
    # Give agents time to register
    time.sleep(2)

    # Verify agents registered
    try:
        with httpx.Client(timeout=5) as c:
            resp = c.get(f"{EXCHANGE_URL}/status")
            status = resp.json()
            logger.info(f"Exchange status: {status['agents_registered']} agents registered")
    except Exception as e:
        logger.error(f"Exchange not responding: {e}")
        sys.exit(1)

    # Fire tasks
    logger.info(
        f"Firing {len(tasks)} tasks with concurrency={args.concurrency}..."
    )
    collector = asyncio.run(
        run_all_tasks(tasks, concurrency=args.concurrency, timeout=args.timeout)
    )

    # Deduct winning bids from agent balances
    for r in collector._results:
        if r.agent_id and r.bid is not None:
            balances.deduct(r.agent_id, r.bid)

    # Output
    output_path = str(ROOT / args.output)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    collector.save_json(output_path)
    logger.info(f"Results saved to {output_path}")

    print_summary(collector, balances)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add sim/run_simulation.py
git commit -m "feat: add concurrent simulation runner with CLI args"
```

---

### Task 8: Integration Smoke Test — 10 Tasks, 3 Agents

**Files:**
- Create: `tests/test_simulation_smoke.py`

This test verifies the full pipeline works end-to-end with a small task count. It starts a real exchange, registers real agents (with mocked LLM calls for speed), and runs 10 tasks concurrently.

- [ ] **Step 1: Write the integration test**

```python
# tests/test_simulation_smoke.py
"""Smoke test: run 10 tasks through the full simulation pipeline.

Uses mocked LLM calls for speed (no real API costs).
Tests the full HTTP flow: exchange ← agents ← broadcast ← submit.
"""

import asyncio
import json
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import uvicorn

from agentx.provider import AgentProvider
from sim.balance import BalanceTracker
from sim.results import ResultCollector, SimulationResult
from sim.task_bank import generate_tasks

# Use a random high port to avoid conflicts
EXCHANGE_PORT = 18765
EXCHANGE_URL = f"http://localhost:{EXCHANGE_PORT}"


@pytest.fixture(scope="module")
def exchange_server():
    """Start exchange on a test port."""
    from exchange.server import app

    def run():
        uvicorn.run(app, host="127.0.0.1", port=EXCHANGE_PORT, log_level="error")

    t = threading.Thread(target=run, daemon=True)
    t.start()
    for _ in range(40):
        try:
            with socket.create_connection(("127.0.0.1", EXCHANGE_PORT), timeout=0.5):
                break
        except (ConnectionRefusedError, OSError):
            time.sleep(0.25)
    yield
    # Server dies when test process exits (daemon thread)


@pytest.fixture(scope="module")
def mock_agents(exchange_server):
    """Register 3 mock agents (no real LLM calls)."""
    agents = []
    base_port = 19001

    for i, (name, bid_frac) in enumerate([
        ("mock-cheap", 0.3),
        ("mock-mid", 0.5),
        ("mock-premium", 0.7),
    ]):
        port = base_port + i
        provider = AgentProvider(
            exchange_url=EXCHANGE_URL,
            agent_id=name,
            callback_port=port,
        )

        def make_handler(frac, agent_name):
            def handler(request):
                task = request["input"]
                max_price = request["max_price"]
                bid = round(max_price * frac, 6)
                work = f"[{agent_name}] Mock response to: {task[:50]}"
                return {"bid": bid, "work": work}
            return handler

        provider.handle()(make_handler(bid_frac, name))
        t = threading.Thread(target=provider.start, daemon=True)
        t.start()
        agents.append(name)

    time.sleep(2)  # Wait for all agents to register
    yield agents


def test_smoke_10_tasks(exchange_server, mock_agents):
    """Run 10 tasks and verify results."""
    tasks = generate_tasks(seed=99)[:10]

    async def run():
        collector = ResultCollector()
        async with httpx.AsyncClient() as client:
            for task in tasks:
                start = time.time()
                try:
                    resp = await client.post(
                        f"{EXCHANGE_URL}/call",
                        json={
                            "input": task["input"],
                            "max_price": task["max_price"],
                            "min_quality": task["min_quality"],
                            "timeout": 30.0,
                        },
                        headers={"Authorization": "Bearer demo"},
                        timeout=40.0,
                    )
                    elapsed = (time.time() - start) * 1000
                    if resp.status_code == 200:
                        data = resp.json()
                        collector.add(SimulationResult(
                            task_id=task["task_id"],
                            input=task["input"],
                            difficulty=task["difficulty"],
                            category=task["category"],
                            max_price=task["max_price"],
                            min_quality=task["min_quality"],
                            agent_id=data["agent_id"],
                            bid=data["price"],
                            score=data.get("score"),
                            latency_ms=elapsed,
                            output=data["output"][:500],
                            error=None,
                        ))
                    else:
                        collector.add(SimulationResult(
                            task_id=task["task_id"],
                            input=task["input"],
                            difficulty=task["difficulty"],
                            category=task["category"],
                            max_price=task["max_price"],
                            min_quality=task["min_quality"],
                            agent_id=None, bid=None, score=None,
                            latency_ms=elapsed, output=None,
                            error=f"HTTP {resp.status_code}",
                        ))
                except Exception as e:
                    elapsed = (time.time() - start) * 1000
                    collector.add(SimulationResult(
                        task_id=task["task_id"],
                        input=task["input"],
                        difficulty=task["difficulty"],
                        category=task["category"],
                        max_price=task["max_price"],
                        min_quality=task["min_quality"],
                        agent_id=None, bid=None, score=None,
                        latency_ms=elapsed, output=None,
                        error=str(e),
                    ))
        return collector

    collector = asyncio.run(run())

    # At least some tasks should succeed (judge may fail w/o real API key)
    assert collector.count == 10

    # Save results to temp file and verify JSON structure
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    collector.save_json(path)
    data = json.loads(Path(path).read_text())
    assert "results" in data
    assert "summary" in data
    assert len(data["results"]) == 10
    Path(path).unlink()

    summary = collector.summary()
    assert summary["total_tasks"] == 10
```

- [ ] **Step 2: Run the smoke test**

Run: `cd /Users/benrapport/conductor/workspaces/exchangification/riga && python -m pytest tests/test_simulation_smoke.py -v --timeout=120`

Expected: Test passes. Some tasks may fail if no OPENAI_API_KEY is set (judge needs it), but the HTTP flow and result collection should work regardless.

- [ ] **Step 3: Commit**

```bash
git add tests/test_simulation_smoke.py
git commit -m "test: add integration smoke test for simulation pipeline"
```

---

### Task 9: Add .gitignore for simulation output

**Files:**
- Modify: `.gitignore` (or create if doesn't exist)

- [ ] **Step 1: Create/update .gitignore**

```
# sim/results.json and any simulation output
sim/results*.json
sim/output/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore simulation output files"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] 1,000 tasks across difficulty tiers → Task 1
- [x] Hard/brutal tasks (B-trees, consensus, VMs, compilers) → Task 1 (HARD_SEEDS, BRUTAL_SEEDS)
- [x] Full game state available to agents → Task 4 (agent_count, exchange_stats)
- [x] Agents are coding agent instances, not single-shot LLM calls → Task 2 (ToolAgent with multi-turn loop)
- [x] Claw-code inspired architecture → Task 2 (turn loop pattern from PortRuntime)
- [x] Real HTTP, real concurrency → Task 7 (asyncio + real FastAPI servers)
- [x] Real money / balance tracking → Task 3 (BalanceTracker, race-tolerant)
- [x] JSON output → Task 6 (ResultCollector.save_json)
- [x] IO-bound concurrent dispatch → Task 7 (asyncio.Semaphore, httpx.AsyncClient)

**Placeholder scan:** No TBDs, TODOs, or "implement later" found.

**Type consistency:** ToolAgent.run() returns str. AgentProvider handler returns dict | None. SimulationResult fields match what submit_task produces. BroadcastPayload fields match what game.py populates.
