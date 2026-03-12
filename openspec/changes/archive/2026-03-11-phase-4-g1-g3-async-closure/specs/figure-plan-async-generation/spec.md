## ADDED Requirements

### Requirement: Figure Plan generation returns handle immediately
The system SHALL return a `202 Accepted` response with a `JobHandle` when Figure Plan generation is requested, without blocking on generation completion.

#### Scenario: Generation request accepted
- **WHEN** user requests Figure Plan generation for a system
- **THEN** system SHALL return `202` status with `workflow_id` in response body within 500ms

### Requirement: Figure Plan generation completes asynchronously
The system SHALL execute Figure Plan generation in a background task and persist the result to the `figure_plans` table.

#### Scenario: Background task creates FigurePlan record
- **WHEN** Figure Plan generation background task completes successfully
- **THEN** system SHALL create a `FigurePlan` record with `system_id`, `version`, `data_needed_json`, and audit fields

#### Scenario: Background task handles executor placeholder
- **WHEN** Figure Plan generation calls executor (placeholder implementation)
- **THEN** system SHALL accept mock data and persist it as a valid FigurePlan record

### Requirement: Figure Plan generation broadcasts task events
The system SHALL append workflow events and broadcast task status via WebSocket during Figure Plan generation.

#### Scenario: Task started event
- **WHEN** Figure Plan generation background task starts
- **THEN** system SHALL append `TASK_STARTED` workflow event and broadcast via WebSocket

#### Scenario: Task succeeded event
- **WHEN** Figure Plan generation background task completes successfully
- **THEN** system SHALL append `TASK_SUCCEEDED` workflow event and broadcast via WebSocket

#### Scenario: Task failed event
- **WHEN** Figure Plan generation background task fails
- **THEN** system SHALL append `TASK_FAILED` workflow event with error message and broadcast via WebSocket

### Requirement: Figure Plan generation supports versioning
The system SHALL assign a version number to each generated Figure Plan, starting from 1 and incrementing for subsequent generations.

#### Scenario: First Figure Plan version
- **WHEN** Figure Plan is generated for a system with no existing plans
- **THEN** system SHALL create FigurePlan with `version = 1`

#### Scenario: Subsequent Figure Plan version
- **WHEN** Figure Plan is generated for a system with existing plans
- **THEN** system SHALL create FigurePlan with `version = max(existing_versions) + 1`
