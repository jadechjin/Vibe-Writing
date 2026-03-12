## ADDED Requirements

### Requirement: System list displays within project detail
The `GET /projects/{id}` endpoint SHALL continue to return `systems[]` in `ProjectDetail`. No separate list endpoint is required. The frontend SHALL render systems sorted by `(systemNo, createdAt, id)`.

#### Scenario: Systems sorted correctly
- **WHEN** a project has 3 systems with systemNo 1, 2, 3
- **THEN** the systems array SHALL be ordered by systemNo ascending

### Requirement: System creation with concurrent safety
The `POST /projects/{projectId}/systems` endpoint SHALL handle concurrent `system_no` allocation. If an `IntegrityError` occurs due to duplicate `(project_id, system_no)`, the endpoint SHALL return `409 Conflict` with a message indicating retry.

#### Scenario: Successful system creation
- **WHEN** user creates a system with title "Experiment A"
- **THEN** the system SHALL be created with the next available `system_no` and default sections

#### Scenario: Concurrent creation collision
- **WHEN** two concurrent requests attempt to create systems and both compute the same `system_no`
- **THEN** one request SHALL succeed and the other SHALL return `409 Conflict` with error code `CONFLICT`

### Requirement: System restricted deletion
The `DELETE /systems/{id}` endpoint SHALL check for associated data before deletion. If the system has any assets, asset manifests, or workflow events, the endpoint SHALL return `409 Conflict`. If the system has no associated data beyond sections, the endpoint SHALL delete the system and its sections.

#### Scenario: Delete empty system
- **WHEN** user deletes a system that has only default sections and no assets/manifests/workflow
- **THEN** the system and its sections SHALL be deleted, returning `204 No Content`

#### Scenario: Delete system with assets
- **WHEN** user deletes a system that has uploaded assets
- **THEN** the endpoint SHALL return `409 Conflict` with message "System has associated data and cannot be deleted"

#### Scenario: Delete system with workflow events
- **WHEN** user deletes a system that has workflow instances
- **THEN** the endpoint SHALL return `409 Conflict` with message "System has associated data and cannot be deleted"

#### Scenario: Delete non-existent system
- **WHEN** user attempts to delete a system with an invalid ID
- **THEN** the endpoint SHALL return `404 Not Found`

### Requirement: Frontend system creation dialog
The project Dashboard SHALL provide a modal dialog for creating new systems. The dialog SHALL include fields for title (required) and research goal (optional). On success, the dialog SHALL close and the system list SHALL refresh.

#### Scenario: Create system via modal
- **WHEN** user clicks "New System", fills in title, and submits
- **THEN** the system SHALL be created and appear in the system list

#### Scenario: Create system with empty title
- **WHEN** user submits the creation form with an empty title
- **THEN** the form SHALL prevent submission (client-side validation)

### Requirement: Frontend system deletion with confirmation
The Dashboard SHALL provide a delete action on each SystemCard. Deletion SHALL require a confirmation dialog. On `409 Conflict`, the UI SHALL display a descriptive error explaining the system contains protected data.

#### Scenario: Delete system with confirmation
- **WHEN** user clicks delete on an empty system and confirms
- **THEN** the system SHALL be removed from the list

#### Scenario: Delete system rejected by server
- **WHEN** user confirms deletion but server returns 409
- **THEN** the UI SHALL show a toast/modal: "This system contains data (assets, manifests, or workflow history) and cannot be deleted"

### Requirement: Navigation between dashboard and workbench
Each SystemCard SHALL link to `/projects/[projectId]/systems/[systemId]`. The system workbench SHALL include a "Back to Dashboard" navigation element (via breadcrumb or explicit link).

#### Scenario: Navigate to workbench
- **WHEN** user clicks a SystemCard
- **THEN** the browser SHALL navigate to the system workbench page

#### Scenario: Navigate back to dashboard
- **WHEN** user clicks "Back to Dashboard" or the project breadcrumb in the workbench
- **THEN** the browser SHALL navigate to `/projects/[projectId]`
