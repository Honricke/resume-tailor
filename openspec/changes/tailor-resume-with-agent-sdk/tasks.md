## 1. Project setup
- [x] 1.1 Create Python project (`pyproject.toml`, venv, `claude-agent-sdk` dependency) and `.gitignore` for `input/`, `outputs/`, `.env`
- [x] 1.2 Add CLI entry point with `--person`, `--job`, `--lang`, `--refine`, `--target`, `--max-revisions`
- [x] 1.3 Validate inputs and language before any model call; check Claude login and LaTeX availability

## 2. Agent layer
- [x] 2.1 Add a helper that runs one agent step through the Agent SDK with tools disabled and returns text
- [x] 2.2 Port and trim the four prompts (strategist, hiring manager, editor, applicant); drop interview coach
- [x] 2.3 Add JSON extraction and schema validation with one retry on invalid output

## 3. Pipeline
- [x] 3.1 Implement Strategist, Hiring Manager, Editor sequence reading only `profile_truth.md` and the job description
- [x] 3.2 Save `coverage_review.md` from the Editor output
- [x] 3.3 Implement Job Applicant step and write `rating_report.md`

## 4. Refinement loop
- [x] 4.1 Port `refine()` with rating parsing and stop reasons
- [x] 4.2 Wire flags and environment variables with flag priority; off by default
- [x] 4.3 Snapshot and restore best-rated version

## 5. Rendering
- [x] 5.1 Port JSON to LaTeX to PDF (`generator.py`, `latex_utils.py`) and render the final JSON after the loop

## 6. Verification
- [x] 6.1 Unit tests: rating parsing, `refine()` stop conditions, config precedence, JSON validation
- [x] 6.2 End-to-end run with `input/henrique/profile_truth.md` and a job description; check all output files
- [x] 6.3 Run with `--refine` and confirm the stop reason in `rating_report.md`
