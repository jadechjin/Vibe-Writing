## ADDED Requirements

### Requirement: Outline generation returns handle immediately
The system SHALL return a `202 Accepted` response with a `JobHandle` when Outline generation is requested, without blocking on generation completion.

#### Scenario: Generation request accepted
- **WHEN** user requests Outline generation for a system
- **THEN** system SHALL return `202` status with `workflow_id` in response body within 500ms

### Requirement: Outline generation completes asynchronously
The system SHALL execute Outline generation in a background task and persist the result to the `outlines` table.

#### Scenario: Background task creates Outline record
- **WHEN** Outline generation background task completes successfully
- **THEN** system SHALL create an `Outline` record with `system_id`, `version`, `content_json`, and audit fields

#### Scenario: Background task handles executor placeholder
- **WHEN** Outline generation calls executor (placeholder implementation)
- **THEN** system SHALL accept mock outline data and persist it as a valid Outline record

### Requirement: Outline generation broadcasts task events
The system SHALL append workflow events and broadcast task status via WebSocket during Outline generation.

#### Scenario: Task started event
- **WHEN** Outline generation background task starts
- **THEN** system SHALL append `TASK_STARTED` workflow event and broadcast via WebSocket

#### Scenario: Task succeeded event
- **WHEN** Outline generation background task completes successfully
- **THEN** system SHALL append `TASK_SUCCEEDED` workflow event and broadcast via WebSocket

#### Scenario: Task failed event
- **WHEN** Outline generation background task fails
- **THEN** system SHALL append `TASK_FAILED` workflow event with error message and broadcast via WebSocket

### Requirement: Outline generation supports versioning
The system SHALL assign a version number to each generated Outline, starting from 1 and incrementing for subsequent generations.

#### Scenario: First Outline version
- **WHEN** Outline is generated for a system with no existing outlines
- **THEN** system SHALL create Outline with `version = 1`

#### Scenario: Subsequent Outline version
- **WHEN** Outline is generated for a system with existing outlines
- **THEN** system SHALL create Outline with `version = max(existing_versions) + 1`
