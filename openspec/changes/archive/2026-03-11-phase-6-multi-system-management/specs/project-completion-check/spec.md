## ADDED Requirements

### Requirement: ProjectDetail includes completion metrics
The `GET /projects/{id}` response (`ProjectDetail` schema) SHALL include two new fields: `completedSystemCount` (integer) and `introductionUnlocked` (boolean). These fields SHALL be computed at read time from the systems collection.

#### Scenario: Correct completed count
- **WHEN** a project has 5 systems, 3 with status `Chapter_Approved` and 2 with status `Section_Drafting`
- **THEN** `completedSystemCount` SHALL be `3`

#### Scenario: Zero completions
- **WHEN** a project has 2 systems, both with status `Draft`
- **THEN** `completedSystemCount` SHALL be `0` and `introductionUnlocked` SHALL be `false`

#### Scenario: Introduction unlock threshold
- **WHEN** `completedSystemCount` is exactly `3`
- **THEN** `introductionUnlocked` SHALL be `true`

#### Scenario: Below threshold
- **WHEN** `completedSystemCount` is `2`
- **THEN** `introductionUnlocked` SHALL be `false`

### Requirement: Completion check is idempotent and stateless
The completion metrics SHALL be computed purely from the current `systems` collection state. No persistent project-level state SHALL be written or cached for completion tracking.

#### Scenario: System reverts from approved
- **WHEN** a system's status changes from `Chapter_Approved` back to `Chapter_Review` (hypothetical future feature)
- **THEN** `completedSystemCount` SHALL decrease by 1 and `introductionUnlocked` SHALL update accordingly

#### Scenario: Concurrent reads during system advance
- **WHEN** two clients read `GET /projects/{id}` while a system is being advanced
- **THEN** both responses SHALL reflect a consistent snapshot (either pre-advance or post-advance count, never an intermediate state)

### Requirement: Completion logic resides in projects service
The completion computation (`completedSystemCount` and `introductionUnlocked`) SHALL be implemented in `backend/app/modules/projects/service.py`, not in `gates/service.py`. Gate service SHALL remain scoped to single-system gate evaluation.

#### Scenario: Gate service unchanged
- **WHEN** the completion check logic is deployed
- **THEN** `gates/service.py` SHALL have zero modifications related to project-level completion

### Requirement: Frontend displays introduction unlock status
The ProjectStats component SHALL visually indicate whether Introduction writing is unlocked. When locked, it SHALL show the remaining count needed (e.g., "1 more system needed"). When unlocked, it SHALL show an actionable indicator.

#### Scenario: Locked state display
- **WHEN** `introductionUnlocked` is `false` and `completedSystemCount` is `1`
- **THEN** ProjectStats SHALL display "2 more systems needed to unlock Introduction"

#### Scenario: Unlocked state display
- **WHEN** `introductionUnlocked` is `true`
- **THEN** ProjectStats SHALL display Introduction as available/unlocked
