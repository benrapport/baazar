"""Per-agent replay buffer for learning from past submissions.

Each agent maintains a fixed-size buffer of its recent attempts:
(task, rewritten_prompt, model, score, feedback, won).

The buffer is used to build few-shot context for prompt rewriting:
best-scoring examples show what works, worst show what to avoid.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Attempt:
    """A single past attempt by an agent."""
    task: str
    rewritten_prompt: str
    model: str
    score: int | None = None
    feedback: str = ""
    won: bool = False


class AgentMemory:
    """Fixed-size replay buffer for one agent."""

    def __init__(self, max_entries: int = 30):
        self.max_entries = max_entries
        self.attempts: list[Attempt] = []
        # Track pending attempts by request_id so we can attach scores later
        self._pending: dict[str, Attempt] = {}

    def record_attempt(self, request_id: str, task: str,
                       rewritten_prompt: str, model: str):
        """Record an attempt before the score is known."""
        attempt = Attempt(
            task=task,
            rewritten_prompt=rewritten_prompt,
            model=model,
        )
        self._pending[request_id] = attempt

    def record_score(self, request_id: str, score: int,
                     feedback: str = "", won: bool = False):
        """Attach a score to a pending attempt and move it to the buffer."""
        attempt = self._pending.pop(request_id, None)
        if attempt is None:
            return
        attempt.score = score
        attempt.feedback = feedback
        attempt.won = won
        self.attempts.append(attempt)
        # Evict oldest if over cap
        if len(self.attempts) > self.max_entries:
            self.attempts = self.attempts[-self.max_entries:]

    @property
    def scored_attempts(self) -> list[Attempt]:
        """All attempts that have scores."""
        return [a for a in self.attempts if a.score is not None]

    def get_best(self, n: int = 3) -> list[Attempt]:
        """Top N highest-scoring attempts."""
        scored = self.scored_attempts
        scored.sort(key=lambda a: a.score, reverse=True)
        return scored[:n]

    def get_worst(self, n: int = 2) -> list[Attempt]:
        """Bottom N lowest-scoring attempts."""
        scored = self.scored_attempts
        scored.sort(key=lambda a: a.score)
        return scored[:n]

    def get_avg_score(self) -> float | None:
        """Average score across all scored attempts."""
        scored = self.scored_attempts
        if not scored:
            return None
        return sum(a.score for a in scored) / len(scored)

    def get_win_rate(self) -> float | None:
        """Win rate across all scored attempts."""
        scored = self.scored_attempts
        if not scored:
            return None
        return sum(1 for a in scored if a.won) / len(scored)

    def build_context(self) -> str:
        """Build few-shot context string for prompt rewriting.

        Includes best examples (what works), worst examples (what to avoid),
        and overall stats.
        """
        scored = self.scored_attempts
        if not scored:
            return ""

        parts = []
        avg = self.get_avg_score()
        win_rate = self.get_win_rate()
        parts.append(
            f"Your performance so far: {len(scored)} tasks scored, "
            f"avg score {avg:.1f}/10, win rate {win_rate:.0%}."
        )

        best = self.get_best(3)
        if best:
            parts.append("\nYour BEST rewrites (learn from these):")
            for a in best:
                parts.append(
                    f"  Task: \"{a.task[:80]}\" → Rewrite: \"{a.rewritten_prompt[:120]}\" "
                    f"→ Score: {a.score}/10"
                    + (f" [WON]" if a.won else "")
                    + (f" — Judge: {a.feedback[:80]}" if a.feedback else "")
                )

        worst = self.get_worst(2)
        if worst and worst[0].score < (avg or 10):
            parts.append("\nYour WORST rewrites (avoid these patterns):")
            for a in worst:
                parts.append(
                    f"  Task: \"{a.task[:80]}\" → Rewrite: \"{a.rewritten_prompt[:120]}\" "
                    f"→ Score: {a.score}/10"
                    + (f" — Judge: {a.feedback[:80]}" if a.feedback else "")
                )

        return "\n".join(parts)
