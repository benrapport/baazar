"""Run the full simulation. Entry point: python3 -m sim.runner

Usage:
    python3 -m sim.runner                      # Full 1K run
    python3 -m sim.runner --tasks 100          # Pilot
    python3 -m sim.runner --tasks 10 --dry     # Dry run (mocked)
    python3 -m sim.runner --concurrent 100     # More parallelism
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

from sim.tasks import load_task_bank, Task
from sim.fleet import Fleet, DEFAULT_FLEET
from sim.results import TaskResult, ResultsWriter, generate_summary, save_summary

logger = logging.getLogger(__name__)

class SimulationRunner:
    def __init__(
        self,
        num_tasks: int = 1000,
        max_concurrent: int = 50,
        exchange_url: str = "http://localhost:8000",
        output_dir: str = "sim_results",
        fleet_members: list | None = None,
    ):
        self.num_tasks = num_tasks
        self.max_concurrent = max_concurrent
        self.exchange_url = exchange_url
        self.output_dir = output_dir
        self._fleet_members = fleet_members
        self._exchange_process = None
        self._fleet = None

    async def run(self) -> dict:
        """Full simulation lifecycle:
        1. Start exchange server (subprocess)
        2. Launch agent fleet
        3. Load tasks (truncated to num_tasks)
        4. Fire all tasks concurrently via POST /call
        5. Collect results, stream to JSONL
        6. Generate + save summary
        7. Print results
        8. Shutdown

        Returns summary dict.
        """
        # Set up market log path so exchange writes JSONL directly
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        self._market_log_ts = int(time.time())
        market_log_path = output_path / f"markets_{self._market_log_ts}.jsonl"
        env = {**os.environ, "MARKET_LOG_PATH": str(market_log_path)}

        try:
            # 1. Start exchange server
            logger.info("Starting exchange server...")
            self._exchange_process = subprocess.Popen(
                [sys.executable, "demo/run_exchange.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            await asyncio.sleep(2)  # Give it time to bind

            # 2. Wait for exchange to be ready
            logger.info("Waiting for exchange to be ready...")
            await self._wait_for_exchange()

            # 3. Launch agent fleet
            self._fleet = Fleet(
                members=self._fleet_members,
                exchange_url=self.exchange_url,
            )
            logger.info(f"Launching agent fleet ({len(self._fleet.members)} agents)...")
            self._fleet.launch()
            await asyncio.sleep(1)  # Give agents time to start

            # 4. Load tasks
            logger.info(f"Loading task bank (requesting {self.num_tasks})...")
            all_tasks = load_task_bank()
            tasks = all_tasks[:self.num_tasks]
            logger.info(f"Loaded {len(tasks)} tasks")

            # 5. Fire tasks and collect results
            logger.info(f"Firing {len(tasks)} tasks with max_concurrent={self.max_concurrent}")
            output_path = Path(self.output_dir)
            output_path.mkdir(exist_ok=True)

            writer = ResultsWriter(output_dir=self.output_dir)
            results = await self._fire_tasks(tasks, writer)
            results_file = writer.close()
            logger.info(f"Results written to {results_file}")

            # 6. Check market logs (written by exchange server directly)
            if market_log_path.exists():
                count = sum(1 for _ in open(market_log_path))
                logger.info(f"Market logs: {market_log_path} ({count} markets)")
            else:
                logger.warning("No market log file found — exchange may not have written any")

            # 7. Generate and save summary (include agent costs for PnL)
            logger.info("Generating summary...")
            agent_costs = {}
            if self._fleet:
                for stat in self._fleet.get_agent_stats():
                    agent_costs[stat["agent_id"]] = stat["total_cost_usd"]
            summary = generate_summary(results)
            summary["agent_costs_usd"] = agent_costs
            summary_file = save_summary(summary, output_dir=self.output_dir)
            logger.info(f"Summary written to {summary_file}")

            # 8. Print results
            self._print_results(summary, results)

            return summary

        finally:
            # 8. Shutdown
            if self._fleet:
                self._fleet.stop()
            if self._exchange_process:
                logger.info("Stopping exchange server...")
                self._exchange_process.terminate()
                try:
                    self._exchange_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._exchange_process.kill()

    async def _wait_for_exchange(self, max_retries: int = 30):
        """Poll GET /status until exchange is ready."""
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.exchange_url}/status", timeout=2)
                    if response.status_code == 200:
                        logger.info("Exchange is ready")
                        return
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            await asyncio.sleep(0.5)
        raise RuntimeError("Exchange server did not become ready in time")

    async def _fire_tasks(self, tasks: list[Task], writer: ResultsWriter) -> list[TaskResult]:
        """Submit all tasks concurrently with semaphore control.

        Uses httpx.AsyncClient with connection pooling:
        - limits = httpx.Limits(max_connections=100, max_keepalive_connections=50)
        - timeout = httpx.Timeout(task.timeout + 10)

        For each task:
        - POST to {exchange_url}/call with CallRequest body
        - On success: create TaskResult from ExchangeResult
        - On error/timeout: create TaskResult with error field
        - Write to ResultsWriter immediately
        - Print progress every 50 tasks

        Uses asyncio.Semaphore(max_concurrent) to limit parallelism.
        """
        limits = httpx.Limits(max_connections=100, max_keepalive_connections=50)
        timeout = httpx.Timeout(timeout=300.0)  # Global timeout for the client

        semaphore = asyncio.Semaphore(self.max_concurrent)
        results = []
        start_time = time.time()

        async def bounded_call(client: httpx.AsyncClient, task: Task, idx: int) -> TaskResult:
            async with semaphore:
                result = await self._call_exchange(client, task)
                writer.write(result)

                # Progress update every 50 tasks
                if (idx + 1) % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = (idx + 1) / elapsed
                    remaining = len(tasks) - (idx + 1)
                    eta_sec = remaining / rate if rate > 0 else 0
                    logger.info(
                        f"[{idx + 1}/{len(tasks)}] rate {rate:.1f} tasks/sec ETA {eta_sec:.0f}s"
                    )

                return result

        async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
            tasks_coro = [bounded_call(client, task, idx) for idx, task in enumerate(tasks)]
            results = await asyncio.gather(*tasks_coro, return_exceptions=False)

        return results

    async def _call_exchange(self, client: httpx.AsyncClient, task: Task) -> TaskResult:
        """Single /call request to exchange. Returns TaskResult."""
        request_body = {
            "llm": {
                "input": task.input,
            },
            "exchange": {
                "max_price": task.max_price,
                "judge": {
                    "min_quality": task.min_quality,
                    "criteria": task.quality_criteria,
                },
                "timeout": task.timeout,
            },
        }

        try:
            task_timeout = task.timeout + 10.0
            response = await client.post(
                f"{self.exchange_url}/call",
                json=request_body,
                headers={"Authorization": "Bearer demo"},
                timeout=task_timeout,
            )

            if response.status_code == 200:
                exchange_result = response.json()
                return TaskResult(
                    task_id=task.task_id,
                    category=task.category,
                    difficulty=task.difficulty,
                    winner_agent=exchange_result.get("agent_id"),
                    fill_price=exchange_result.get("price"),
                    score=exchange_result.get("score"),
                    latency_ms=exchange_result.get("latency_ms", 0),
                    output=exchange_result.get("output", ""),
                )
            else:
                return TaskResult(
                    task_id=task.task_id,
                    category=task.category,
                    difficulty=task.difficulty,
                    error=f"HTTP {response.status_code}: {response.text}",
                )

        except httpx.TimeoutException as e:
            return TaskResult(
                task_id=task.task_id,
                category=task.category,
                difficulty=task.difficulty,
                error=f"Timeout after {task.timeout}s",
            )
        except httpx.HTTPStatusError as e:
            return TaskResult(
                task_id=task.task_id,
                category=task.category,
                difficulty=task.difficulty,
                error=f"HTTP error: {e}",
            )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                category=task.category,
                difficulty=task.difficulty,
                error=f"Exception: {type(e).__name__}: {e}",
            )

    def _print_results(self, summary: dict, results: list[TaskResult]):
        """Print leaderboard and stats."""
        print("\n" + "=" * 80)
        print("SIMULATION COMPLETE")
        print("=" * 80)

        # Overall stats
        print(f"\nTotal tasks: {summary.get('total_tasks', 0)}")
        print(f"Tasks completed: {summary.get('completed_tasks', 0)}")
        print(f"Total cost: ${summary.get('total_cost_usd', 0):.2f}")
        print(f"Average price per task: ${summary.get('avg_price_usd', 0):.4f}")
        print(f"Average score: {summary.get('avg_score', 0):.2f}")

        # Leaderboard
        if "agent_wins" in summary:
            print("\nAgent Leaderboard (by wins):")
            print("-" * 40)
            for agent_id, wins in sorted(summary["agent_wins"].items(), key=lambda x: x[1], reverse=True):
                pct = 100.0 * wins / summary.get('total_tasks', 1)
                print(f"  {agent_id:20s}: {wins:4d} wins ({pct:5.1f}%)")

        # Category breakdown
        if "category_stats" in summary:
            print("\nResults by Category:")
            print("-" * 40)
            for category, stats in summary["category_stats"].items():
                print(f"  {category:20s}: {stats.get('count', 0):4d} tasks, avg score {stats.get('avg_score', 0):.2f}")

        print("\n" + "=" * 80)

        # Fleet stats
        if self._fleet:
            print("\nFleet Cost Summary:")
            print("-" * 40)
            stats = self._fleet.get_agent_stats()
            for agent_stat in stats:
                agent_id = agent_stat["agent_id"]
                cost_usd = agent_stat["total_cost_usd"]
                remaining_usd = agent_stat["budget_remaining_usd"]
                print(f"  {agent_id:20s}: used ${cost_usd:.2f}, remaining ${remaining_usd:.2f}")
            print("=" * 80 + "\n")


def _load_api_keys():
    """Load API keys from ~/.config/keys/ and .env."""
    key_path = Path.home() / ".config" / "keys" / "openai"
    if key_path.exists():
        os.environ.setdefault("OPENAI_API_KEY", key_path.read_text().strip())

    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def main():
    _load_api_keys()
    parser = argparse.ArgumentParser(description="Run exchange simulation")
    parser.add_argument("--tasks", type=int, default=1000, help="Number of tasks")
    parser.add_argument("--concurrent", type=int, default=50, help="Max concurrent requests")
    parser.add_argument("--fleet-size", type=int, default=0,
                        help="Number of agents (0 = default 5-agent fleet)")
    parser.add_argument("--exchange-url", type=str, default="http://localhost:8000")
    parser.add_argument("--output", type=str, default="sim_results")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    fleet_members = None
    if args.fleet_size > 0:
        from sim.fleet import generate_fleet
        fleet_members = generate_fleet(size=args.fleet_size)

    runner = SimulationRunner(
        num_tasks=args.tasks,
        max_concurrent=args.concurrent,
        exchange_url=args.exchange_url,
        output_dir=args.output,
        fleet_members=fleet_members,
    )
    summary = asyncio.run(runner.run())

    # Exit with success code
    sys.exit(0)


if __name__ == "__main__":
    main()
