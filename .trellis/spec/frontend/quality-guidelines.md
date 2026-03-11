# Quality Guidelines

> Code quality standards for frontend development.

---

## Overview

Frontend quality in this repository means preserving the current shell/workbench architecture, keeping state boundaries clear, and maintaining transport normalization inside hooks.

Current tooling baseline from `frontend/package.json` is modest but real:

- Next.js build scripts
- TypeScript typecheck via `npm run typecheck`

There is no declared lint or frontend test script in `frontend/package.json` yet, so do not document imaginary enforcement. Document the actual baseline and extend it only when the repo really adds those tools.

---

## Forbidden Patterns

Avoid these patterns because they fight the codebase that already exists:

- network fetching inside layout-only components like `MainShell` or `ProjectWorkspace`
- pushing raw snake_case API responses directly into presentation components
- adding a separate global state library for page-local workflow concerns
- pretending every route should share the same shell layout
- introducing a second styling system for isolated files when the repository uses inline `CSSProperties`
- inventing a central normalizer file that does not exist in the repo

---

## Required Patterns

New frontend work should preserve these patterns:

- root layout only wraps `Providers`
- the system workspace page assembles data hooks and passes slot props into `MainShell`
- hooks own queries, mutations, normalization, and invalidation
- layout components receive already-prepared data and stay prop-driven, while gate-specific feature panels may call their own domain hooks when the logic is tightly scoped to that panel
- shared transport access goes through `frontend/lib/api.ts` and `frontend/lib/websocket.ts`
- props are explicitly typed, often with `Readonly<{ ... }>`

Reference files:

- `frontend/app/layout.tsx`
- `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx`
- `frontend/hooks/useProjectStatus.ts`
- `frontend/hooks/useSystemAdvance.ts`
- `frontend/components/layout/MainShell.tsx`

---

## Testing Requirements

The current documented baseline is:

- frontend changes should continue to pass TypeScript checking
- for cross-layer workflow UI, verify that invalidation and derived state still match backend workflow truth
- when adding new complex logic to hooks or transport helpers, prefer adding tests only when the repo actually introduces a frontend test runner

Because there is no frontend test script yet, reviewers should rely on:

- `typecheck`
- route-level smoke verification
- checking that server-state invalidation paths still make sense

---

## Code Review Checklist

Reviewers should check:

- does this component fetch data it should have received as props?
- is raw transport data normalized in the hook before hitting UI?
- are query invalidation rules still correct after a mutation?
- does the change preserve the existing MainShell / EvidenceHub / GatePanel / StatusTray composition?
- did the author avoid inventing architecture that is not already present, such as a global store or central normalizer layer?
- does the change still pass TypeScript checks?
