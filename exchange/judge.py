"""Judge — scores agent submissions using an LLM."""

from __future__ import annotations
import json
import logging
from openai import OpenAI
from exchange.types import Submission

from exchange.config import ExchangeDefaults

logger = logging.getLogger(__name__)

DEFAULT_JUDGE_MODEL = ExchangeDefaults.JUDGE_MODEL

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


IMAGE_PREFIX = "data:image/"


def _is_image_submission(work: str) -> bool:
    """Detect if a submission contains a base64-encoded image."""
    return bool(work) and work.startswith(IMAGE_PREFIX)


IMAGE_CRITERIA = [
    "Accuracy: Does the image match the prompt description?",
    "Composition: Is the layout balanced and visually appealing?",
    "Detail: Is there appropriate level of detail and clarity?",
    "Style: Is the artistic quality and style consistent?",
]


def _build_vision_messages(task: str, image_data: str,
                           criteria: list[str] | None = None) -> list[dict]:
    """Build messages for vision-based image scoring."""
    criteria = criteria or IMAGE_CRITERIA
    criteria_text = "\n".join(f"- {c}" for c in criteria)

    system_prompt = (
        "You are a strict art director scoring AI-generated images for "
        "a competitive marketplace. Rate the image 1-10.\n\n"
        f"Scoring criteria:\n{criteria_text}\n\n"
        "Scoring guide — be demanding, use the FULL range:\n"
        "  1-3: Fails the prompt. Wrong subject, incoherent, or broken.\n"
        "  4-5: Recognizable attempt but poor quality, missing key elements, "
        "or generic/bland output.\n"
        "  6: Adequate. Gets the basics right but nothing impressive.\n"
        "  7: Good. Professional quality, all elements present, solid execution.\n"
        "  8: Very good. Strong composition, mood, and detail. "
        "Minor imperfections only.\n"
        "  9: Excellent. Striking image that exceeds expectations. "
        "Would stop someone scrolling.\n"
        "  10: Masterwork. Gallery-quality, emotionally powerful, technically flawless.\n\n"
        "Penalize heavily: wrong subject, missing requested elements, "
        "AI artifacts (extra fingers, melted text), flat/generic compositions.\n"
        "Reward: accurate prompt interpretation, strong lighting, emotional impact, "
        "creative interpretation, fine detail.\n\n"
        "Respond with ONLY valid JSON:\n"
        '{"score": <1-10>, "feedback": "<1-2 sentence feedback>"}'
    )

    user_content = [
        {
            "type": "text",
            "text": f"Task prompt: {task}\n\nScore the generated image below:",
        },
        {
            "type": "image_url",
            "image_url": {"url": image_data},
        },
    ]

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


class Judge:
    def __init__(self, client: OpenAI | None = None,
                 model: str = DEFAULT_JUDGE_MODEL):
        self._client = client or OpenAI()
        self._model = model

    def score_submission(self, task: str, submission: Submission,
                         quality_criteria: list[str] | None = None) -> dict:
        """Score a single submission. Returns {score: int, feedback: str}.

        Automatically detects image submissions and uses vision scoring.
        If quality_criteria is provided, uses those instead of defaults.
        """
        if _is_image_submission(submission.work):
            return self._score_image(task, submission.work, quality_criteria)

        # Text scoring (existing behavior)
        criteria = quality_criteria or DEFAULT_CRITERIA
        system_prompt = _build_judge_prompt(criteria)
        work = _truncate(submission.work)
        prompt = f"Task: {task}\n\nSubmission:\n{work}"

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

    def _score_image(self, task: str, image_data: str,
                     quality_criteria: list[str] | None = None) -> dict:
        """Score an image submission using vision."""
        messages = _build_vision_messages(task, image_data, quality_criteria)
        vision_model = "gpt-4o"

        try:
            resp = self._client.chat.completions.create(
                model=vision_model,
                max_completion_tokens=256,
                messages=messages,
            )
            result = parse_json(resp.choices[0].message.content)
            return {
                "score": _clamp_score(result.get("score")),
                "feedback": str(result.get("feedback", "")),
            }
        except Exception as e:
            logger.error(f"Vision judge scoring failed: {e}")
            return {"score": 1, "feedback": f"Vision judge error: {e}"}

    def score_batch(self, task: str,
                    submissions: dict[str, Submission],
                    quality_criteria: list[str] | None = None) -> dict[str, dict]:
        """Score multiple submissions. Returns {agent_id: {score, feedback}}."""
        criteria = quality_criteria or DEFAULT_CRITERIA
        system_prompt = _build_judge_prompt(criteria, batch=True)

        parts = [f"Task: {task}\n"]
        for agent_id, sub in submissions.items():
            work = _truncate(sub.work)
            parts.append(f"## {agent_id}\n{work}\n")

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
