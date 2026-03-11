# State Management

> How state is managed in this project.

---

## Overview

This frontend currently uses a simple split:

- server state in React Query
- local UI/form state in component `useState`
- derived display state in hook helpers or `useMemo`
- realtime task state inside `useWebSocket`

There is no dedicated global client-state library like Redux or Zustand in the current repository.

---

## State Categories

### Local state

Use local component state for temporary form and interaction state.

Reference example:

- `frontend/components/gates/SystemDefinitionForm.tsx`
  - owns textarea values in `useState`
  - tracks JSON validation error locally
  - derives missing fields with `useMemo`

### Server state

Use React Query for API-backed state.

Reference examples:

- `useProjects.ts`
- `useSystem.ts`
- `useProjectStatus.ts`
- `useEvidence.ts`
- `useDrafts.ts`

### Derived state

Keep derived state close to where the underlying source lives.

Examples:

- `deriveGateItems(...)` in `useProjectStatus.ts`
- `resolveWorkbenchContent(...)` in `GatePanel.tsx`
- `resolveEvidenceContent(...)` in `EvidenceHub.tsx`

### Realtime task state

Realtime status is encapsulated by `useWebSocket.ts`, which stores connection state and a bounded event list.

---

## When to Use Global State

Right now, almost never.

The current codebase does not maintain a shared client-side global store. Before introducing one, ask whether the state can stay in one of these places instead:

- React Query cache if it comes from the server
- route params if it comes from navigation
- local component state if only one panel or form needs it
- a focused custom hook if multiple nearby components share stateful logic

If the state is only needed on the system workspace page, it usually belongs in that page’s hooks and props composition, not in a global store.

---

## Server State

Current server-state rules:

- fetch with React Query hooks
- normalize transport data inside the hook
- invalidate affected query keys on mutation success
- use small targeted cache patches only when the repo already has a proven pattern for it

Examples:

- `useProjectStatus.ts` normalizes workflow payloads before components consume them
- `useSystemAdvance.ts` invalidates workflow after advance
- `useEvidence.ts` and `useDrafts.ts` invalidate feature-specific queries and workflow together when needed

---

## Common Mistakes

Avoid these mistakes:

- duplicating server data into local component state without a good reason
- creating a global store for page-local concerns
- scattering transport normalization across components instead of hooks
- optimistic updates that pretend the workflow advanced when the backend is still the source of truth
- letting realtime event lists grow unbounded instead of capping them like `MAX_EVENTS` in `useWebSocket.ts`
