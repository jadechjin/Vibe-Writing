## ADDED Requirements

### Requirement: Gate panel SHALL honor a valid selected-gate view override
The gate workbench SHALL accept a client-side selected-gate view override and SHALL use it to determine which gate content renders when the override is valid for the current gate set.

#### Scenario: View override replaces snapshot-driven panel selection
- **WHEN** the page provides a valid selected-gate override of `G3` while the authoritative workflow current gate remains `G2`
- **THEN** the gate workbench SHALL render the `G3` panel content without rewriting the authoritative workflow state

### Requirement: Gate panel SHALL fall back to authoritative gate when no valid override exists
The gate workbench SHALL fall back to the authoritative workflow gate when no selected-gate override is set or when the provided override is invalid for the current workspace.

#### Scenario: Missing override uses workflow current gate
- **WHEN** no selected-gate override is present
- **THEN** the gate workbench SHALL render the panel associated with the authoritative workflow current gate

#### Scenario: Invalid override is ignored
- **WHEN** the page provides a selected-gate value that is not part of the current workspace gate set
- **THEN** the gate workbench SHALL ignore the invalid override and render from authoritative workflow state

### Requirement: Gate panel view override SHALL survive until cleared or invalidated
A valid selected-gate override SHALL continue determining visible gate content until the user selects a different gate or the application clears the override because it is no longer valid after authoritative refresh.

#### Scenario: Override persists across non-invalidating updates
- **WHEN** task events or other local updates occur without invalidating the selected gate
- **THEN** the gate workbench SHALL continue rendering the currently selected override
