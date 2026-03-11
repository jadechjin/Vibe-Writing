## 1. Deterministic data selection and shared workbench rules

- [x] 1.1 Add deterministic latest-selection helpers for versioned claims, outlines, and drafts using version-first and updatedAt-second ordering
- [x] 1.2 Refactor G4 and G5 panels to consume shared latest-only selection rules instead of relying on transport array tail order
- [x] 1.3 Lock section identity to system sections and keep empty sections visible as empty or waiting states

## 2. G4 workbench refinement

- [x] 2.1 Keep outline generation, binding, and confirmation controls exclusively in the G4 workbench
- [x] 2.2 Split G4 claims into explicit approved and pending groups using latest-version status only
- [x] 2.3 Add bounded evidence-link visibility cues and helper messaging without assuming a new backend read model
- [x] 2.4 Improve section visibility and outline binding duplicate/already-bound feedback within the existing inline-style system

## 3. G5 workbench refinement

- [x] 3.1 Group sections into approved, needs-review, and ready-to-generate using a single deterministic classifier
- [x] 3.2 Add collapsed-by-default draft previews with explicit unavailable states for non-previewable sections
- [x] 3.3 Add clearer review decision markers and local inline submission feedback for review actions
- [x] 3.4 Add single-priority disabled helper reasons for blocked G5 actions

## 4. Minimum automated acceptance baseline

- [x] 4.1 Introduce or configure the minimal panel-level smoke test harness and execution command for frontend acceptance coverage using Vitest + JSDOM + React Testing Library, direct panel rendering, QueryClient-backed test providers, and contract-shaped fixture builders
- [x] 4.2 Add G4 smoke coverage for `EvidenceMatrixPanel` covering claims, outline, bindings, approved/pending grouping, and at least one resource-derived known binding cue from outlines/assets/system sections
- [x] 4.3 Add G5 smoke coverage for `DraftPanel` using a fixed three-section fixture: approved with decision marker and visible review comment, needs-review with collapsed preview and review actions, and ready-to-generate with unavailable or waiting preview state
- [x] 4.4 Add panel-level smoke assertions proving latest-selection semantics with non-sorted fixtures for claims/outlines/drafts, require clear-on-authoritative-refresh for success feedback, keep helper-only tests optional, and treat clear-on-next-user-action as supplemental coverage
- [x] 4.5 Add a dual-surface async truth matrix covering one G4 action and one G5 action where `202 Accepted` does not imply finished artifacts, websocket delivery may be absent, workflow refresh updates gate/progress truth, and later resource refresh unlocks artifact-ready rendering

## 5. Verification and implementation handoff

- [x] 5.1 Verify specs and design remain aligned with current backend workflow constraints and existing G4/G5 contract tests
- [x] 5.2 Run the planned smoke/typecheck verification commands and confirm the new minimum acceptance baseline is executable
- [x] 5.3 Prepare implementation handoff notes so execution can proceed mechanically from specs, design, and tasks without new design decisions
