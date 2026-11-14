import os
from dataclasses import dataclass

LANGUAGES = ("pt-BR", "en")
DEFAULT_TARGET = 8.0
DEFAULT_MAX_REVISIONS = 1
DEFAULT_REVIEW_MODEL = "sonnet"  # hiring-manager steps only read and rate: a cheaper model is enough


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    refine: bool
    target: float
    max_revisions: int
    model: str | None
    review_model: str | None = DEFAULT_REVIEW_MODEL


def resolve(refine: bool | None, target: float | None, max_revisions: int | None) -> Config:
    """Precedence: CLI flag, then environment variable, then default."""
    cfg = Config(
        refine=refine if refine else _env_bool("RESUME_REFINE"),
        target=target if target is not None else float(os.getenv("RESUME_TARGET") or DEFAULT_TARGET),
        max_revisions=max_revisions if max_revisions is not None
        else int(os.getenv("RESUME_MAX_REVISIONS") or DEFAULT_MAX_REVISIONS),
        model=os.getenv("RESUME_MODEL") or None,
        review_model=os.getenv("RESUME_REVIEW_MODEL") or DEFAULT_REVIEW_MODEL,
    )
    if not 1 <= cfg.target <= 10:
        raise ValueError("target must be between 1 and 10")
    if cfg.max_revisions < 0:
        raise ValueError("max-revisions must be >= 0")
    return cfg
