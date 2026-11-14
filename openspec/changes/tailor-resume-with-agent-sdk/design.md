## Context

See proposal.md for motivation. Constraints: Python, Claude Agent SDK, Claude subscription (no API key), `profile_truth.md` as the only fact source. The LaTeX template lives in code in the old repo (`resume/generator.py`, `resume/latex_utils.py`) and is reused.

## Goals / Non-Goals

**Goals:** one command, one job, one resume; small code base; optional refinement.
**Non-Goals:** batches, resume ingest, other LLM providers, interview prep, job search, tracking.

## Decisions

1. **Claude Agent SDK, one `query()` call per agent step.** Each agent is a system prompt plus an input, run in sequence by plain Python. Alternative: SDK subagents inside one session. Rejected: harder to control order, to snapshot state and to run the loop.
2. **Agents return text; Python writes files.** Strategist and Editor return the resume JSON in a fenced block; code parses, validates and saves it. Tools are disabled for the agents. Alternative: custom tools to save JSON (as the old repo did). Rejected: more surface, and validation belongs in code anyway.
3. **Fact source is only `profile_truth.md`.** The Strategist builds the first JSON from it using the schema from the old `JSON_STRUCTURE`. The base `resume.json` and the matcher are removed.
4. **Refinement as a small pure function** `refine(evaluate, revise, snapshot, restore, target, max_revisions)`, ported from the old `refinement.py`. Rating is read from a final `FINAL_RATING: <n>` line.
5. **Config precedence:** CLI flag, then environment variable (`RESUME_REFINE`, `RESUME_TARGET`, `RESUME_MAX_REVISIONS`), then default.
6. **Layout:** `input/<person>/{profile_truth.md,job_desc.md}`, `outputs/<person>/<job-slug>/{resume.json,resume.tex,resume.pdf,coverage_review.md,rating_report.md}`. Job slug comes from the job title.
7. **Prompts ported and trimmed** from `prompts/job_application_prompts.py`: strategist, hiring manager, editor, applicant. Interview coach prompt dropped.
8. **Model:** SDK default for the subscription; overridable with `RESUME_MODEL`.

## Risks / Trade-offs

- Subscription usage limits can stop long refinement runs → loop is off by default, max revisions defaults to 3, partial results stay on disk.
- Model returns invalid JSON → validate, retry once with the error message, then keep the last valid file.
- Subscription use through the SDK follows Anthropic's current terms for automated use → check the terms before sharing the tool with others; personal use only for now.
- LaTeX not installed → fail early with a clear message, still save `resume.json`.
- `profile_truth.md` has private data → git-ignore `input/` and `outputs/`; never print its content in logs.

## Open Questions

- Exact `--lang` default if `PERSON` has a language preference file (assume `pt-BR` for now).
