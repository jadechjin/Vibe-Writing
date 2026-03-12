# async-generation-pattern Specification

## Purpose
TBD - created by archiving change phase-5-implementation-analysis. Update Purpose after archive.
## Requirements
### Requirement: Three-Phase Pattern Structure

The async generation pattern SHALL consist of three distinct phases: generate, run, and complete.

#### Scenario: Phase separation
- **WHEN** implementing a new async generation feature
- **THEN** the implementation MUST include all three phases: `generate_*`, `run_*_generation_task`, and `complete_*_generation`

#### Scenario: Phase responsibilities
- **WHEN** each phase executes
- **THEN** generate phase SHALL validate inputs and return 202 + JobHandle, run phase SHALL spawn background task with fresh session, and complete phase SHALL create business records and append events

### Requirement: Generate Phase Contract

The generate phase SHALL validate inputs, create workflow instance, and return HTTP 202 Accepted with JobHandle.

#### Scenario: Successful generation start
- **WHEN** generate endpoint is called with valid inputs
- **THEN** system SHALL return 202 status code with JobHandle containing workflow_id and job_id

#### Scenario: Workflow instance creation
- **WHEN** generate phase executes
- **THEN** system SHALL create WorkflowInstance with status=QUEUED and initial task.created event

#### Scenario: Input validation failure
- **WHEN** generate endpoint is called with invalid inputs
- **THEN** system SHALL return 4xx error without creating workflow instance

### Requirement: Run Phase Session Isolation

The run phase SHALL spawn background task with fresh DB session using session binding pattern.

#### Scenario: Session binding extraction
- **WHEN** run phase starts
- **THEN** system SHALL call `get_*_task_session_bind()` to extract bind object and session type flag

#### Scenario: Fresh session creation
- **WHEN** background task executes
- **THEN** system SHALL create new AsyncSession or Session from bind, not reuse request session

#### Scenario: Startup delay
- **WHEN** background task starts
- **THEN** system SHALL delay 50ms before calling complete phase to allow request to finish

### Requirement: Complete Phase Idempotency

The complete phase SHALL check workflow status is QUEUED before executing to prevent duplicate processing.

#### Scenario: Idempotency check success
- **WHEN** complete phase executes and workflow status is QUEUED
- **THEN** system SHALL proceed with business record creation

#### Scenario: Idempotency check failure
- **WHEN** complete phase executes and workflow status is not QUEUED
- **THEN** system SHALL return immediately without creating records or appending events

#### Scenario: Duplicate task execution
- **WHEN** same workflow is triggered multiple times
- **THEN** only the first execution SHALL create business records, subsequent executions SHALL be no-ops

### Requirement: Success Event Sequence

The complete phase SHALL append task.succeeded event and commit business records on success.

#### Scenario: Successful completion
- **WHEN** complete phase finishes successfully
- **THEN** system SHALL create business records, append task.succeeded event, and commit transaction

#### Scenario: Event payload format
- **WHEN** task.succeeded event is created
- **THEN** event SHALL include workflow_id, job_id, status=SUCCEEDED, and relevant business record IDs

### Requirement: Failure Event Sequence

The complete phase SHALL append task.failed event on failure. Module-specific rollback behavior: drafts module performs session.rollback(), evidence module does not.

#### Scenario: Failure handling
- **WHEN** complete phase encounters an error
- **THEN** system SHALL append task.failed event with error details and commit failure event

#### Scenario: Module-specific rollback
- **WHEN** drafts module complete phase fails
- **THEN** system SHALL rollback transaction before appending task.failed event
- **WHEN** evidence module complete phase fails
- **THEN** system SHALL NOT rollback transaction, only append task.failed event

#### Scenario: Partial record prevention
- **WHEN** failure occurs after partial flush in drafts module
- **THEN** rollback SHALL ensure no business records are committed alongside task.failed event

### Requirement: Version Helper Pattern

The repository layer SHALL provide version helper functions using max(version)+1 pattern.

#### Scenario: Version allocation
- **WHEN** creating a new versioned record
- **THEN** system SHALL call `get_next_*_version()` to get max(version)+1 for the entity

#### Scenario: Version uniqueness
- **WHEN** concurrent requests allocate versions
- **THEN** database unique constraint SHALL prevent duplicate versions, causing one request to fail

### Requirement: Router Thin Layer

The router layer SHALL remain thin, only handling broadcaster extraction and background task spawning.

#### Scenario: Router responsibilities
- **WHEN** router endpoint is called
- **THEN** router SHALL extract broadcaster, call service generate function, extract session bind, spawn background task with asyncio.create_task, and return response

#### Scenario: No business logic in router
- **WHEN** implementing router endpoint
- **THEN** router SHALL NOT contain validation, business logic, or database operations

### Requirement: Naming Convention

The three phases SHALL follow consistent naming: `generate_*`, `run_*_generation_task`, `complete_*_generation`.

#### Scenario: Function naming
- **WHEN** implementing new async generation feature for entity X
- **THEN** functions SHALL be named `generate_x`, `run_x_generation_task`, and `complete_x_generation`

#### Scenario: Workflow key naming
- **WHEN** creating workflow instance
- **THEN** workflow_key SHALL follow pattern `<entity>_generate` (e.g., `figure_plan_generate`, `evidence_matrix_generate`)

