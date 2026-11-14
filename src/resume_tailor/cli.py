import argparse
import re
import sys
import unicodedata
from pathlib import Path

from .config import LANGUAGES, resolve


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "job"


def _fail(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="resume-tailor", description="Tailored resume for one job, from profile_truth.md.")
    p.add_argument("--person", required=True, help="Folder name under input/")
    p.add_argument("--job", help="Job description file (default: input/<person>/job_desc.md)")
    p.add_argument("--lang", default="pt-BR", help="pt-BR (default) or en")
    p.add_argument("--refine", action="store_true", help="Enable the revision loop (env: RESUME_REFINE)")
    p.add_argument("--target", type=float, help="Target rating 1-10 (env: RESUME_TARGET, default 8.0)")
    p.add_argument("--max-revisions", type=int, help="Revision limit (env: RESUME_MAX_REVISIONS, default 1)")
    args = p.parse_args(argv)

    if args.lang not in LANGUAGES:
        _fail(f"Unsupported language '{args.lang}'. Supported: {', '.join(LANGUAGES)}")
    try:
        cfg = resolve(args.refine, args.target, args.max_revisions)
    except ValueError as exc:
        _fail(str(exc))

    truth_path = Path("input") / args.person / "profile_truth.md"
    job_path = Path(args.job) if args.job else Path("input") / args.person / "job_desc.md"
    for path in (truth_path, job_path):
        if not path.is_file():
            _fail(f"File not found: {path}")

    # Imported late: checks above must work without the SDK or a login.
    from .agent import ask, usage
    from .pipeline import run
    from .render import render

    out_dir = Path("outputs") / args.person / _slug(job_path.stem)
    try:
        result = run(
            truth_path.read_text(encoding="utf-8"), job_path.read_text(encoding="utf-8"),
            args.lang, cfg, out_dir, ask,
        )
    except Exception as exc:  # SDK/login/network/invalid JSON: partial files stay in out_dir
        _fail(f"{type(exc).__name__}: {exc}\n  If this is a login problem, run `claude` and use /login. Partial output (if any): {out_dir}")

    print(result.refinement.summary())
    print(usage.summary())
    try:
        pdf = render(result.resume, out_dir)
        print(f"PDF: {pdf}")
    except RuntimeError as exc:
        print(f"[WARN] {exc}", file=sys.stderr)
    print(f"Output: {out_dir}")


if __name__ == "__main__":
    main()
