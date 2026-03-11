# Hook Guidelines

> How hooks are used in this project.

---

## Overview

Hooks are the main home for frontend data access, response normalization, React Query integration, and reusable stateful logic.

In this codebase, hooks are not just thin `fetch()` wrappers. They usually own:

- query keys
- request/mutation wiring
- transport-to-UI normalization
- cache invalidation
- limited optimistic or local snapshot patching when necessary

Reference files:

- `frontend/hooks/useProjectStatus.ts`
- `frontend/hooks/useSystemAdvance.ts`
- `frontend/hooks/useSystem.ts`
- `frontend/hooks/useProjects.ts`
- `frontend/hooks/useEvidence.ts`
- `frontend/hooks/useDrafts.ts`
- `frontend/hooks/useWebSocket.ts`

---

## Custom Hook Patterns

Current stable patterns include:

- one hook file per domain concern
- local query key factory near the hook definitions
- exported domain types from the same hook file when they are mainly consumed by that area
- helper functions inside the hook file for normalization and derived-state mapping

Examples:

- `useProjectStatus.ts` defines raw transport types, normalized UI types, normalizer helpers, gate derivation, and the query hook in one file
- `useSystemAdvance.ts` normalizes mixed camelCase/snake_case backend responses before UI consumption
- `useWebSocket.ts` encapsulates filtering, buffering, and callback wiring instead of exposing raw socket behavior to components

---

## Data Fetching

Server state is managed with React Query.

Current data-fetching conventions:

- use `useQuery` for reads and `useMutation` for writes
- keep domain query keys close to the hook file
- call the shared `apiRequest<T>()` wrapper from `frontend/lib/api.ts`
- invalidate affected queries in `onSuccess`
- only patch cached workflow state locally when the UI benefit is clear and the scope is tightly controlled

Real examples:

- `frontend/hooks/useDrafts.ts` invalidates both draft and workflow queries after mutations
- `frontend/hooks/useSystem.ts` invalidates system detail and workflow queries after patching a system
- `frontend/hooks/useEvidence.ts` uses `setQueryData(...)` to apply a constrained workflow snapshot update

---

## Naming Conventions

- hook names always start with `use`
- hook files are named after the exported primary hook set, for example `useProjectStatus.ts`
- query key helpers use plural domain nouns where appropriate, for example `draftKeys`, `evidenceKeys`, `systemKeys`, `projectKeys`
- raw transport types are prefixed with `Raw*` when the normalized type is also exported

The `Raw* -> normalized` pattern in `useProjectStatus.ts` and `useSystemAdvance.ts` is the clearest current naming baseline.

---

## Common Mistakes

Do not introduce these patterns:

- parsing raw API shapes separately inside multiple components
- putting query keys in unrelated global files when they are only used by one feature area
- invalidating nothing after a successful mutation
- using hooks as giant dumping grounds for unrelated domains
- exposing raw WebSocket events or raw snake_case API shapes directly to presentation components when a hook already owns the conversion boundary
