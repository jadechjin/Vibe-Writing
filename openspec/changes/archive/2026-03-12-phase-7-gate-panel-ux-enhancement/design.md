## Context

G1-G5 gate panels were implemented as "minimally viable" in Phase 1-6. Each panel independently defines identical CSSProperties constants (9 duplicated style objects), has no shared UI primitives, no real-time progress feedback (backend `TaskEvent.progress` field exists but frontend ignores it), no batch operations, no toast notifications, and no confirm dialogs.

Current state:
- 5 gate panels each define their own `panelStyle`, `sectionCardStyle`, `titleStyle`, `descStyle`, `actionBtnStyle`, `statusBadgeStyle`, `emptyStateStyle`, `fieldGroupStyle`, `inputStyle`
- `GateTaskStatus` shows a spinner but no progress bar
- Claims and assets can only be approved/confirmed one at a time
- No user feedback on operation success/failure

## Goals / Non-Goals

**Goals:**
- Eliminate style duplication across 5 gate panels via shared `gate-theme.ts`
- Create reusable UI primitives in `frontend/components/ui/` (global, not gate-specific)
- Add indeterminate progress bar to `GateTaskStatus` (no backend changes needed)
- Add batch approve for claims (G4) and batch confirm QC for assets (G3)
- Add toast notifications and confirm dialogs for destructive/important actions
- Add empty state guidance in panels

**Non-Goals:**
- No new external UI library dependencies (continue with inline CSSProperties)
- No real TASK_PROGRESS events from backend (indeterminate animation is sufficient)
- No changes to WebSocket infrastructure or event routing
- No changes to gate transition logic or system state machine

## Decisions

### D1: UI Primitives Location — `frontend/components/ui/` (global)

Alternatives considered:
- `frontend/components/gates/ui/` (gate-specific): Better isolation but prevents reuse in future non-gate pages
- `frontend/components/ui/` (global): Chosen. These primitives (ActionButton, SectionCard, etc.) are generic enough to be reused across the app. The project already has `frontend/components/` as the component root.

### D2: Batch Failure Strategy — Partial Success

Each claim/asset is processed independently. Response shape:
```
{ succeeded: string[], failed: { id: string, error: string }[] }
```

Alternatives considered:
- Atomic (all-or-nothing): Simpler but poor UX — 1 invalid claim out of 10 blocks all approvals
- Partial success: Chosen. Matches user expectation that valid items should proceed. Frontend shows per-item failure in toast.

For `batch_approve_claims`, section_ref validation is pre-fetched once (single query for all valid section keys), then applied per-claim without extra DB round trips.

### D3: Progress Bar — Indeterminate Animation (no backend changes)

Generation tasks (figure plan, evidence matrix, outline, section drafts) are "thin workflow" — they complete in milliseconds to seconds. Adding real TASK_PROGRESS events would require instrumenting each task at arbitrary milestones with no meaningful semantic value.

Decision: `GateTaskStatus` shows a CSS-animated indeterminate bar (30% width, sliding left-to-right) when `status === "running"`. On `TASK_SUCCEEDED`, bar jumps to 100% briefly then hides. No backend changes.

### D4: Toast Architecture — React Context + useToast Hook

`ToastProvider` added to `frontend/app/projects/[projectId]/layout.tsx` (already exists as a layout wrapper). Exposes `useToast()` hook with `showSuccess(msg)` and `showError(msg)`. Queue-based to handle overlapping toasts.

Alternatives considered:
- Global singleton (module-level): Simpler but breaks React's render lifecycle
- Per-component state: No global visibility, can't trigger from hooks
- React Context: Chosen. Clean, testable, no extra dependencies.

### D5: Batch Endpoint URL Design

```
POST /systems/{system_id}/claims/batch-approve
POST /systems/{system_id}/assets/batch-confirm-qc
```

Scoped to system_id for authorization clarity. Consistent with existing `/systems/{id}/claims` and `/systems/{id}/assets` patterns.

## Risks / Trade-offs

- [Style migration regression] Replacing inline styles with shared constants could introduce visual regressions if any panel had intentional overrides → Mitigation: Each primitive accepts optional `style?: CSSProperties` override prop; panels can pass overrides during migration
- [Batch partial failure UX] Users may be confused when some items succeed and others fail → Mitigation: Toast shows count of succeeded/failed with expandable error list
- [ToastProvider scope] If a gate panel is rendered outside the project layout, toasts won't work → Mitigation: All gate panels are under `[projectId]` layout; this is a non-issue for current routing
- [indeterminate bar flicker] If task completes very fast (< 200ms), the animation may flash → Mitigation: Add minimum display duration of 300ms before hiding

## Migration Plan

1. Create `frontend/styles/gate-theme.ts` with shared constants
2. Create `frontend/components/ui/` primitives (no panel changes yet)
3. Add `ToastProvider` to layout, create `useToast` hook
4. Update `GateTaskStatus` with indeterminate progress bar
5. Migrate panels one by one: FigurePlanPanel → AnalysisPanel → ManifestPanel (+batch QC) → EvidenceMatrixPanel (+batch approve) → DraftPanel
6. Add backend batch endpoints + tests
7. Add frontend batch hooks + wire into panels

Each step is independently deployable. Panels not yet migrated continue using their local styles.

## Open Questions

None — all decisions resolved in planning phase.
