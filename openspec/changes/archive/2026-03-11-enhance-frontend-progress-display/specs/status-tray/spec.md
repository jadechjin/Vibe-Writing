## ADDED Requirements

### Requirement: Status tray SHALL render compact task metadata for current workspace tasks
The StatusTray SHALL render a compact, scrollable list of task items for the current workspace and SHALL continue showing connection status separately from task rows. Each rendered task row SHALL include status, message, task type label, and progress information when available.

#### Scenario: Task row shows compact metadata
- **WHEN** a task event with type, status, message, and numeric progress is rendered in the StatusTray
- **THEN** the row SHALL show status, task type label, message text, a progress indicator, and percentage text

#### Scenario: Task row without progress omits percentage
- **WHEN** a rendered task event has no numeric progress
- **THEN** the row SHALL omit percentage text rather than displaying a fabricated progress value

### Requirement: Status tray SHALL remain bounded and non-blocking
The StatusTray SHALL remain a bounded list region that does not block the main workspace and does not require a global loading overlay for long-running tasks.

#### Scenario: Many task events remain bounded
- **WHEN** more task events arrive than the tray's bounded display limit
- **THEN** the StatusTray SHALL continue rendering within a bounded scrollable region instead of unbounded page growth

### Requirement: Status tray SHALL expose navigation affordance only for mapped tasks
The StatusTray SHALL expose task activation behavior only when the rendered task can be mapped to a gate. Unmapped tasks SHALL remain visible as read-only status rows.

#### Scenario: Mapped task is activatable
- **WHEN** a rendered task type maps to a supported gate
- **THEN** the row SHALL expose an activation affordance that can trigger navigation to that gate

#### Scenario: Unmapped task stays read-only
- **WHEN** a rendered task type does not map to a supported gate
- **THEN** the row SHALL remain visible but SHALL NOT expose gate-navigation behavior
