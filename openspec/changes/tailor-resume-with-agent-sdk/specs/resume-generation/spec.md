## ADDED Requirements

### Requirement: Generate tailored resume from truth file and job description
The system SHALL generate a resume for one job from `input/<person>/profile_truth.md` and a job description file, and SHALL NOT require any other input.

#### Scenario: Successful run
- **WHEN** the user runs the tool with a person name and a job description path
- **THEN** the system writes `resume.json`, a LaTeX file and a PDF under `outputs/<person>/<job-slug>/`

#### Scenario: Missing input
- **WHEN** `profile_truth.md` or the job description file does not exist
- **THEN** the system exits with a non-zero code and names the missing file, without calling the model

### Requirement: No fabrication
The system SHALL only state facts that are supported by `profile_truth.md`, and SHALL apply its corrections and exclusions.

#### Scenario: Unsupported claim
- **WHEN** the job description asks for a skill that `profile_truth.md` does not support
- **THEN** the resume does not claim that skill, and the gap is listed in the rating report

### Requirement: Output language
The system SHALL write the resume in the language selected by the user, `pt-BR` (default) or `en`.

#### Scenario: English selected
- **WHEN** the user passes `--lang en`
- **THEN** all resume text is in English, even if the sources are in Portuguese

#### Scenario: Unsupported language
- **WHEN** the user passes a language other than `pt-BR` or `en`
- **THEN** the system exits with a non-zero code and lists the supported languages

### Requirement: Agent pipeline
The system SHALL run these steps in order: Career Strategist drafts the resume, Hiring Manager evaluates it, Resume Editor produces the final resume and coverage audit, Job Applicant writes a report. It SHALL NOT produce interview preparation material.

#### Scenario: Default run
- **WHEN** a run finishes without the refinement loop
- **THEN** the output folder contains `resume.json`, the PDF, `coverage_review.md` and `rating_report.md`

### Requirement: Coverage audit
The Resume Editor SHALL report, for each position in the resume, the source themes from `profile_truth.md`, the final bullets that cover them, and any omissions.

#### Scenario: Omitted experience
- **WHEN** a documented theme of a position is not in the final resume
- **THEN** `coverage_review.md` lists it as an omission for that position

### Requirement: Valid output
The system SHALL validate the resume JSON against the expected structure before rendering, and SHALL keep the last valid version if a model reply is invalid.

#### Scenario: Invalid JSON from a model
- **WHEN** an agent returns JSON that does not parse or lacks required sections
- **THEN** the system does not overwrite the last valid `resume.json` and reports the error

### Requirement: Subscription authentication
The system SHALL use the user's Claude subscription session and SHALL NOT require an API key.

#### Scenario: Not logged in
- **WHEN** no Claude session is available
- **THEN** the system exits with a clear message asking the user to log in
