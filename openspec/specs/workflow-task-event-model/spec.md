# workflow-task-event-model Specification

## Purpose
TBD - created by archiving change phase-5-implementation-analysis. Update Purpose after archive.
## Requirements
### Requirement: Thin Workflow Model

The system SHALL use thin workflow model where workflow instances track async generation progress.

#### Scenario: Workflow instance creation
- **WHEN** async generation starts
- **THEN** system SHALL create WorkflowInstance with workflow_key, system_id, status=QUEUED, and version

#### Scenario: Workflow as state machine
- **WHEN** workflow progresses
- **THEN** status SHALL transition: QUEUED → SUCCEEDED or QUEUED → FAILED

#### Scenario: No long-running orchestration
- **WHEN** workflow is created
- **THEN** it SHALL NOT orchestrate multi-step processes, only track single async generation

### Requirement: Task Event Persistence

The system SHALL persist task events as WorkflowEvent records linked to WorkflowInstance.

#### Scenario: Event creation
- **WHEN** task state changes (created, succeeded, failed)
- **THEN** system SHALL create WorkflowEvent with event_type, payload_json, and timestamp

#### Scenario: Event ordering
- **WHEN** multiple events exist for same workflow
- **THEN** events SHALL be ordered by created_at ascending and id ascending

#### Scenario: Event immutability
- **WHEN** event is created
- **THEN** it SHALL NOT be modified or deleted, only appended

### Requirement: Job Handle Format

The system SHALL generate job_id using format: `<workflow_key>:<system_id>:<version>`.

#### Scenario: Job ID structure
- **WHEN** workflow instance is created
- **THEN** job_id SHALL follow pattern `<workflow_key>:<system_id>:<version>` (e.g., `figure_plan_generate:sys-123:1`)

#### Scenario: Job ID uniqueness
- **WHEN** multiple workflows exist for same system
- **THEN** each SHALL have unique job_id due to incrementing version

#### Scenario: Job ID parsing
- **WHEN** frontend receives job_id
- **THEN** it SHALL be able to extract workflow_key, system_id, and version from the format

### Requirement: Event Type Enumeration

Phase 5 async generation workflows SHALL use event types: task.created, task.succeeded, task.failed. The full workflow system supports additional event types (task.progress) and states (RUNNING, WAITING_USER, gate.blocked, gate.passed) for other workflow types.

#### Scenario: Initial event
- **WHEN** Phase 5 async generation workflow starts
- **THEN** first event SHALL have event_type=task.created

#### Scenario: Success event
- **WHEN** Phase 5 async generation completes successfully
- **THEN** final event SHALL have event_type=task.succeeded

#### Scenario: Failure event
- **WHEN** Phase 5 async generation fails
- **THEN** final event SHALL have event_type=task.failed with error details in payload

#### Scenario: Scope limitation
- **WHEN** implementing non-Phase-5 workflows
- **THEN** system MAY use additional event types (task.progress) and states (RUNNING, WAITING_USER, gate.blocked, gate.passed) as supported by TaskWorkflowService

### Requirement: Workflow Context Storage

The system SHALL store workflow-specific context in WorkflowInstance.context_json.

#### Scenario: Context initialization
- **WHEN** workflow is created
- **THEN** context_json SHALL be initialized with relevant parameters (e.g., section_key, claim_ids)

#### Scenario: Context immutability
- **WHEN** workflow progresses
- **THEN** context_json SHOULD NOT be modified after creation (input snapshot), but MAY be updated via TaskWorkflowService.append_event(context_update) if needed

#### Scenario: Context retrieval
- **WHEN** complete phase executes
- **THEN** it SHALL read context_json to retrieve original input parameters

### Requirement: Event Payload Structure

The system SHALL store event-specific data in WorkflowEvent.payload_json.

#### Scenario: Payload format
- **WHEN** event is created
- **THEN** payload_json SHALL contain status, message, and event-specific fields

#### Scenario: Snake case for workflow
- **WHEN** storing data in workflow payload
- **THEN** field names SHALL use snake_case (e.g., from_state, to_state)

#### Scenario: Camel case for WebSocket
- **WHEN** broadcasting event via WebSocket
- **THEN** field names SHALL use camelCase (e.g., fromState, toState)

### Requirement: Workflow Snapshot Query

The system SHALL provide workflow snapshot query combining instance and events.

#### Scenario: Snapshot structure
- **WHEN** querying workflow snapshot
- **THEN** response SHALL include workflow_id, job_id, status, context, events array, and latest_event

#### Scenario: Event aggregation
- **WHEN** building snapshot
- **THEN** all events for workflow SHALL be included in chronological order

#### Scenario: Latest event extraction
- **WHEN** snapshot is built
- **THEN** latest_event SHALL be the last event in chronological order

### Requirement: Workflow Version Tracking

The system SHALL track workflow version to support multiple generations for same entity.

#### Scenario: Version increment
- **WHEN** new workflow is created for same system and workflow_key
- **THEN** version SHALL be max(existing_versions) + 1

#### Scenario: Version in job_id
- **WHEN** job_id is generated
- **THEN** it SHALL include version number for traceability

#### Scenario: Historical workflow access
- **WHEN** querying workflows
- **THEN** system SHALL support retrieving all versions, not just latest

### Requirement: Workflow State Transitions

The system SHALL enforce valid state transitions: QUEUED → SUCCEEDED or QUEUED → FAILED.

#### Scenario: Valid transition to success
- **WHEN** workflow completes successfully
- **THEN** status SHALL transition from QUEUED to SUCCEEDED

#### Scenario: Valid transition to failure
- **WHEN** workflow fails
- **THEN** status SHALL transition from QUEUED to FAILED

#### Scenario: Invalid transition prevention
- **WHEN** workflow is already in terminal state (SUCCEEDED or FAILED)
- **THEN** system SHALL NOT allow further state transitions

### Requirement: Workflow Completion Timestamp

The system SHALL record completion timestamp when workflow reaches terminal state.

#### Scenario: Completion time on success
- **WHEN** workflow transitions to SUCCEEDED
- **THEN** completed_at SHALL be set to current UTC timestamp

#### Scenario: Completion time on failure
- **WHEN** workflow transitions to FAILED
- **THEN** completed_at SHALL be set to current UTC timestamp

#### Scenario: No completion time for queued
- **WHEN** workflow is in QUEUED state
- **THEN** completed_at SHALL be NULL

### Requirement: Error Information Storage

The system SHALL store error details in WorkflowInstance.last_error on failure.

#### Scenario: Error capture
- **WHEN** workflow fails
- **THEN** last_error SHALL contain error message or exception details

#### Scenario: Error sanitization
- **WHEN** storing error for user-facing workflows
- **THEN** sensitive information (stack traces, internal paths) SHALL be sanitized

#### Scenario: No error on success
- **WHEN** workflow succeeds
- **THEN** last_error SHALL be NULL or empty

