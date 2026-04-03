"""Results collection: JSONL streaming + summary report generation."""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import median, quantiles


@dataclass
class TaskResult:
    """Result of a single task execution."""

    task_id: str
    category: str
    difficulty: str
    winner_agent: str | None = None
    fill_price: float | None = None
    score: int | None = None
    latency_ms: float = 0.0
    output: str = ""
    error: str | None = None
    timestamp: float = field(default_factory=time.time)


class ResultsWriter:
    """Stream results to JSONL file as they arrive. Crash-safe."""

    def __init__(self, output_dir: str = "sim_results"):
        """Initialize results writer.

        Args:
            output_dir: Directory to write results to.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create JSONL file with timestamp
        timestamp = int(time.time())
        self.jsonl_path = self.output_dir / f"results_{timestamp}.jsonl"
        self.file = open(self.jsonl_path, "w")

    def write(self, result: TaskResult):
        """Append one result. Flush immediately for crash safety.

        Args:
            result: TaskResult to write.
        """
        line = json.dumps(asdict(result))
        self.file.write(line + "\n")
        self.file.flush()

    def close(self) -> Path:
        """Close file and return path to JSONL.

        Returns:
            Path to the written JSONL file.
        """
        self.file.close()
        return self.jsonl_path


def generate_summary(results: list[TaskResult]) -> dict:
    """Generate aggregate summary dict.

    Args:
        results: List of TaskResult objects.

    Returns:
        Summary dict with statistics.
    """
    if not results:
        return {
            "total_tasks": 0,
            "completed": 0,
            "timed_out": 0,
            "agent_leaderboard": [],
            "by_category": {},
            "by_difficulty": {},
            "economics": {"total_volume_usd": 0.0, "avg_price_usd": 0.0},
            "timing": {
                "total_seconds": 0.0,
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
            },
        }

    total_tasks = len(results)
    completed = sum(1 for r in results if r.winner_agent is not None and r.error is None)
    timed_out = sum(1 for r in results if r.error is not None)

    # Agent leaderboard
    agent_stats = {}
    for result in results:
        if result.winner_agent is None:
            continue
        agent = result.winner_agent
        if agent not in agent_stats:
            agent_stats[agent] = {
                "wins": 0,
                "prices": [],
                "scores": [],
                "latencies": [],
            }
        agent_stats[agent]["wins"] += 1
        if result.fill_price is not None:
            agent_stats[agent]["prices"].append(result.fill_price)
        if result.score is not None:
            agent_stats[agent]["scores"].append(result.score)
        if result.latency_ms > 0:
            agent_stats[agent]["latencies"].append(result.latency_ms)

    leaderboard = []
    for agent, stats in agent_stats.items():
        leaderboard.append(
            {
                "agent": agent,
                "wins": stats["wins"],
                "win_rate": stats["wins"] / total_tasks if total_tasks > 0 else 0.0,
                "avg_fill_price": sum(stats["prices"]) / len(stats["prices"]) if stats["prices"] else 0.0,
                "avg_score": sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0.0,
                "avg_latency_ms": sum(stats["latencies"]) / len(stats["latencies"]) if stats["latencies"] else 0.0,
            }
        )
    leaderboard.sort(key=lambda x: x["wins"], reverse=True)

    # By category
    by_category = {}
    for result in results:
        cat = result.category
        if cat not in by_category:
            by_category[cat] = {
                "completed": 0,
                "total": 0,
                "scores": [],
                "latencies": [],
                "prices": [],
            }
        by_category[cat]["total"] += 1
        if result.error is None and result.winner_agent is not None:
            by_category[cat]["completed"] += 1
        if result.score is not None:
            by_category[cat]["scores"].append(result.score)
        if result.latency_ms > 0:
            by_category[cat]["latencies"].append(result.latency_ms)
        if result.fill_price is not None:
            by_category[cat]["prices"].append(result.fill_price)

    category_summary = {}
    for cat, stats in by_category.items():
        category_summary[cat] = {
            "total": stats["total"],
            "completed": stats["completed"],
            "completion_rate": stats["completed"] / stats["total"] if stats["total"] > 0 else 0.0,
            "avg_score": sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0.0,
            "avg_latency_ms": sum(stats["latencies"]) / len(stats["latencies"]) if stats["latencies"] else 0.0,
            "avg_fill_price": sum(stats["prices"]) / len(stats["prices"]) if stats["prices"] else 0.0,
        }

    # By difficulty
    by_difficulty = {}
    for result in results:
        diff = result.difficulty
        if diff not in by_difficulty:
            by_difficulty[diff] = {
                "completed": 0,
                "total": 0,
                "scores": [],
                "latencies": [],
                "prices": [],
            }
        by_difficulty[diff]["total"] += 1
        if result.error is None and result.winner_agent is not None:
            by_difficulty[diff]["completed"] += 1
        if result.score is not None:
            by_difficulty[diff]["scores"].append(result.score)
        if result.latency_ms > 0:
            by_difficulty[diff]["latencies"].append(result.latency_ms)
        if result.fill_price is not None:
            by_difficulty[diff]["prices"].append(result.fill_price)

    difficulty_summary = {}
    for diff, stats in by_difficulty.items():
        difficulty_summary[diff] = {
            "total": stats["total"],
            "completed": stats["completed"],
            "completion_rate": stats["completed"] / stats["total"] if stats["total"] > 0 else 0.0,
            "avg_score": sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0.0,
            "avg_latency_ms": sum(stats["latencies"]) / len(stats["latencies"]) if stats["latencies"] else 0.0,
            "avg_fill_price": sum(stats["prices"]) / len(stats["prices"]) if stats["prices"] else 0.0,
        }

    # Economics
    total_volume = sum(r.fill_price for r in results if r.fill_price is not None)
    priced_results = [r for r in results if r.fill_price is not None]
    avg_price = total_volume / len(priced_results) if priced_results else 0.0

    # Timing and latencies
    latencies = [r.latency_ms for r in results if r.latency_ms > 0]
    if latencies:
        latencies.sort()
        p50 = median(latencies)
        # quantiles() requires at least 2 data points
        if len(latencies) >= 2:
            q = quantiles(latencies, n=100)
            p95 = q[94]  # 95th percentile
            p99 = q[98]  # 99th percentile
        else:
            p95 = latencies[0]
            p99 = latencies[0]
    else:
        p50 = 0.0
        p95 = 0.0
        p99 = 0.0

    return {
        "total_tasks": total_tasks,
        "completed": completed,
        "timed_out": timed_out,
        "completion_rate": completed / total_tasks if total_tasks > 0 else 0.0,
        "agent_leaderboard": leaderboard,
        "by_category": category_summary,
        "by_difficulty": difficulty_summary,
        "economics": {
            "total_volume_usd": round(total_volume, 2),
            "avg_price_usd": round(avg_price, 4),
        },
        "timing": {
            "total_seconds": sum(r.latency_ms for r in results) / 1000.0,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0.0,
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
            "p99_latency_ms": p99,
        },
    }


def save_summary(summary: dict, output_dir: str = "sim_results") -> Path:
    """Write summary dict as formatted JSON file.

    Args:
        summary: Summary dict from generate_summary().
        output_dir: Directory to write to.

    Returns:
        Path to the written JSON file.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    summary_path = output_path / f"summary_{timestamp}.json"

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    return summary_path
