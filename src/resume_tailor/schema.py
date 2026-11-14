import json
import re

REQUIRED = ("basics", "work", "education", "skills", "certificates")
BASICS_REQUIRED = ("name", "email", "summary")
WORK_REQUIRED = ("name", "position", "startDate", "endDate", "highlights")

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class InvalidResume(ValueError):
    pass


def extract_json(text: str) -> dict:
    """Parses the resume JSON from a model reply (fenced block, or the outermost braces)."""
    matches = _FENCE_RE.findall(text or "")
    candidate = matches[-1] if matches else None
    if candidate is None:
        start, end = (text or "").find("{"), (text or "").rfind("}")
        if start == -1 or end <= start:
            raise InvalidResume("no JSON object found in the reply")
        candidate = text[start:end + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise InvalidResume(f"invalid JSON: {exc}") from exc
    validate(data)
    return data


def validate(data: dict) -> None:
    if not isinstance(data, dict):
        raise InvalidResume("resume must be a JSON object")
    for key in REQUIRED:
        if key not in data:
            raise InvalidResume(f"missing section: {key}")
    for key in BASICS_REQUIRED:
        if not str(data["basics"].get(key, "")).strip():
            raise InvalidResume(f"basics.{key} is empty")
    if not data["work"]:
        raise InvalidResume("work is empty")
    for i, job in enumerate(data["work"]):
        for key in WORK_REQUIRED:
            if key not in job:
                raise InvalidResume(f"work[{i}].{key} missing")
