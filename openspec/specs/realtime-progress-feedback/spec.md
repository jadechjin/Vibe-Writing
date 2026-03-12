## ADDED Requirements

### Requirement: Indeterminate progress bar in GateTaskStatus
The `GateTaskStatus` component SHALL display an animated indeterminate progress bar when the task status is `running`. The bar SHALL use a CSS sliding animation (30% width element sliding left-to-right within a track). When status transitions to `succeeded`, the bar SHALL briefly show 100% fill before hiding. When status is not `running` or `succeeded`, no progress bar is shown.

#### Scenario: Running state shows animated bar
- **WHEN** a task event with `status="running"` is received via WebSocket
- **THEN** GateTaskStatus SHALL render an animated indeterminate progress bar

#### Scenario: Succeeded state shows completion
- **WHEN** a task event with `status="succeeded"` is received
- **THEN** the progress bar SHALL show full width (100%) for at least 300ms before hiding

#### Scenario: Non-running states show no bar
- **WHEN** task status is `queued`, `failed`, or `cancelled`
- **THEN** no progress bar element is rendered

## MODIFIED Requirements

### Requirement: gate-task-status
The `GateTaskStatus` component SHALL continue to accept `systemId` and `gateKey` props and subscribe to WebSocket task events. In addition to existing spinner behavior, it SHALL render the indeterminate progress bar as specified above.

#### Scenario: Existing task status display preserved
- **WHEN** GateTaskStatus renders for a gate with no active task
- **THEN** it SHALL display the same gate status information as before this change
