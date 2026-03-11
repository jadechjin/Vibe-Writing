# Directory Structure

> How frontend code is organized in this project.

---

## Overview

The frontend uses Next.js App Router and keeps responsibilities split by route, component area, hook, and low-level runtime utility.

The stable top-level layout is:

- routes in `frontend/app/*`
- reusable UI in `frontend/components/*`
- domain and transport hooks in `frontend/hooks/*`
- shared request/socket/query utilities in `frontend/lib/*`

Only the system workspace route uses the MainShell workbench layout. Project list and project detail pages stay as independent pages instead of being forced through the shell.

---

## Directory Layout

```text
frontend/  (representative, non-exhaustive)
├── app/
│   ├── layout.tsx
│   └── projects/
│       ├── page.tsx
│       ├── [projectId]/page.tsx
│       └── [projectId]/systems/[systemId]/page.tsx
├── components/
│   ├── layout/
│   ├── gates/
│   ├── evidence/
│   ├── drafting/
│   └── tasks/
├── hooks/
│   ├── useProjectStatus.ts
│   ├── useSystemAdvance.ts
│   ├── useSystem.ts
│   ├── useProjects.ts
│   ├── useFigurePlan.ts
│   ├── useAnalysis.ts
│   ├── useManifest.ts
│   ├── useEvidence.ts
│   ├── useDrafts.ts
│   └── useWebSocket.ts
└── lib/
    ├── api.ts
    ├── providers.tsx
    ├── query.ts
    └── websocket.ts
```

---

## Module Organization

Current frontend organization is responsibility-first, not feature-folder maximalism.

- `frontend/app/layout.tsx` only wraps `Providers` and page chrome basics.
- route files in `frontend/app/*` assemble page-level hooks and panels.
- `frontend/components/layout/*` contains shell and layout primitives such as `MainShell`, `GateNav`, and `ProjectWorkspace`.
- `frontend/components/gates/*` contains gate-specific workbench panels.
- `frontend/components/evidence/*` contains evidence-side presentation.
- `frontend/components/tasks/*` contains realtime task tray rendering.
- `frontend/hooks/*` owns data fetching, mutations, invalidation, normalization, and reusable stateful logic.
- `frontend/lib/*` is reserved for low-level shared utilities like request wrappers, QueryClient wiring, and raw WebSocket management.

A real page assembly example is `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx`, which composes hooks and passes ready-to-render panels into `MainShell`.

---

## Naming Conventions

- directories and files use `camelCase` or route-segment naming already established by Next.js
- React components use PascalCase exports and file names such as `MainShell.tsx`, `GatePanel.tsx`, `StatusTray.tsx`
- hooks use `use*` naming, for example `useProjectStatus.ts`, `useDrafts.ts`, `useWebSocket.ts`
- low-level browser/runtime helpers stay under `frontend/lib/*`
- route directories follow App Router conventions like `[projectId]` and `[systemId]`

Important real convention: there is no shared `frontend/lib/normalizers.ts` file right now. Normalization logic lives inside the relevant hooks such as `useProjectStatus.ts` and `useSystemAdvance.ts`.

---

## Examples

Use these files as the strongest current references:

- `frontend/app/layout.tsx` — root layout boundary
- `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx` — page assembly pattern
- `frontend/components/layout/MainShell.tsx` — shell composition by slots
- `frontend/components/layout/ProjectWorkspace.tsx` — layout container without data fetching
- `frontend/hooks/useProjectStatus.ts` — workflow query + normalization + derived gate items
- `frontend/lib/api.ts` — shared API wrapper boundary

Anti-patterns to avoid:

- putting network requests inside layout-only components
- forcing every route through `MainShell`
- inventing a fake shared normalizer layer that does not exist in the repo
- mixing raw transport parsing into many components instead of centralizing it in hooks
