import argparse
import re
import sys
import threading
import time
import unicodedata
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from .config import LANGUAGES, resolve


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "job"


def _new_out_dir(person: str, name: str) -> Path:
    """Distinct folder per run, so parallel runs and reruns never overwrite each other."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("outputs") / person / f"{_slug(name)}-{stamp}-{uuid.uuid4().hex[:6]}"


def _job_path(person_dir: Path, name: str) -> Path:
    """File name only: looked up in input/<person>/job_descriptions/. The .md extension is optional."""
    return person_dir / "job_descriptions" / (name if Path(name).suffix else f"{name}.md")


def _clock(seconds: float) -> str:
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def _fail(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.exit(1)


def _list_roles(person_dir: Path) -> list[str]:
    return sorted(f.stem for f in (person_dir / "job_profiles").glob("*.md"))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="resume-tailor", description="Tailored resume for one job or one role, from profile_truth.md.")
    p.add_argument("--person", required=True, help="Folder name under input/")
    p.add_argument("--job", nargs="+", help="One or more file names in input/<person>/job_descriptions/ (.md optional). Default: input/<person>/job_desc.md")
    p.add_argument("--role", help="Target role: input/<person>/job_profiles/<role>.md (e.g. devops, fullstack). With --job, the role focuses the resume for those jobs")
    p.add_argument("--all", action="store_true", help="One resume per role in input/<person>/job_profiles/")
    p.add_argument("--list-roles", action="store_true", help="List available roles and exit")
    p.add_argument("--workers", type=int, default=4, help="Resumes generated in parallel (default 4)")
    p.add_argument("--lang", default="pt-BR", help="pt-BR (default) or en")
    p.add_argument("--refine", action="store_true", help="Enable the revision loop (env: RESUME_REFINE)")
    p.add_argument("--target", type=float, help="Target rating 1-10 (env: RESUME_TARGET, default 8.0)")
    p.add_argument("--max-revisions", type=int, help="Revision limit (env: RESUME_MAX_REVISIONS, default 1)")
    args = p.parse_args(argv)

    if args.workers < 1:
        _fail("workers must be >= 1")
    if args.all and (args.job or args.role):
        _fail("--all cannot be combined with --job or --role")
    if args.lang not in LANGUAGES:
        _fail(f"Unsupported language '{args.lang}'. Supported: {', '.join(LANGUAGES)}")
    try:
        cfg = resolve(args.refine, args.target, args.max_revisions)
    except ValueError as exc:
        _fail(str(exc))

    person_dir = Path("input") / args.person
    roles = _list_roles(person_dir)
    if args.list_roles:
        print("\n".join(roles) if roles else f"No roles in {person_dir / 'job_profiles'}")
        return

    truth_path = person_dir / "profile_truth.md"
    if args.all:
        if not roles:
            _fail(f"No roles in {person_dir / 'job_profiles'}")
        job_paths = [person_dir / "job_profiles" / f"{r}.md" for r in roles]
    else:
        job_paths = [_job_path(person_dir, j) for j in args.job] if args.job else None
    role_path = None
    if args.role:
        role_path = person_dir / "job_profiles" / f"{args.role}.md"
        if not role_path.is_file():
            _fail(f"Role '{args.role}' not found. Available: {', '.join(roles) or 'none'}")
        if job_paths is None:  # role alone: the role file is the job description
            job_paths, role_path = [role_path], None
    elif job_paths is None:
        job_paths = [person_dir / "job_desc.md"]
    for path in [truth_path, *job_paths]:
        if not path.is_file():
            _fail(f"File not found: {path}")

    # Imported late: checks above must work without the SDK or a login.
    from .agent import ask, usage
    from .pipeline import run
    from .render import render

    truth = truth_path.read_text(encoding="utf-8")
    role_text = role_path.read_text(encoding="utf-8") if role_path else None
    print_lock = threading.Lock()

    def generate(job_path: Path) -> str | None:
        """Returns the job name on failure. Output lines are prefixed so parallel runs stay readable."""
        out_dir = _new_out_dir(args.person, job_path.stem)
        started = time.monotonic()

        def log(message: str) -> None:
            with print_lock:
                print(f"[{job_path.stem}] [{_clock(time.monotonic() - started)}] {message}...", file=sys.stderr, flush=True)

        lines: list[tuple[str, bool]] = []
        failed = False
        try:
            job_text = job_path.read_text(encoding="utf-8")
            if role_text:
                job_text = (f"### Target role profile ({args.role}): position the resume as this role\n{role_text}\n\n"
                            f"### Specific job posting: match its requirements within that role\n{job_text}")
            result = run(truth, job_text, args.lang, cfg, out_dir, ask, log)
            lines.append((result.refinement.summary(), False))
            try:
                lines.append((f"PDF: {render(result.resume, out_dir, args.lang)}", False))
            except RuntimeError as exc:
                lines.append((f"[WARN] {exc}", True))
            lines.append((f"Output: {out_dir}", False))
            lines.append((f"Time: {_clock(time.monotonic() - started)}", False))
        except Exception as exc:  # SDK/login/network/invalid JSON: partial files stay in out_dir
            failed = True
            lines.append((f"[ERROR] {type(exc).__name__}: {exc}\n  If this is a login problem, run `claude` and use /login. Partial output (if any): {out_dir}", True))
        with print_lock:
            for text, is_err in lines:
                print(f"[{job_path.stem}] {text}", file=sys.stderr if is_err else sys.stdout)
        return job_path.stem if failed else None

    total_start = time.monotonic()
    with ThreadPoolExecutor(max_workers=min(args.workers, len(job_paths))) as pool:
        failed = [name for name in pool.map(generate, job_paths) if name]
    print(usage.summary())
    print(f"Total time: {_clock(time.monotonic() - total_start)}")
    if failed:
        _fail(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
