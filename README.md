# resume-tailor

Generates a tailored, one-page, ATS-friendly resume (PDF) for a specific job. It uses the candidate's `profile_truth.md` and a job description. It runs on the [Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview) with your Claude subscription login. No API key is needed.

## How it works

Each resume goes through a small pipeline of model calls (no tools, one turn each):

1. **Strategist** writes the first resume (JSON) from `profile_truth.md` and the job description.
2. **Hiring Manager** rates the draft (1-10) and gives feedback.
3. **Editor** produces the final resume and a per-position coverage audit.
4. **Refine loop** (optional): evaluate, revise, repeat until the target rating, no improvement, or the revision limit. The best-rated version is always kept.
5. **Fit check**: if the PDF has more than one page, the Editor condenses it. Rendering trims bullets as a last resort.

The resume only uses facts from `profile_truth.md`.

## Requirements

- Python 3.10+ (`.python-version` pins 3.12)
- [uv](https://docs.astral.sh/uv/)
- Claude Code installed and logged in (run `claude`, then `/login`)

## Setup

```bash
uv sync
```

## Input layout

```
input/
  <person>/
    profile_truth.md      # required: full verified career data
    job_desc.md           # default job description
    job_descriptions/     # job postings, passed to --job by file name
      vaga1.md
    job_profiles/         # optional: one file per target role
      devops.md
      fullstack.md
```

`input/` and `outputs/` are git-ignored because they hold private data.

## Usage

```bash
# Default job description: input/<person>/job_desc.md
uv run resume-tailor --person henrique

# One or more files from input/<person>/job_descriptions/ (name only, .md optional)
uv run resume-tailor --person henrique --job vaga1.md vaga2.md

# One role from job_profiles/
uv run resume-tailor --person henrique --role devops

# A role applied to specific jobs: the role sets the identity, the job sets the requirements
uv run resume-tailor --person henrique --role devops --job vaga1 vaga2

# One resume per role
uv run resume-tailor --person henrique --all

# List roles
uv run resume-tailor --person henrique --list-roles

# English output, with the refine loop
uv run resume-tailor --person henrique --lang en --refine --target 9 --max-revisions 2
```

### Options

| Option | Description |
| --- | --- |
| `--person` | Folder name under `input/` (required) |
| `--job NAME...` | File names in `input/<person>/job_descriptions/` (`.md` optional) |
| `--role NAME` | Role file `input/<person>/job_profiles/<NAME>.md`. Alone: the role file is the job description. With `--job`: the role focuses the resume for those jobs |
| `--all` | One resume per role in `job_profiles/` |
| `--list-roles` | List available roles and exit |
| `--workers N` | Resumes generated in parallel (default 4) |
| `--lang` | `pt-BR` (default) or `en` |
| `--refine` | Enable the revision loop |
| `--target` | Target rating, 1-10 (default 8.5) |
| `--max-revisions` | Revision limit (default 1) |

`--role` and `--job` can be combined. `--all` cannot be combined with either.

### Environment variables

CLI flags win over environment variables, which win over defaults.

| Variable | Default | Meaning |
| --- | --- | --- |
| `RESUME_REFINE` | off | Enable the refine loop (`1`, `true`, `yes`, `on`) |
| `RESUME_TARGET` | `8.5` | Target rating |
| `RESUME_MAX_REVISIONS` | `1` | Revision limit |
| `RESUME_MODEL` | `sonnet` | Model for the Strategist and Editor |
| `RESUME_REVIEW_MODEL` | `sonnet` | Model for the Hiring Manager |

## Output

Each run writes to its own folder, so reruns and parallel runs never overwrite each other:

```
outputs/<person>/<job>-<timestamp>-<id>/
  resume.json          # structured resume
  resume.pdf           # rendered resume (reportlab, one A4 page)
  coverage_review.md   # per-position coverage audit
  rating_report.md     # ratings, last evaluation, audit
```

The CLI also prints the ratings and a usage summary (calls, tokens, API-equivalent cost).

## Project layout

```
src/resume_tailor/
  cli.py        # arguments, file checks, parallel runs
  config.py     # CLI / env / default resolution
  pipeline.py   # Strategist -> Hiring Manager -> Editor -> fit check
  refine.py     # rating parser and refine loop
  prompts.py    # agent prompts
  agent.py      # Claude Agent SDK call and usage tracking
  schema.py     # resume JSON extraction and validation
  render.py     # JSON -> PDF
tests/          # pytest
openspec/       # specs and change proposals
```

## Tests

```bash
uv run pytest
```
