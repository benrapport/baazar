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
    max_price: float = 0.0
    min_quality: int = 0


class AgentMemory:
    """Fixed-size replay buffer for one agent."""

    def __init__(self, max_entries: int = 30):
        self.max_entries = max_entries
        self.attempts: list[Attempt] = []
        # Track pending attempts by request_id so we can attach scores later
        self._pending: dict[str, Attempt] = {}

    def record_attempt(self, request_id: str, task: str,
                       rewritten_prompt: str, model: str,
                       max_price: float = 0.0, min_quality: int = 0):
        """Record an attempt before the score is known."""
        attempt = Attempt(
            task=task,
            rewritten_prompt=rewritten_prompt,
            model=model,
            max_price=max_price,
            min_quality=min_quality,
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

    def estimate_qualification_rate(self, min_quality: int) -> float:
        """What fraction of my past attempts would have met this quality bar?"""
        scored = self.scored_attempts
        if not scored:
            return 0.5  # optimistic prior with no data
        qualified = sum(1 for a in scored if a.score >= min_quality)
        return qualified / len(scored)

    def estimate_win_rate_at_bar(self, min_quality: int) -> float:
        """Of my past attempts that met a similar quality bar, how often did I win?"""
        relevant = [a for a in self.scored_attempts
                    if a.min_quality >= min_quality - 1]
        if not relevant:
            return self.get_win_rate() or 0.2  # fallback
        won = sum(1 for a in relevant if a.won)
        return won / len(relevant)

    def should_bid(self, max_price: float, min_quality: int,
                   cost_per_attempt: float, n_competitors: int = 10,
                   top_n: int = 1) -> tuple[bool, str]:
        """Decide whether to bid on a market based on expected value.

        top_n > 1 means multiple winners get paid — increases win probability.
        Returns (should_fill, reason).
        """
        scored = self.scored_attempts
        margin = max_price - cost_per_attempt

        # Always pass if margin is negative
        if margin <= 0:
            return False, f"negative margin (${margin:.4f})"

        # With no history, be willing to explore (but require positive margin)
        if len(scored) < 3:
            if margin > cost_per_attempt * 0.3:
                return True, f"exploring (top_n={top_n})"
            return False, f"thin margin for exploration (${margin:.4f})"

        # Estimate qualification probability
        qual_rate = self.estimate_qualification_rate(min_quality)

        # Estimate win probability
        # top_n > 1 multiplies the naive win chance — more winner slots
        historical_win_rate = self.get_win_rate() or 0.1
        naive_win_rate = qual_rate * min(top_n, n_competitors) / max(n_competitors * 0.5, 1)
        naive_win_rate = min(naive_win_rate, 0.9)  # cap at 90%
        est_win_prob = 0.6 * historical_win_rate + 0.4 * naive_win_rate

        # Boost win probability for top_n > 1 based on qualification rate
        if top_n > 1:
            # If I qualify, my odds are roughly top_n/qualified_agents
            est_win_prob = min(est_win_prob * (1 + (top_n - 1) * 0.3), 0.9)

        # Expected value = P(win) * revenue - cost
        expected_revenue = est_win_prob * max_price
        expected_value = expected_revenue - cost_per_attempt

        if expected_value <= 0:
            return False, (f"negative EV (${expected_value:.4f}): "
                          f"P(qual)={qual_rate:.0%} P(win)={est_win_prob:.0%} "
                          f"top_n={top_n}")

        # Can I meet the quality bar?
        if qual_rate < 0.15 and len(scored) >= 5:
            return False, (f"low qualification rate ({qual_rate:.0%}) "
                          f"for q>={min_quality}")

        return True, (f"EV=${expected_value:.4f}: "
                     f"P(qual)={qual_rate:.0%} P(win)={est_win_prob:.0%} "
                     f"top_n={top_n}")

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
