# Type Safety

> Type safety patterns in this project.

---

## Overview

The frontend is TypeScript-first and keeps type boundaries close to where data enters the UI.

The current codebase uses:

- explicit object types for props and domain models
- `Readonly<{ ... }>` for many props declarations
- generic helpers such as `apiRequest<T>()`
- raw transport types plus normalized UI-facing types in hook files

---

## Type Organization

The real organization pattern is local-to-domain, not one giant shared `types.ts`.

Examples:

- `frontend/hooks/useProjectStatus.ts` defines `RawWorkflowSnapshot`, `WorkflowSnapshot`, `RawBlocker`, `Blocker`, and related normalizers
- `frontend/hooks/useSystemAdvance.ts` defines `RawAdvanceResponse`, `AdvanceResponse`, and job-handle mappings
- `frontend/hooks/useProjects.ts` exports project and system DTOs consumed by pages and components
- components import domain types from hooks instead of cloning them locally

This repository currently prefers colocating types with the hook or component that owns the contract.

---

## Validation

Runtime validation is lightweight right now.

Current reality:

- backend response shape is trusted at the `apiRequest<T>()` boundary
- hooks often normalize and narrow data manually instead of using a schema library
- WebSocket frames are checked with explicit runtime guards in `frontend/lib/websocket.ts`
- form validation is manual and local, for example JSON parsing and required-field checks in `SystemDefinitionForm.tsx`

So the real documented rule is not “use Zod everywhere.” The real rule is “validate where the transport boundary is risky, and normalize before UI consumption.”

---

## Common Patterns

Current strong patterns include:

- `Raw*` transport types paired with normalized UI types
- `Record<string, unknown>` for open-ended JSON payloads
- readonly array/object props where mutation should be prevented by convention
- discriminated string unions for visual or transport state, for example `GateVisualStatus` and `TaskStatus`
- generic request helpers such as `apiRequest<T>()`

Reference files:

- `frontend/lib/api.ts`
- `frontend/lib/websocket.ts`
- `frontend/hooks/useProjectStatus.ts`
- `frontend/hooks/useSystemAdvance.ts`
- `frontend/components/layout/GateNav.tsx`

---

## Forbidden Patterns

Avoid these patterns:

- `any` for domain payloads that already have a stable shape in the repo
- duplicating raw snake_case API types inside multiple components
- mutating props or cached objects in place
- skipping runtime checks for untrusted WebSocket frames
- inventing fake shared type layers that are not actually used by the repository
