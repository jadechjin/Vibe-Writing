## ADDED Requirements

### Requirement: Gate workbench panels SHALL render local active-task status for their own gate
The system SHALL render a gate-local task status region at the top of each G1-G5 workbench panel when the shared task stream contains at least one active task for the current system and selected gate. Active tasks SHALL be limited to statuses `queued`, `running`, or `waiting_user`.

#### Scenario: Matching active task appears in gate panel
- **WHEN** the shared task stream contains an active task whose type maps to the currently displayed gate and whose `systemId` matches the open workspace
- **THEN** the corresponding gate panel SHALL render a local task-status region near the top of the panel

#### Scenario: Terminal task does not keep gate-local status visible
- **WHEN** the latest task event for a matching task has status `succeeded`, `failed`, or `cancelled`
- **THEN** the gate-local active-task region SHALL stop treating that task as an active inline indicator

### Requirement: Gate-local task status SHALL use compact progress cues
The gate-local task status region SHALL present compact visual cues that include task type labeling, status labeling, and progress when available. Running tasks SHALL provide a distinct active visual cue without introducing a full-panel blocking overlay.

#### Scenario: Running task shows compact active cue
- **WHEN** a matching task is `running`
- **THEN** the gate-local region SHALL show a compact active visual cue with status and available progress information

#### Scenario: Task without progress still renders status
- **WHEN** a matching active task has no numeric progress value
- **THEN** the gate-local region SHALL still render its task type and status without inventing a percentage

### Requirement: Gate-local task status SHALL ignore unrelated tasks
The gate-local task status region SHALL ignore tasks whose `systemId` does not match the open workspace or whose task type does not map to the currently displayed gate.

#### Scenario: Different gate task stays hidden
- **WHEN** the shared task stream contains an active task for the same system but a different mapped gate
- **THEN** the current gate panel SHALL NOT render that task in its local status region
