## Context

The repository already has a minimally operable G4/G5 workbench inside the existing Next.js App Router system workspace, with `MainShell`, `EvidenceHub`, `GatePanel`, and `StatusTray` composing the primary experience. G4 behavior currently lives in `frontend/components/gates/EvidenceMatrixPanel.tsx`, while G5 behavior lives in `frontend/components/gates/DraftPanel.tsx`. Data access and normalization boundaries are already concentrated in `frontend/hooks/useEvidence.ts`, `frontend/hooks/useDrafts.ts`, `frontend/hooks/useProjectStatus.ts`, and `frontend/hooks/useSystemAdvance.ts`.

Backend truth for this area is already defined by thin workflow semantics and tested contracts rather than by a dedicated read model. `POST /systems/{id}/advance` only requests gate progression. Generate endpoints return `202 Accepted` plus a handle, and completion truth arrives later through workflow snapshot refreshes, resource queries, and websocket task events. Existing backend tests in `backend/tests/modules/evidence/test_evidence_api.py` and `backend/tests/modules/drafts/test_drafts_api.py` are the current executable truth for G4/G5 constraints.

This design exists to remove the remaining planning ambiguity before implementation. The change is intentionally restricted to G4/G5 workbench refinement and minimum automated acceptance. It does not reopen G0/G1 work, cross-gate status unification, or backend architectural expansion.

## Goals / Non-Goals

**Goals:**
- Refine G4 interactions within the existing workbench to make claim grouping, binding visibility, and section visibility more explicit.
- Refine G5 interactions within the existing workbench to make section grouping, decision signaling, draft preview, and action feedback easier to understand.
- Encode a deterministic latest-only selection rule that is independent of array order.
- Keep all async truth tied to workflow snapshot refreshes, resource refreshes, and websocket task invalidation rather than optimistic UI truth.
- Define a minimum automated acceptance strategy that is realistic for the current repository and test baseline.
- Produce artifact-ready constraints and task sequencing so implementation can be mechanical.

**Non-Goals:**
- Rebuilding the system workspace shell, replacing `MainShell`, or introducing a new layout model.
- Adding a new global state library, global toast infrastructure, or second styling system.
- Expanding backend APIs by default, including new claim evidence-link read-model endpoints.
- Promoting Playwright full E2E to the default minimum baseline for this change.
- Implementing G0 UX cleanup, G1 Figure Plan refinement, or cross-gate state unification.

## Decisions

### 1. G4 is the sole outline ownership gate
**Decision:** Outline generation, binding management, and outline confirmation remain G4-owned actions. G5 may show read-only outline context only.

**Rationale:** Current domain meaning places outline closure inside G4 evidence-and-outline work. This removes the contradiction between G4 action ownership and G5 active-state mapping by making operational ownership explicit. It also prevents duplicate control surfaces across gates.

**Alternatives considered:**
- Make G5 the outline owner: rejected because it would split evidence and outline closure across gates and complicate G4 completion semantics.
- Allow both G4 and G5 to mutate outline: rejected because it creates duplicated workflows and ambiguous acceptance behavior.

### 2. Latest-only selection uses version-first, updatedAt-second semantics
**Decision:** Latest record selection SHALL use greatest `version`, then greatest `updatedAt` as tie-breaker. Array order is never authoritative.

**Rationale:** Current code often takes the array tail as latest, which is unstable if backend ordering changes. A deterministic selector is required for claims, outlines, and drafts so grouping and visibility rules remain stable.

**Alternatives considered:**
- `updatedAt` only: rejected because versioned resources already encode domain ordering.
- Array tail: rejected because it is transport-order dependent and unsafe.

### 3. System sections are the single section identity source
**Decision:** G4 and G5 section identity comes from system sections only. Empty sections remain visible as empty states or waiting states.

**Rationale:** System sections are the stable cross-layer contract. Outline sections and draft content can vary in shape, but section identity for workbench grouping and action affordances must remain consistent even when claims, bindings, or drafts are absent.

**Alternatives considered:**
- Outline-defined sections: rejected because it would over-couple section identity to outline lifecycle.
- Mixed derivation: rejected because it introduces inconsistent grouping behavior and hidden edge cases.

### 4. G5 grouping uses a single deterministic classifier
**Decision:** G5 sections are grouped into `approved`, `needs_review`, and `ready_to_generate` with this priority: latest approved draft → approved; latest non-approved draft → needs_review; no draft → ready_to-generate.

**Rationale:** This removes implementation-time judgment about comments, earlier versions, or ad hoc sorting. It also keeps grouping aligned with backend latest-draft truth rather than with transient UI signals.

**Alternatives considered:**
- Add a fourth blocked group: rejected because blocked reasons are better expressed as local disabled-action explanations.
- Drive groups from review comments or latest decision text: rejected because draft status is the stronger canonical state.

### 5. Local inline feedback is the only feedback channel for this change
**Decision:** G4/G5 actions use panel-local inline feedback only. Each action defines pending, success, and error states locally, with success clearing on next authoritative refresh or next user action.

**Rationale:** The repository already uses inline error rendering and has no global notification layer. Keeping feedback local reduces scope and aligns with current component architecture.

**Alternatives considered:**
- Add global toast notifications: rejected as unnecessary architecture expansion.
- Persist feedback beyond authoritative refresh: rejected because refreshed truth should supersede transient local success states.

### 6. Missing claim evidence-link read model remains a risk, not a default API addition
**Decision:** The change will not introduce backend API changes by default. Claim-level “bound/unbound” visibility must be expressed only to the degree currently supported by existing query data and mutation results.

**Rationale:** Proposal scope explicitly avoids backend API expansion. The UI can still improve clarity with bounded visibility cues and explicit helper messaging without assuming unavailable historical truth.

**Alternatives considered:**
- Add a new claim evidence-link read endpoint immediately: rejected as scope expansion.
- Pretend the frontend already has full claim-level binding truth: rejected as inaccurate and brittle.

### 7. Minimum automated acceptance is panel-level smoke coverage
**Decision:** Minimum automated acceptance is defined at the panel/render level using Vitest with JSDOM and React Testing Library rather than full route-level or Playwright-first E2E.

**Execution shape locked for implementation:**
- The minimum baseline renders `EvidenceMatrixPanel` and `DraftPanel` directly, not the full system route.
- The harness uses QueryClient-backed providers plus contract-shaped fixtures aligned with existing frontend hooks and API response types.
- Playwright remains a follow-up expansion path and is not part of the minimum completion definition for Phase 4.
- Fixture data must avoid unresolved three-way ties for latest selection (same logical key, same version, same updatedAt) because the current selector contract does not define a third tie-break.
- The baseline proves authoritative truth through a dual-surface model: artifact existence comes from refreshed resource reads, while gate/progress truth comes from workflow snapshot refreshes.

**Rationale:** The current frontend package has no production-ready test runner or Playwright baseline scripts. Panel-level smoke coverage is the smallest realistic baseline that still verifies required regions, grouping, latest-selection rules, inline feedback, and async-truth assumptions.

**Alternatives considered:**
- Route-level smoke as the minimum: rejected as larger surface with little additional planning value.
- Full Playwright-first baseline: rejected because the repository lacks complete Playwright setup and would turn acceptance work into infrastructure work.

### 8. Panel smoke harness is contract-shaped and direct-rendered
**Decision:** The minimum Phase 4 harness renders `EvidenceMatrixPanel` and `DraftPanel` directly with QueryClient-backed providers and contract-shaped fixtures instead of route-level assembly.

**Rationale:** The panels currently call hooks directly (`frontend/components/gates/EvidenceMatrixPanel.tsx:253`, `frontend/components/gates/DraftPanel.tsx:453`), while the shared QueryClient entrypoint is minimal (`frontend/lib/query.ts:0`). Direct panel rendering preserves the intended panel-level scope, avoids forcing `MainShell`/system-page composition into the minimum baseline, and still allows fixtures to follow the real hook and transport contracts.

**Constraints:**
- The baseline fixture layer must align with existing hook response types from `frontend/hooks/useEvidence.ts` and `frontend/hooks/useDrafts.ts`.
- The initial harness must include QueryClient-backed test providers and only the minimal browser/runtime mocks required for semantic DOM assertions.
- The minimum baseline must avoid layout-metric assertions and browser-only rendering requirements that would force escalation to Playwright.

## Risks / Trade-offs
- **[Claim evidence-link truth is incomplete at read time]** → Mitigation: specify bounded visibility requirements only; treat missing read model as a recorded risk/candidate dependency rather than implementation assumption.
- **[Current gate mapping contains semantic tension around `Outline_Ready`]** → Mitigation: lock outline ownership to G4 in specs and require implementation to reconcile presentation without expanding action ownership.
- **[Local snapshot patching can race against authoritative refresh]** → Mitigation: require specs and tests to prioritize refreshed workflow/resource truth over optimistic local state.
- **[Inline styles keep files verbose and harder to audit]** → Mitigation: limit this change to additive refinement within current files or carefully scoped subcomponents, without introducing a second styling system.
- **[Panel-level smoke coverage may miss route integration regressions]** → Mitigation: document route-level and Playwright paths as future expansion paths while keeping the minimum baseline realistic.
- **[Latest-only mental model hides history in the main UI]** → Mitigation: record old-version handling as out-of-scope for main UI while keeping deterministic latest selection explicit.

## Migration Plan

This change is planning-only at this phase, so there is no deployment or rollback procedure yet. Implementation should follow these sequencing constraints:
1. Introduce deterministic latest-selection helpers before changing visible grouping.
2. Refine G4 ownership and grouping behavior before G5 grouping and preview changes.
3. Add acceptance harness support before wiring final smoke assertions.
4. Keep all backend contracts unchanged unless implementation proves a hard blocker and the change is explicitly re-scoped.

## Implementation Handoff Notes

- Minimum automated acceptance now runs at panel scope from `frontend/` via `npm run test:smoke` and uses `Vitest + JSDOM + React Testing Library`, matching the locked Phase 4 baseline.
- The direct-render harness lives in `frontend/vitest.config.ts`, `frontend/vitest.setup.ts`, `frontend/components/gates/testUtils.tsx`, and `frontend/components/gates/testFixtures.ts`.
- The smoke suites are `frontend/components/gates/EvidenceMatrixPanel.test.tsx` and `frontend/components/gates/DraftPanel.test.tsx`; they render the panels directly with QueryClient-backed providers and contract-shaped fixtures rather than routing through `MainShell` or the system page.
- G4 smoke coverage proves visible claims/outline/binding regions, approved-versus-pending latest grouping, resource-derived known binding cues, version-first plus updatedAt-second latest selection, and the rule that workflow refresh may advance gate/progress truth before refreshed outline resources make artifacts visible.
- G5 smoke coverage proves approved / needs-review / ready-to-generate grouping, collapsed-by-default preview behavior, visible decision markers, disabled-helper priority, latest-selection stability for non-sorted draft fixtures, and local success feedback clearing only after refreshed draft truth replaces transient UI state.
- Verified commands for this baseline are `npm --prefix "F:/Vibe-writing/frontend" run test:smoke` and `npm --prefix "F:/Vibe-writing/frontend" run typecheck`.
- Backend contract assumptions remain unchanged and continue to align with `backend/tests/modules/evidence/test_evidence_api.py` and `backend/tests/modules/drafts/test_drafts_api.py`: generation endpoints return `202 Accepted`, artifact truth arrives later through refreshed resource reads, workflow truth arrives through refreshed workflow snapshots, and websocket delivery may be absent without invalidating the final rendered state.

## Open Questions

- None for planning. The remaining previously open questions are explicitly resolved by default decisions in this design: G4 owns outline lifecycle, latest means version-first then updatedAt, system sections are the sole section source, and minimum automated acceptance is panel-level smoke coverage.
