## ADDED Requirements

### Requirement: Section Draft generation returns handle immediately
The system SHALL return a `202 Accepted` response with a `JobHandle` when Section Draft generation is requested, without blocking on generation completion.

#### Scenario: Generation request accepted
- **WHEN** user requests Section Draft generation for a system section
- **THEN** system SHALL return `202` status with `workflow_id` in response body within 500ms

### Requirement: Section Draft generation completes asynchronously
The system SHALL execute Section Draft generation in a background task and persist the result to the `section_drafts` table.

#### Scenario: Background task creates SectionDraft record
- **WHEN** Section Draft generation background task completes successfully
- **THEN** system SHALL create a `SectionDraft` record with `system_id`, `section_id`, `version`, `content_markdown`, and audit fields

#### Scenario: Background task handles executor placeholder
- **WHEN** Section Draft generation calls executor (placeholder implementation)
- **THEN** system SHALL accept mock draft content and persist it as a valid SectionDraft record

### Requirement: Section Draft generation broadcasts task events
The system SHALL append workflow events and broadcast task status via WebSocket during Section Draft generation.

#### Scenario: Task started event
- **WHEN** Section Draft generation background task starts
- **THEN** system SHALL append `TASK_STARTED` workflow event and broadcast via WebSocket

#### Scenario: Task succeeded event
- **WHEN** Section Draft generation background task completes successfully
- **THEN** system SHALL append `TASK_SUCCEEDED` workflow event and broadcast via WebSocket

#### Scenario: Task failed event
- **WHEN** Section Draft generation background task fails
- **THEN** system SHALL append `TASK_FAILED` workflow event with error message and broadcast via WebSocket

### Requirement: Section Draft generation supports versioning
The system SHALL assign a version number to each generated Section Draft, starting from 1 and incrementing for subsequent generations.

#### Scenario: First Section Draft version
- **WHEN** Section Draft is generated for a section with no existing drafts
- **THEN** system SHALL create SectionDraft with `version = 1`

#### Scenario: Subsequent Section Draft version
- **WHEN** Section Draft is generated for a section with existing drafts
- **THEN** system SHALL create SectionDraft with `version = max(existing_versions) + 1`

### Requirement: Section Draft generation validates section existence
The system SHALL verify that the target section exists before starting Section Draft generation.

#### Scenario: Section exists
- **WHEN** Section Draft generation is requested for an existing section
- **THEN** system SHALL proceed with generation

#### Scenario: Section does not exist
- **WHEN** Section Draft generation is requested for a non-existent section
- **THEN** system SHALL return `404 Not Found` error before creating any workflow instance
