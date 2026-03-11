## ADDED Requirements

### Requirement: G4 workbench SHALL use G4 as the sole outline ownership gate
The system SHALL treat outline generation, outline binding management, and outline confirmation as G4-owned actions. G5 MAY display the latest outline as read-only context, but SHALL NOT expose outline mutation actions.

#### Scenario: G4 exposes outline actions
- **WHEN** the active workbench is rendering G4 content
- **THEN** the latest outline summary, binding list, binding actions, and outline confirmation actions SHALL be available in the G4 workbench

#### Scenario: G5 renders outline as read-only context
- **WHEN** the active workbench is rendering G5 content and a latest outline exists
- **THEN** G5 SHALL show at most a read-only summary of the latest outline and SHALL NOT render any outline generate, bind, or confirm controls

### Requirement: G4 claim review SHALL use explicit approved and pending groups
The system SHALL render G4 claims in two explicit groups: approved and pending. Pending SHALL include every claim whose latest version is not approved.

#### Scenario: Approved claims render in approved group
- **WHEN** the latest version of a claim has status `approved`
- **THEN** the claim SHALL appear only in the approved group

#### Scenario: Non-approved claims render in pending group
- **WHEN** the latest version of a claim has any status other than `approved`
- **THEN** the claim SHALL appear only in the pending group

### Requirement: G4 SHALL determine latest records by deterministic version-first selection
The system SHALL determine the latest outline, claim, and other versioned G4 records by selecting the record with the greatest version, and SHALL break ties by greatest updated timestamp. Array order alone SHALL NOT determine latest.

#### Scenario: Version dominates latest selection
- **WHEN** two records share the same logical identity and one has a greater version
- **THEN** the greater-version record SHALL be treated as latest regardless of array order

#### Scenario: Updated timestamp breaks version ties
- **WHEN** two records share the same logical identity and version
- **THEN** the record with the greater `updatedAt` SHALL be treated as latest

### Requirement: G4 and G5 SHALL use system sections as the single section source
The system SHALL use the current system sections as the single source of section identity for G4 section visibility and G5 section grouping. Sections without claims, bindings, or drafts SHALL still render as empty items or empty groups rather than being hidden.

#### Scenario: Empty section still renders
- **WHEN** a system section has no approved claims, no bindings, and no drafts
- **THEN** the section SHALL still appear in the workbench with an empty or waiting state

#### Scenario: Outline does not redefine section identity
- **WHEN** the latest outline contains section-like content that differs from system sections
- **THEN** workbench grouping and section ownership SHALL still be keyed by system sections

### Requirement: G4 SHALL provide bounded visibility for evidence-link state without new backend APIs
The system SHALL only promise evidence-link visibility that can be derived from currently available query data and mutation outcomes. When no authoritative read model exists, the UI SHALL use helper text or limited status messaging instead of claiming complete historical binding truth.

#### Scenario: Binding status is shown from known data only
- **WHEN** the workbench can determine that the latest outline binding or current mutation result references an asset-section relationship
- **THEN** the UI SHALL show a concrete bound state for that known relationship

#### Scenario: Unknown historical binding truth is not overstated
- **WHEN** the workbench lacks an authoritative read model for claim-level evidence-link history
- **THEN** the UI SHALL avoid presenting unsupported global certainty and SHALL use a constrained helper message instead

### Requirement: G5 SHALL group sections into approved, needs-review, and ready-to-generate
The system SHALL classify each system section into exactly one of three G5 groups using a single priority order: approved, needs-review, then ready-to-generate. A section with a latest approved draft SHALL be approved. A section with a latest non-approved draft SHALL be needs-review. A section without a draft SHALL be ready-to-generate.

#### Scenario: Approved draft places section in approved group
- **WHEN** a system section has a latest draft with status `approved`
- **THEN** the section SHALL appear only in the approved group

#### Scenario: Non-approved latest draft places section in needs-review group
- **WHEN** a system section has a latest draft whose status is not `approved`
- **THEN** the section SHALL appear only in the needs-review group

#### Scenario: Missing draft places section in ready-to-generate group
- **WHEN** a system section has no draft records
- **THEN** the section SHALL appear only in the ready-to-generate group

### Requirement: G5 draft preview SHALL default to collapsed local previews
The system SHALL render draft previews as collapsible local previews. By default, draft preview content SHALL be collapsed, MAY allow multiple sections to be expanded at once, and SHALL provide an explicit empty or unavailable state when no previewable draft exists.

#### Scenario: Existing draft starts collapsed
- **WHEN** a section has a latest draft with content
- **THEN** the draft preview SHALL initially render in a collapsed state until the user expands it

#### Scenario: Missing draft shows unavailable preview state
- **WHEN** a section has no previewable draft
- **THEN** the section SHALL show an explicit unavailable or waiting preview state instead of empty body content

### Requirement: G4 and G5 actions SHALL use local inline feedback with defined lifecycle
The system SHALL show local inline feedback for G4 and G5 actions. Each action SHALL define pending, success, and error presentation within the relevant panel. Inline success feedback SHALL clear on the next user action or authoritative data refresh. Inline error feedback SHALL remain until the user retries, dismisses by navigation, or authoritative refresh replaces it.

#### Scenario: Pending feedback stays local to action region
- **WHEN** the user triggers an evidence binding, outline binding, review submission, or similar workbench action
- **THEN** pending feedback SHALL render within the relevant panel or action region and SHALL NOT require a global toast system

#### Scenario: Success feedback clears after authoritative refresh
- **WHEN** an action succeeds and subsequent query refresh confirms the new state
- **THEN** the corresponding success feedback SHALL clear automatically or reduce to a passive updated state

#### Scenario: Error feedback persists for retry
- **WHEN** an action fails
- **THEN** the panel SHALL keep the inline error visible until retry, navigation, or authoritative replacement occurs

### Requirement: Disabled G5 actions SHALL show a single prioritized helper reason
The system SHALL show one primary helper reason for a disabled G5 action. The priority order SHALL be: task in progress, missing confirmed outline, existing latest draft already present, workflow blocker, then fallback unmet prerequisite.

#### Scenario: Task progress overrides other reasons
- **WHEN** a section action is disabled because a relevant task is currently pending
- **THEN** the helper reason SHALL communicate task progress rather than a lower-priority prerequisite message

#### Scenario: Missing outline overrides blocker fallback
- **WHEN** a section action is disabled because no confirmed outline exists
- **THEN** the helper reason SHALL communicate the missing outline prerequisite before any generic fallback text
