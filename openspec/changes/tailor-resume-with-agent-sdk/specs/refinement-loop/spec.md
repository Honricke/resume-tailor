## ADDED Requirements

### Requirement: Refinement is optional
The system SHALL run the refinement loop only when the user enables it, and SHALL be disabled by default.

#### Scenario: Default
- **WHEN** the user does not enable refinement
- **THEN** the Hiring Manager evaluates once and no revision cycle runs

#### Scenario: Enabled
- **WHEN** the user passes `--refine`
- **THEN** the system repeats evaluate and revise until a stop condition is met

### Requirement: Configurable target and limit
The system SHALL accept a target rating (default 8.5, scale 1 to 10) and a maximum number of revisions (default 3), through CLI flags and environment variables, with flags taking priority.

#### Scenario: Custom values
- **WHEN** the user passes `--target 9 --max-revisions 5`
- **THEN** the loop stops at a rating of 9 or after 5 revisions, whichever comes first

### Requirement: Stop conditions
The loop SHALL stop when the target is reached, when a revision does not improve the rating, when the revision limit is reached, or when the rating cannot be read.

#### Scenario: No improvement
- **WHEN** a revision gets a rating equal to or lower than the previous one
- **THEN** the loop stops and the best-rated version is restored as the final resume

### Requirement: Rating report
The system SHALL record the rating of each evaluation, the stop reason and whether the target was reached in `rating_report.md`.

#### Scenario: Target not reached
- **WHEN** the loop ends below target
- **THEN** the report says so and lists the remaining gaps
