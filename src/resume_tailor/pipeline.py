import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import prompts
from .config import Config
from .render import page_count
from .refine import RefinementResult, parse_rating, refine
from .schema import InvalidResume, extract_json

MAX_FIT_ATTEMPTS = 1
Ask = Callable[[str, str, str | None], str]
_AUDIT_RE = re.compile(r"^##\s*Coverage audit.*", re.IGNORECASE | re.MULTILINE | re.DOTALL)


@dataclass
class Result:
    out_dir: Path
    refinement: RefinementResult
    resume: dict


def _ask_resume(ask: Ask, system: str, prompt: str, model: str | None) -> tuple[dict, str]:
    """Asks for a resume JSON. Retries once, telling the model what was wrong."""
    reply = ask(system, prompt, model)
    try:
        return extract_json(reply), reply
    except InvalidResume as exc:
        retry = f"{prompt}\n\nYour previous reply was rejected: {exc}. Reply again, following the output format exactly."
        reply = ask(system, retry, model)
        return extract_json(reply), reply  # second failure propagates; last valid file stays on disk


def _audit(reply: str) -> str:
    match = _AUDIT_RE.search(reply)
    return match.group(0).strip() if match else "## Coverage audit\n\n(The editor did not return an audit.)"


def _report(refinement: RefinementResult, audit: str) -> str:
    """Built locally (no model call): measured ratings, last evaluation, coverage audit."""
    parts = [refinement.summary(), "## Hiring manager's last evaluation\n\n" + refinement.final_feedback.strip()]
    if audit:
        parts.append(audit)
    return "\n\n".join(parts) + "\n"


def run(
    truth: str, job_description: str, language: str, cfg: Config, out_dir: Path, ask: Ask,
) -> Result:
    out_dir.mkdir(parents=True, exist_ok=True)
    resume_path = out_dir / "resume.json"
    audit_path = out_dir / "coverage_review.md"
    review_model = cfg.review_model or cfg.model

    def save(resume: dict, audit: str) -> None:
        resume_path.write_text(json.dumps(resume, ensure_ascii=False, indent=2), encoding="utf-8")
        if audit:
            audit_path.write_text(audit + "\n", encoding="utf-8")

    state = {"resume": None, "audit": ""}

    def evaluate() -> str:
        return ask(
            prompts.HIRING_MANAGER_SYSTEM,
            prompts.hiring_manager_prompt(job_description, state["resume"], truth),
            review_model,
        )

    def revise(feedback: str, with_audit: bool = True) -> None:
        resume, reply = _ask_resume(
            ask, prompts.EDITOR_SYSTEM,
            prompts.editor_prompt(job_description, state["resume"], truth, feedback, language, audit=with_audit),
            cfg.model,
        )
        state["resume"], state["audit"] = resume, _audit(reply) if with_audit else state["audit"]
        save(resume, state["audit"])

    # 1. Strategist: first version from profile_truth.md
    state["resume"], _ = _ask_resume(
        ask, prompts.STRATEGIST_SYSTEM,
        prompts.strategist_prompt(job_description, truth, language), cfg.model,
    )
    save(state["resume"], "")

    # 2-3. Hiring Manager evaluates the draft, Editor produces the final resume
    draft_feedback = evaluate()
    revise(draft_feedback, with_audit=cfg.refine)

    # 4. Refine loop only when enabled; otherwise the draft rating is the only one (saves two calls)
    if cfg.refine:
        refinement = refine(
            evaluate=evaluate,
            revise=revise,
            snapshot=lambda: (state["resume"], state["audit"]),
            restore=lambda s: (state.update(resume=s[0], audit=s[1]), save(s[0], s[1])),
            target=cfg.target,
            max_revisions=cfg.max_revisions,
            enabled=True,
        )
    else:
        rating = parse_rating(draft_feedback)
        refinement = RefinementResult([rating], "draft_only", rating, draft_feedback, False, cfg.target)

    # 5. One-page limit: ask the editor to condense until the PDF fits (render trims as a last resort)
    for _ in range(MAX_FIT_ATTEMPTS):
        pages = page_count(state["resume"], language)
        if pages <= 1:
            break
        revise(
            f"LAYOUT: the rendered resume has {pages} pages. It MUST fit ONE A4 page. "
            "Cut the least relevant bullets, shorten the summary and merge similar bullets. "
            "Keep every position and the most vacancy-relevant evidence. Do not add content.",
            with_audit=False,
        )

    (out_dir / "rating_report.md").write_text(_report(refinement, state["audit"]), encoding="utf-8")
    return Result(out_dir, refinement, state["resume"])
