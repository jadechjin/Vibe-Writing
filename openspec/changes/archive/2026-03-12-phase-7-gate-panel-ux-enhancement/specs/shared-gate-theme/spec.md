## ADDED Requirements

### Requirement: Shared style constants module
The system SHALL provide a `frontend/styles/gate-theme.ts` module exporting a `gateTheme` object containing all shared CSSProperties constants used across G1-G5 gate panels. The module SHALL export: `panel`, `sectionCard`, `title`, `desc`, `actionBtn`, `statusBadge`, `emptyState`, `fieldGroup`, `input` style objects.

#### Scenario: Style constants are importable
- **WHEN** a gate panel imports `gateTheme` from `frontend/styles/gate-theme.ts`
- **THEN** all 9 style constant objects are available and typed as `CSSProperties`

#### Scenario: No duplicate style definitions remain
- **WHEN** all 5 gate panels (FigurePlanPanel, AnalysisPanel, ManifestPanel, EvidenceMatrixPanel, DraftPanel) are migrated
- **THEN** no panel file SHALL contain inline definitions of the 9 shared style constants

#### Scenario: Style overrides are still possible
- **WHEN** a panel needs a local style variation
- **THEN** the panel SHALL spread `gateTheme.<constant>` and add overrides inline (e.g., `{ ...gateTheme.sectionCard, marginTop: 8 }`)
