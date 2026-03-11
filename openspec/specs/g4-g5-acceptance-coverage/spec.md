## ADDED Requirements

### Requirement: Minimum automated acceptance SHALL default to panel-level smoke coverage
The system SHALL define minimum automated acceptance for this change at the panel/render level. The default acceptance harness SHALL validate G4 and G5 panel rendering and key state transitions without requiring full end-to-end Playwright workflow infrastructure.

#### Scenario: G4 panel smoke coverage is sufficient for minimum acceptance
- **WHEN** minimum automated acceptance is evaluated for G4
- **THEN** panel-level rendering and key interaction-state assertions SHALL satisfy the baseline without requiring a full route-level E2E harness

#### Scenario: G5 panel smoke coverage is sufficient for minimum acceptance
- **WHEN** minimum automated acceptance is evaluated for G5
- **THEN** panel-level rendering and key interaction-state assertions SHALL satisfy the baseline without requiring a full route-level E2E harness

### Requirement: Minimum automated acceptance SHALL define a concrete harness and command
The system SHALL define minimum automated acceptance using Vitest with JSDOM and React Testing Library, executed by a single frontend smoke command. The baseline SHALL render `EvidenceMatrixPanel` and `DraftPanel` directly with QueryClient-backed test providers and contract-shaped fixture builders. Playwright E2E MAY remain as a future expansion path, but it SHALL NOT be required for this minimum baseline.

#### Scenario: Harness choice is explicit
- **WHEN** implementation begins
- **THEN** the team SHALL already know that Vitest + JSDOM + React Testing Library is used, that fixture data is injected through direct panel rendering with QueryClient-backed providers and contract-shaped fixtures, and which single command executes the baseline suite

### Requirement: G4 smoke coverage SHALL assert required visible regions and state cues
Minimum acceptance for G4 SHALL assert that the workbench can render the claims region, outline region, and bindings region using deterministic fixture data. It SHALL also assert approved-versus-pending grouping and visible bound-state cues supported by the available data model.

#### Scenario: G4 visible regions render
- **WHEN** deterministic G4 fixture data is loaded into the panel harness
- **THEN** the rendered panel SHALL expose claims, outline, and bindings regions

#### Scenario: G4 grouping is verifiable
- **WHEN** fixture data contains both approved and non-approved latest claims
- **THEN** the rendered panel SHALL expose separate approved and pending groups

#### Scenario: G4 binding cue is verifiable
- **WHEN** deterministic G4 fixture data renders `EvidenceMatrixPanel` with system sections, assets, outlines, and claims
- **THEN** the rendered panel SHALL expose at least one visible binding cue derived from current resource truth, such as a known outline binding for a section

### Requirement: G5 smoke coverage SHALL assert required visible regions and section grouping
Minimum acceptance for G5 SHALL assert that the workbench can render drafts, comments, and action-button regions using deterministic fixture data. It SHALL also assert approved, needs-review, and ready-to-generate section grouping.

The minimum G5 fixture SHALL include exactly these baseline section shapes:
- one approved section with a latest approved draft, at least one visible review comment, and an approval decision marker
- one needs-review section with a latest non-approved draft, a collapsed-by-default preview, and a visible review action region
- one ready-to-generate section with no draft and a visible unavailable or waiting preview state

#### Scenario: G5 visible regions render
- **WHEN** deterministic G5 fixture data is loaded into the panel harness
- **THEN** the rendered panel SHALL expose drafts, comments, and action-button regions

#### Scenario: G5 section groups are verifiable
- **WHEN** fixture data contains approved, non-approved, and missing-draft sections
- **THEN** the rendered panel SHALL expose approved, needs-review, and ready-to-generate groups

### Requirement: Acceptance coverage SHALL verify latest-only selection semantics
Minimum acceptance SHALL verify that latest-only selection uses version-first, updatedAt-second semantics rather than array order. The baseline SHALL prove this behavior through panel rendering with contract-shaped, non-sorted fixtures for claims, outlines, and drafts; helper-only tests MAY supplement the baseline but SHALL NOT replace panel-level smoke assertions.

#### Scenario: Array order does not override latest choice
- **WHEN** fixture data contains older and newer versions in non-sorted order
- **THEN** the rendered panel SHALL still choose the greatest-version record as latest

#### Scenario: UpdatedAt breaks version tie in fixtures
- **WHEN** fixture data contains same-version records with different updated timestamps
- **THEN** the rendered panel SHALL choose the record with the greatest updated timestamp as latest

### Requirement: Acceptance coverage SHALL verify local inline feedback lifecycles
Minimum acceptance SHALL verify that pending, success, and error feedback states remain local to the panel and follow the defined lifecycle rules.

#### Scenario: Pending feedback remains local
- **WHEN** a panel action enters a pending state in the harness
- **THEN** the pending indicator SHALL render inside the relevant panel region without requiring a global notification channel

#### Scenario: Success feedback clears on authoritative refresh
- **WHEN** the harness simulates a successful action followed by authoritative refreshed data
- **THEN** the local success feedback SHALL clear or reduce to a passive updated state
- **AND** clear-on-authoritative-refresh SHALL be required for the minimum baseline, while clear-on-next-user-action MAY be covered as supplemental behavior outside the baseline

#### Scenario: Error feedback survives until retry or replacement
- **WHEN** the harness simulates a failed action
- **THEN** the local error feedback SHALL remain visible until retry, navigation, or authoritative replacement occurs

### Requirement: Acceptance coverage SHALL preserve backend truth assumptions
Minimum acceptance SHALL verify that the frontend does not treat accepted async requests as completed truth and does not require websocket delivery to reach a consistent rendered state.

For this baseline, truth SHALL be split across two authoritative surfaces:
- artifact existence and artifact-ready rendering SHALL come from refreshed resource reads such as claims, outlines, and drafts
- gate, progress, and workflow-level transition truth SHALL come from the workflow snapshot

#### Scenario: Accepted async handle does not imply completed artifact
- **WHEN** fixture or mocked transport data represents a `202 Accepted` state without refreshed resources
- **THEN** the rendered UI SHALL avoid claiming that the final artifact already exists

#### Scenario: Snapshot refresh recovers from websocket absence
- **WHEN** websocket task events are absent or delayed in the harness
- **THEN** a subsequent authoritative resource or workflow refresh SHALL still drive the panel to the correct final visible state
- **AND** the minimum baseline SHALL treat missing or dropped websocket delivery as a required scenario rather than an optional failure-path add-on
