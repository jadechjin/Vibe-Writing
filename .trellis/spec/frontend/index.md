# Frontend Development Guidelines

> Best practices for frontend development in this project.

---

## Overview

These documents describe the frontend as it exists today: Next.js App Router pages, a slot-driven `MainShell` workbench used only by the system workspace route, hook-owned normalization for workflow, advance, and other complex transport responses, React Query for server state, and inline `CSSProperties` styling.

Some feature hooks still expose backend-style snake_case job handles directly, so these guides describe a mixed but intentional boundary rather than an all-or-nothing normalization rule.

Use these guides to preserve the current workbench architecture instead of introducing a parallel UI or state-management model.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Route, component, hook, and low-level `lib` boundaries in the App Router frontend | Documented |
| [Component Guidelines](./component-guidelines.md) | Prop typing, slot composition, inline styles, and layout-versus-feature-panel boundaries | Documented |
| [Hook Guidelines](./hook-guidelines.md) | React Query hooks, normalization patterns, mutations, and invalidation rules | Documented |
| [State Management](./state-management.md) | Local component state, React Query server state, and realtime event state | Documented |
| [Quality Guidelines](./quality-guidelines.md) | Real enforcement baseline, architectural guardrails, and review checklist | Documented |
| [Type Safety](./type-safety.md) | Raw-to-normalized type patterns, transport boundaries, and runtime checks | Documented |

---

## Recommended Reading Order

1. [Directory Structure](./directory-structure.md)
2. [Quality Guidelines](./quality-guidelines.md)
3. [Component Guidelines](./component-guidelines.md)
4. [Hook Guidelines](./hook-guidelines.md)
5. [State Management](./state-management.md)
6. [Type Safety](./type-safety.md)

---

## Scope Notes

These guides intentionally document current reality from files such as:

- `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx`
- `frontend/components/layout/MainShell.tsx`
- `frontend/components/layout/ProjectWorkspace.tsx`
- `frontend/components/gates/GatePanel.tsx`
- `frontend/hooks/useProjectStatus.ts`
- `frontend/lib/api.ts`

When the frontend architecture changes, update the affected guide so the index stays aligned with the codebase.
