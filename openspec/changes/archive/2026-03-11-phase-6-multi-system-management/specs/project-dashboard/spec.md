## ADDED Requirements

### Requirement: Project Dashboard displays all systems with gate progress
The Project Dashboard page (`/projects/[projectId]`) SHALL display all experimental systems belonging to the project as SystemCard components in a responsive grid layout. Each SystemCard SHALL show the system title, system number, current gate progress (completedGates / 6 as percentage), status badge, and last update timestamp.

#### Scenario: Dashboard renders system cards with gate progress
- **WHEN** user navigates to `/projects/[projectId]`
- **THEN** the page SHALL render one SystemCard per system, each showing title, `#systemNo`, a progress indicator reflecting completed gates out of 6, and a status badge matching the backend `system.status`

#### Scenario: Dashboard with no systems
- **WHEN** user navigates to a project with zero systems
- **THEN** the page SHALL display an empty state message and a prominent "Create System" button

#### Scenario: Dashboard reflects real-time status updates
- **WHEN** a system's gate status changes via WebSocket event (`gate.passed` or `workflow.state_changed`)
- **THEN** the Dashboard SHALL invalidate the `projectDetail` React Query cache (debounced at 500ms) and re-render the affected SystemCard with updated progress

### Requirement: Project Dashboard shows completion statistics
The Dashboard SHALL include a ProjectStats component displaying: total system count, completed system count (status == `Chapter_Approved`), and Introduction unlock status.

#### Scenario: ProjectStats displays correct counts
- **WHEN** the project has 5 systems, 3 of which have status `Chapter_Approved`
- **THEN** ProjectStats SHALL show "3/3 completed" (or equivalent progress indicator) and Introduction status as "Unlocked"

#### Scenario: ProjectStats with insufficient completions
- **WHEN** the project has 2 systems with status `Chapter_Approved`
- **THEN** ProjectStats SHALL show "2/3 completed" and Introduction status as "Locked"

### Requirement: Project-level Layout with shared WebSocket
A project-level layout (`frontend/app/projects/[projectId]/layout.tsx`) SHALL provide a shared WebSocket subscription scoped to `projectId`, breadcrumb navigation, and shared container styles for all child routes.

#### Scenario: WebSocket persists across dashboard-to-workbench navigation
- **WHEN** user navigates from Dashboard to a system workbench and back
- **THEN** the WebSocket connection SHALL remain active without reconnection

#### Scenario: Breadcrumb reflects current location
- **WHEN** user is on `/projects/[projectId]/systems/[systemId]`
- **THEN** breadcrumb SHALL show "Projects > [Project Name] > [System Title]"

#### Scenario: Breadcrumb on dashboard
- **WHEN** user is on `/projects/[projectId]`
- **THEN** breadcrumb SHALL show "Projects > [Project Name]"

### Requirement: Gate progress utility is shared
The `deriveGateItems` logic SHALL be extracted to `frontend/lib/gates.ts` and reused by both the system workbench `GateNav` and the Dashboard `SystemCard`.

#### Scenario: SystemCard and GateNav produce identical gate items
- **WHEN** given the same system status and workflow snapshot
- **THEN** both SystemCard progress and GateNav items SHALL reflect the same gate completion state
