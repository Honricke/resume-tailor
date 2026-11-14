## Why

The existing `resume-transform` tool tailors a resume per job, but it depends on CrewAI and paid LLM API keys, and it carries many features that are no longer needed (ingest, role batches, multi-provider, LinkedIn auth, interview prep). We want a small tool that runs on a Claude subscription and does one thing: generate a tailored resume for one specific job from the candidate's `profile_truth.md` and a job description.

## What Changes

- New standalone project `resume-tailor` (Python) built on the Claude Agent SDK, using the user's Claude subscription login (no API key).
- Inputs are only `input/<person>/profile_truth.md` and a job description file. No base `resume.json`, no PDF input.
- Four-agent pipeline: Career Strategist, Hiring Manager, Resume Editor, Job Applicant. The Interview Coach is not included.
- The Resume Editor produces a per-position coverage audit.
- Output language is selectable (`pt-BR` or `en`).
- Optional, configurable refinement loop (evaluate, revise, repeat) that is off by default.
- Rendering: `resume.json` to LaTeX to PDF, ported from `resume-transform`.
- Not carried over: ingest, job-profile batches (`--all`, `--role`), best-resume matcher, multi-provider and Bedrock support, LinkedIn auth, PDF comparison, page padding, interview prep, the method docs folder.

## Capabilities

### New Capabilities
- `resume-generation`: generate a tailored resume (JSON, LaTeX, PDF), coverage audit and rating report from `profile_truth.md` and a job description, in the chosen language.
- `refinement-loop`: optional rating-driven revision cycle with configurable target and revision limit.

### Modified Capabilities
None. This is a new project.

## Impact

- New directory `job-hub/resume-tailor/`. The old `resume-transform` repo is not changed.
- Dependencies: `claude-agent-sdk`, a local LaTeX install (for PDF), and a logged-in Claude Code session.
- Reads `profile_truth.md` from `input/<person>/`. This file may contain private data, so `input/` and `outputs/` must be git-ignored.
