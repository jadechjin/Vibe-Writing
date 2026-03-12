## ADDED Requirements

### Requirement: GatePanel Routing

The GatePanel component SHALL route to appropriate gate-specific panels based on effectiveGateKey.

#### Scenario: Gate-specific panel rendering
- **WHEN** effectiveGateKey changes
- **THEN** GatePanel SHALL render the corresponding panel component (G4 → EvidenceMatrixPanel, G5 → DraftPanel)

#### Scenario: Standardized props passing
- **WHEN** rendering gate-specific panel
- **THEN** GatePanel SHALL pass standardized props: snapshot, blockers, systemId, systemDetail

### Requirement: Namespaced React Query Hooks

The frontend SHALL use separate hooks (useEvidence, useDrafts) with namespaced query keys.

#### Scenario: Query key isolation
- **WHEN** useEvidence or useDrafts creates query keys
- **THEN** keys SHALL be namespaced with module prefix (e.g., ['evidence', 'figure-plans', systemId])

#### Scenario: Independent invalidation
- **WHEN** mutation succeeds in one module
- **THEN** only that module's query keys SHALL be invalidated, not other modules

#### Scenario: No cross-module pollution
- **WHEN** useEvidence and useDrafts are used simultaneously
- **THEN** their query keys SHALL NOT collide or interfere with each other

### Requirement: Mutation Success Invalidation

The frontend SHALL invalidate relevant query keys in mutation onSuccess callbacks.

#### Scenario: Query invalidation after mutation
- **WHEN** mutation (e.g., approve claim, generate outline) succeeds
- **THEN** system SHALL call queryClient.invalidateQueries for affected query keys

#### Scenario: Workflow snapshot invalidation
- **WHEN** any gate-related mutation succeeds
- **THEN** system SHALL invalidate ['workflow', systemId] query key to refresh workflow state

#### Scenario: Automatic refetch
- **WHEN** query keys are invalidated
- **THEN** React Query SHALL automatically refetch affected queries to update UI

### Requirement: WebSocket Real-Time Feedback

The GateTaskStatus component SHALL use WebSocketContext for real-time task progress.

#### Scenario: Task event subscription
- **WHEN** GateTaskStatus mounts
- **THEN** component SHALL subscribe to WebSocket task events for current system

#### Scenario: Active task display
- **WHEN** task.created event is received
- **THEN** GateTaskStatus SHALL immediately display the active task in UI

#### Scenario: Task completion update
- **WHEN** task.succeeded or task.failed event is received
- **THEN** GateTaskStatus SHALL update task status and trigger query invalidation

### Requirement: 202 + JobHandle Contract

The frontend SHALL handle 202 Accepted responses with JobHandle from async generation endpoints.

#### Scenario: Async generation request
- **WHEN** user triggers generation (e.g., generate figure plan)
- **THEN** frontend SHALL send POST request and expect 202 status with JobHandle in response

#### Scenario: JobHandle structure
- **WHEN** 202 response is received
- **THEN** response.data.handle SHALL contain workflow_id, job_id, and status=QUEUED

#### Scenario: Immediate UI feedback
- **WHEN** 202 response is received
- **THEN** frontend SHALL immediately show "generation started" feedback without waiting for completion

### Requirement: Deduplication and Versioning

The workbenchSelectors SHALL deduplicate and select latest version of records.

#### Scenario: Latest version selection
- **WHEN** multiple versions of same record exist (e.g., FigurePlan v1, v2, v3)
- **THEN** selectLatestVersionedRecord SHALL return only the highest version

#### Scenario: Timestamp-based deduplication
- **WHEN** records have same version but different timestamps
- **THEN** selector SHALL return the record with latest updatedAt timestamp

#### Scenario: Consistent list display
- **WHEN** rendering lists (claims, drafts, outlines)
- **THEN** UI SHALL always show deduplicated, latest-version records

### Requirement: Workflow State Derivation

The useProjectStatus hook SHALL derive active gate from workflow snapshot currentState.

#### Scenario: Active gate resolution
- **WHEN** workflow snapshot is loaded
- **THEN** useProjectStatus SHALL call resolveActiveGateFromState to determine current gate

#### Scenario: Panel transition trigger
- **WHEN** workflow currentState updates to next gate's threshold
- **THEN** GatePanel SHALL automatically transition to next gate's panel

#### Scenario: Source of truth
- **WHEN** multiple components need current gate information
- **THEN** all SHALL use useProjectStatus as single source of truth

### Requirement: Manual State Updates

The frontend SHALL use manual setQueryData for immediate UI transitions before refetch.

#### Scenario: Optimistic state update
- **WHEN** mutation is triggered
- **THEN** frontend MAY call queryClient.setQueryData to update UI immediately

#### Scenario: Background refetch reconciliation
- **WHEN** manual setQueryData and background refetch both occur
- **THEN** React Query SHALL reconcile using latest data from server

#### Scenario: Race condition handling
- **WHEN** manual update and refetch conflict
- **THEN** server data SHALL take precedence over manual update

### Requirement: Component Boundary Separation

The frontend SHALL maintain clear boundaries: GatePanel for routing, specific panels for content.

#### Scenario: GatePanel responsibilities
- **WHEN** GatePanel renders
- **THEN** it SHALL only handle routing and props passing, not render gate-specific content

#### Scenario: Panel responsibilities
- **WHEN** EvidenceMatrixPanel or DraftPanel renders
- **THEN** it SHALL handle all gate-specific UI, data fetching, and mutations

#### Scenario: No shared state mutation
- **WHEN** G4 or G5 panel modifies state
- **THEN** it SHALL NOT directly modify GatePanel or system page state
