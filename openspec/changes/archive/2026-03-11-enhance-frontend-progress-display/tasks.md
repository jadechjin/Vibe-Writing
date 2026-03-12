## 1. Shared task-stream foundation

- [x] 1.1 Create `frontend/contexts/WebSocketContext.tsx` to own a single provider-managed task-stream connection, connection state, and bounded recent event list for the system workspace.
- [x] 1.2 Refactor `frontend/hooks/useWebSocket.ts` to consume shared provider state while preserving scoped filtering by `projectId` and `systemId`.
- [x] 1.3 Preserve existing event merge semantics by `taskId`, bounded history behavior, and reconnect state handling under the shared provider model.

## 2. Task-to-gate mapping and navigation state

- [x] 2.1 Add `frontend/lib/gateMapping.ts` with prefix-based task type to gate key resolution for `figure_plan.*`, `analysis.*`, `manifest.*`, `evidence.*`, and `draft.*`.
- [x] 2.2 Add client-side `selectedGate` override state in `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx` and wire task-driven gate selection without mutating authoritative workflow state.
- [x] 2.3 Update gate rendering flow so invalid or cleared overrides fall back to authoritative workflow gate truth.

## 3. Status tray UI refinement

- [x] 3.1 Update `frontend/components/tasks/TaskItem.tsx` to render compact status metadata including task type label, progress indicator, and percentage text when available.
- [x] 3.2 Update `frontend/components/tasks/StatusTray.tsx` to use the shared task-stream provider, keep the tray bounded/non-blocking, and expose activation affordances only for mapped tasks.
- [x] 3.3 Ensure unmapped task rows remain visible as read-only items and mapped task rows trigger selected-gate navigation through the page-level handler.

## 4. Gate-local progress indicators

- [x] 4.1 Create `frontend/components/gates/GateTaskStatus.tsx` to render compact active-task status for the currently displayed gate using shared task-stream data.
- [x] 4.2 Integrate `GateTaskStatus` near the top of each applicable G1-G5 gate workbench panel and restrict visibility to active tasks for the current system and current gate.
- [x] 4.3 Update `frontend/components/gates/GatePanel.tsx` to honor a valid `selectedGate` override while preserving fallback to authoritative gate selection.

## 5. Verification

- [x] 5.1 Add or update focused frontend tests for provider reuse, task-type mapping, task navigation behavior, and gate-local active-task filtering.
- [x] 5.2 Run `npm run typecheck` in `frontend` and fix any type regressions introduced by the progress-display changes.
- [x] 5.3 Run `npm run test:smoke` in `frontend` and fix any failures to confirm progress-display changes preserve existing panel smoke behavior.
