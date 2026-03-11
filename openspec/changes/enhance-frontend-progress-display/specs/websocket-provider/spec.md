## ADDED Requirements

### Requirement: System workbench SHALL expose a single shared task-stream connection
The system workbench SHALL create at most one active WebSocket task-stream connection per mounted system workspace and SHALL expose it through a shared provider that can be consumed by multiple descendants.

#### Scenario: Multiple consumers reuse one connection
- **WHEN** StatusTray and at least one gate-local task status consumer are mounted inside the same system workspace
- **THEN** they SHALL read task events from the same provider-managed connection rather than creating separate socket connections

### Requirement: Shared task-stream state SHALL include bounded recent events and connection state
The shared provider SHALL retain a bounded recent event list and current connection state so that late-mounting consumers can render current task context without waiting for a new frame. The bounded event list SHALL preserve unique tasks by `taskId` through replacement semantics.

#### Scenario: Incoming event replaces existing task by taskId
- **WHEN** a task event arrives for a `taskId` already present in the bounded event list
- **THEN** the provider SHALL replace the prior record for that `taskId` instead of appending a duplicate

#### Scenario: Late consumer receives current provider state
- **WHEN** a consumer mounts after the provider has already received task events
- **THEN** the consumer SHALL immediately receive the current bounded event list and connection state from the provider

### Requirement: Consumer filtering SHALL be scoped and side-effect free
Consumers of the shared provider SHALL be able to filter events by `projectId` and `systemId` without mutating the provider's stored event list or affecting other consumers.

#### Scenario: Consumer filtering does not hide events from another consumer
- **WHEN** two consumers apply different `projectId` or `systemId` filters to the shared provider state
- **THEN** each consumer SHALL receive only its scoped subset while the underlying provider event list remains unchanged

### Requirement: Connection loss SHALL degrade to reconnecting state without blocking the workspace
The provider SHALL surface connection state changes and reconnect attempts without introducing a global blocking overlay or preventing the rest of the workspace from rendering.

#### Scenario: Connection closes while workspace remains usable
- **WHEN** the shared connection closes unexpectedly
- **THEN** the provider SHALL expose a non-open connection state and continue allowing task consumers and the surrounding workspace to render
