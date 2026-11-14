import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

_RATING_RE = re.compile(r"FINAL_RATING\W*(\d{1,2}(?:[.,]\d+)?)", re.IGNORECASE)

_STOP_REASONS = {
    "target_reached": "target reached",
    "no_improvement": "last revision did not improve the rating",
    "max_revisions": "revision limit reached",
    "unrated": "rating could not be read from the evaluation",
    "single_evaluation": "refinement disabled: single evaluation",
    "draft_only": "refinement disabled: the rating is of the draft, before the editor pass",
}


def parse_rating(text: Optional[str]) -> Optional[float]:
    """Last FINAL_RATING in the text, or None if absent or outside the 1-10 scale."""
    matches = _RATING_RE.findall(text or "")
    if not matches:
        return None
    rating = float(matches[-1].replace(",", "."))
    return rating if 1 <= rating <= 10 else None


@dataclass
class RefinementResult:
    ratings: list
    stop_reason: str
    best_rating: Optional[float]
    final_feedback: str
    restored: bool
    target: float

    @property
    def reached_target(self) -> bool:
        return self.best_rating is not None and self.best_rating >= self.target

    def summary(self) -> str:
        ratings = ", ".join("unreadable" if r is None else str(r) for r in self.ratings)
        lines = [
            f"Target rating: {self.target}",
            f"Rating per evaluation: {ratings}",
            f"Final rating: {'unknown' if self.best_rating is None else self.best_rating}",
            f"Target reached: {'yes' if self.reached_target else 'no'}",
            f"Stopped because: {_STOP_REASONS[self.stop_reason]}",
        ]
        if self.restored:
            lines.append("The best-rated version was restored as the final resume.")
        return "\n".join(lines)


def refine(
    evaluate: Callable[[], str],
    revise: Callable[[str], None],
    snapshot: Callable[[], Any],
    restore: Callable[[Any], None],
    target: float,
    max_revisions: int,
    enabled: bool = True,
) -> RefinementResult:
    """Evaluate, then (if enabled) revise until target, no improvement, or revision limit.

    The best-rated version is always the one kept. With enabled=False it evaluates once.
    """
    ratings, best_rating, best_state, best_feedback = [], None, None, ""
    current_is_best, revisions = False, 0

    while True:
        feedback = evaluate()
        rating = parse_rating(feedback)
        ratings.append(rating)

        if rating is None:
            stop_reason = "unrated"
            best_feedback = best_feedback or feedback
            break

        improved = best_rating is None or rating > best_rating
        current_is_best = improved
        if improved:
            best_rating, best_state, best_feedback = rating, snapshot(), feedback

        if rating >= target:
            stop_reason = "target_reached"
            break
        if not enabled:
            stop_reason = "single_evaluation"
            break
        if not improved:
            stop_reason = "no_improvement"
            break
        if revisions >= max_revisions:
            stop_reason = "max_revisions"
            break

        revise(feedback)
        revisions += 1
        current_is_best = False

    restored = best_state is not None and not current_is_best
    if restored:
        restore(best_state)
    return RefinementResult(ratings, stop_reason, best_rating, best_feedback, restored, target)
