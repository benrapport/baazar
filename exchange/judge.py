"""Judge — scores agent submissions using an LLM."""

from __future__ import annotations
import json
import logging
from openai import OpenAI
from exchange.types import Submission

logger = logging.getLogger(__name__)

DEFAULT_JUDGE_MODEL = "gpt-4o-mini"  # fast + cheap, buyer can override

DEFAULT_CRITERIA = [
    "Correctness: Does it accurately complete the task?",
    "Completeness: Is anything missing?",
    "Clarity: Is it well-written and easy to understand?",
    "Effort: Does it show genuine effort, not a minimal throwaway answer?",
]


def _build_judge_prompt(criteria: list[str], batch: bool = False) -> str:
    """Build judge system prompt from criteria list."""
    criteria_text = "\n".join(f"- {c}" for c in criteria)

    if batch:
        return (
            "You are scoring AI-generated work for a marketplace. "
            "Rate each submission 1-10.\n\n"
            f"Scoring criteria:\n{criteria_text}\n\n"
            "Be a fair but demanding judge. 7 = good professional quality. "
            "5 = mediocre. 9-10 = excellent.\n\n"
            "Respond with ONLY valid JSON:\n"
            '{"scores": {"<agent_id>": {"score": <1-10>, '
            '"feedback": "<1-2 sentences>"}, ...}}'
        )
    return (
        "You are scoring AI-generated work for a marketplace. "
        "Rate the submission 1-10.\n\n"
        f"Scoring criteria:\n{criteria_text}\n\n"
        "Be a fair but demanding judge. 7 = good professional quality. "
        "5 = mediocre. 9-10 = excellent.\n\n"
        "Respond with ONLY valid JSON:\n"
        '{"score": <1-10>, "feedback": "<1-2 sentence feedback>"}'
    )


def parse_json(raw: str) -> dict:
    """Robust JSON extraction from LLM responses."""
    if not raw or not raw.strip():
        raise ValueError("Empty response")
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start != -1:
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(text, start)
            return obj
        except json.JSONDecodeError:
            pass
    raise ValueError(f"No valid JSON in: {text[:200]}")


def _clamp_score(raw_score) -> int:
    """Validate and clamp score to 1-10 range."""
    try:
        score = int(raw_score)
    except (TypeError, ValueError):
        return 1
    return max(1, min(10, score))


def _truncate(text: str, max_chars: int = 50_000) -> str:
    """Truncate work to prevent token overflow in judge prompt."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [truncated, {len(text)} chars total]"


class Judge:
    def __init__(self, client: OpenAI | None = None,
                 model: str = DEFAULT_JUDGE_MODEL):
        self._client = client or OpenAI()
        self._model = model

    def score_submission(self, task: str, submission: Submission,
                         quality_criteria: list[str] | None = None) -> dict:
        """Score a single submission. Returns {score: int, feedback: str}.

        If quality_criteria is provided, uses those instead of defaults.
        """
        criteria = quality_criteria or DEFAULT_CRITERIA
        system_prompt = _build_judge_prompt(criteria)
        work = _truncate(submission.work)
        prompt = f"Task: {task}\n\nSubmission (bid ${submission.bid:.4f}):\n{work}"

        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                max_completion_tokens=256,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            result = parse_json(resp.choices[0].message.content)
            return {
                "score": _clamp_score(result.get("score")),
                "feedback": str(result.get("feedback", "")),
            }
        except Exception as e:
            logger.error(f"Judge scoring failed: {e}")
            return {"score": 1, "feedback": f"Judge error: {e}"}

    def score_batch(self, task: str,
                    submissions: dict[str, Submission],
                    quality_criteria: list[str] | None = None) -> dict[str, dict]:
        """Score multiple submissions. Returns {agent_id: {score, feedback}}."""
        criteria = quality_criteria or DEFAULT_CRITERIA
        system_prompt = _build_judge_prompt(criteria, batch=True)

        parts = [f"Task: {task}\n"]
        for agent_id, sub in submissions.items():
            work = _truncate(sub.work)
            parts.append(f"## {agent_id} (bid ${sub.bid:.4f})\n{work}\n")

        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                max_completion_tokens=1024,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "\n".join(parts)},
                ],
            )
            result = parse_json(resp.choices[0].message.content)
            scores = result.get("scores", result)

            validated = {}
            for agent_id in submissions:
                if agent_id in scores and isinstance(scores[agent_id], dict):
                    validated[agent_id] = {
                        "score": _clamp_score(scores[agent_id].get("score")),
                        "feedback": str(scores[agent_id].get("feedback", "")),
                    }
                else:
                    logger.warning(f"Judge missing score for {agent_id}")
                    validated[agent_id] = {
                        "score": 1,
                        "feedback": "Judge did not score this submission.",
                    }
            return validated

        except Exception as e:
            logger.error(f"Batch judge scoring failed: {e}")
            return {
                agent_id: {"score": 1, "feedback": f"Judge error: {e}"}
                for agent_id in submissions
            }
