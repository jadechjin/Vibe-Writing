## Why

Current frontend generation progress display lacks visibility and user control. Users cannot see task types, progress percentages, or navigate to relevant gate panels from the StatusTray. Gate panels also lack embedded status indicators for active generation tasks, making it hard to track ongoing operations at a glance.

## What Changes

- Refactor `useWebSocket` hook into a `WebSocketProvider` to share a single connection across the application
- Enhance `StatusTray` component to display task type badges, progress percentages, and clickable navigation to gate panels
- Create `GateTaskStatus` component with pulse animations to embed in gate panels (G1-G5)
- Add `selectedGate` state to `SystemPage` to support manual gate switching
- Implement `getGateKeyFromTaskType` helper function for task type to gate key mapping (prefix-based)
- Update `TaskItem` component to be clickable and trigger gate navigation
- Modify `GatePanel` to accept and respond to `selectedGate` prop

## Capabilities

### New Capabilities
- `websocket-provider`: Shared WebSocket connection management via React Context API
- `gate-task-status`: Embedded generation status indicators for gate panels with pulse animations
- `task-navigation`: Clickable task items that navigate to corresponding gate panels

### Modified Capabilities
- `status-tray`: Enhanced to show task types, progress percentages, and support navigation
- `gate-panel`: Modified to support manual gate selection via `selectedGate` prop

## Impact

**Affected Components**:
- `frontend/hooks/useWebSocket.ts` - Refactored to use Context
- `frontend/components/tasks/StatusTray.tsx` - Enhanced display and navigation
- `frontend/components/tasks/TaskItem.tsx` - Added click handler
- `frontend/components/gates/GatePanel.tsx` - Added `selectedGate` support
- `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx` - Added gate selection state

**New Files**:
- `frontend/contexts/WebSocketContext.tsx` - WebSocket Provider and Context
- `frontend/components/gates/GateTaskStatus.tsx` - Gate-specific task status component
- `frontend/lib/gateMapping.ts` - Task type to gate key mapping helper

**No Breaking Changes**: All changes are additive or internal refactoring. Existing components continue to work with enhanced functionality.
