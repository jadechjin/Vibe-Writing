## ADDED Requirements

### Requirement: Task navigation SHALL derive target gate from task type prefix
The system SHALL determine whether a task item is navigable by mapping its task type prefix to a gate key. At minimum the following mappings SHALL be supported: `figure_plan.*` → `G1`, `analysis.*` → `G2`, `manifest.*` → `G3`, `evidence.*` → `G4`, `draft.*` → `G5`.

#### Scenario: Known prefix maps to gate
- **WHEN** a task item has a type with a supported prefix
- **THEN** the task item SHALL resolve to the corresponding gate key for navigation

#### Scenario: Unknown prefix remains non-navigable
- **WHEN** a task item has a type that does not match any supported prefix
- **THEN** the system SHALL treat the task item as non-navigable and SHALL NOT invent a fallback gate

### Requirement: Navigable task selection SHALL update workbench view override
The system SHALL allow a user to activate a navigable task item from the StatusTray and SHALL update the workbench view override to the mapped gate.

#### Scenario: Clicking navigable task opens corresponding gate view
- **WHEN** the user activates a task item whose type maps to `G4`
- **THEN** the workbench SHALL switch its selected view override to `G4`

### Requirement: Task navigation SHALL NOT mutate authoritative workflow state
Task-driven navigation SHALL only change the client-side view selection and SHALL NOT rewrite the authoritative workflow snapshot or imply that the backend current gate has changed.

#### Scenario: Navigation leaves workflow truth unchanged
- **WHEN** a user navigates to a gate by activating a task item
- **THEN** the authoritative workflow snapshot SHALL remain unchanged until refreshed by backend workflow truth
