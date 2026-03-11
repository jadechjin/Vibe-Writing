## Why

G4/G5 workbench flows have reached a minimally operable state, but the current interaction clarity is still weak enough to cause repeated UX regressions and ambiguous operator feedback. This change is needed now to lock down the second-pass workbench behaviors for evidence/draft review and to define a realistic minimum automated acceptance baseline before the team returns to the broader G0/G1 and cross-gate backlog.

## What Changes

- Refine G4 workbench behavior so claim review, evidence binding, outline binding, and section visibility communicate state more clearly without changing the existing workbench architecture or async workflow semantics.
- Refine G5 workbench behavior so draft review, decision feedback, section grouping, and draft preview affordances are clearer and easier to verify in the current system workspace.
- Define spec-level UI expectations for G4/G5 state presentation, including approved vs pending grouping, binding status feedback, decision markers, and post-submit feedback states.
- Define a minimum automated acceptance strategy for G4/G5 that reflects the repository's real testing baseline, including a smaller smoke/render path and a documented Playwright E2E path as a higher-cost option.
- Record current testing and contract limitations that constrain G4/G5 verification, including missing Playwright configuration and frontend dependence on workflow snapshot plus task-event invalidation.
- Explicitly defer G0 experience cleanup, G1 figure plan UX refinement, and cross-gate status unification to later backlog work outside this change.

## Capabilities

### New Capabilities
- `g4-g5-workbench-refinement`: Defines the required G4/G5 workbench interaction behaviors for claim binding visibility, outline binding feedback, section grouping, review decision markers, collapsible draft preview, and clearer submission feedback.
- `g4-g5-acceptance-coverage`: Defines the minimum acceptance coverage expectations for G4/G5, including happy-path visibility checks, realistic smoke/render coverage, and the conditions under which Playwright E2E becomes part of the supported baseline.

### Modified Capabilities
- None.

## Impact

- Affected frontend workbench code includes `frontend/components/gates/EvidenceMatrixPanel.tsx`, `frontend/components/gates/DraftPanel.tsx`, `frontend/components/gates/GatePanel.tsx`, and `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx`.
- Affected frontend data boundaries include `frontend/hooks/useEvidence.ts`, `frontend/hooks/useDrafts.ts`, and `frontend/hooks/useProjectStatus.ts`.
- Existing backend API and workflow contracts remain in scope as constraints, especially `GET /systems/{id}/workflow`, evidence/draft generation endpoints, websocket task events, and G4/G5 gate truth documented in backend tests.
- Testing/tooling impact includes `frontend/e2e/`, `frontend/package.json`, and any future minimal smoke/render test entry points required to support automated acceptance.
- No breaking API changes are proposed in this phase; any missing backend read-model support is tracked as a risk or candidate dependency rather than assumed implementation scope.
