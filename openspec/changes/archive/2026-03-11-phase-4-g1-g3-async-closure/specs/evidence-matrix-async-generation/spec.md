## ADDED Requirements

### Requirement: Evidence Matrix generation returns handle immediately
The system SHALL return a `202 Accepted` response with a `JobHandle` when Evidence Matrix generation is requested, without blocking on generation completion.

#### Scenario: Generation request accepted
- **WHEN** user requests Evidence Matrix generation for a system
- **THEN** system SHALL return `202` status with `workflow_id` in response body within 500ms

### Requirement: Evidence Matrix generation completes asynchronously
The system SHALL execute Evidence Matrix generation in a background task and persist claims and claim-evidence links to the database.

#### Scenario: Background task creates Claim records
- **WHEN** Evidence Matrix generation background task completes successfully
- **THEN** system SHALL create `Claim` records with `system_id`, `claim_text`, `claim_type`, `version`, and audit fields

#### Scenario: Background task creates ClaimEvidenceLink records
- **WHEN** Evidence Matrix generation background task completes successfully
- **THEN** system SHALL create `ClaimEvidenceLink` records linking claims to analysis runs with `claim_id`, `analysis_run_id`, `link_type`, and audit fields

#### Scenario: Background task handles executor placeholder
- **WHEN** Evidence Matrix generation calls executor (placeholder implementation)
- **THEN** system SHALL accept mock claim data and persist it as valid Claim and ClaimEvidenceLink records

### Requirement: Evidence Matrix generation broadcasts task events
The system SHALL append workflow events and broadcast task status via WebSocket during Evidence Matrix generation.

#### Scenario: Task started event
- **WHEN** Evidence Matrix generation background task starts
- **THEN** system SHALL append `TASK_STARTED` workflow event and broadcast via WebSocket

#### Scenario: Task succeeded event
- **WHEN** Evidence Matrix generation background task completes successfully
- **THEN** system SHALL append `TASK_SUCCEEDED` workflow event and broadcast via WebSocket

#### Scenario: Task failed event
- **WHEN** Evidence Matrix generation background task fails
- **THEN** system SHALL append `TASK_FAILED` workflow event with error message and broadcast via WebSocket

### Requirement: Evidence Matrix generation supports versioning
The system SHALL assign a version number to each generated set of claims, starting from 1 and incrementing for subsequent generations.

#### Scenario: First Evidence Matrix version
- **WHEN** Evidence Matrix is generated for a system with no existing claims
- **THEN** system SHALL create Claim records with `version = 1`

#### Scenario: Subsequent Evidence Matrix version
- **WHEN** Evidence Matrix is generated for a system with existing claims
- **THEN** system SHALL create Claim records with `version = max(existing_versions) + 1`

### Requirement: Evidence Matrix uses existing tables
The system SHALL represent Evidence Matrix using `claims` and `claim_evidence_links` tables, without introducing a new `evidence_matrices` table.

#### Scenario: No new table created
- **WHEN** Evidence Matrix generation completes
- **THEN** system SHALL have created records only in `claims` and `claim_evidence_links` tables
