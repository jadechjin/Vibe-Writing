## Why

Phase 5 (G4-G5 async closure) has been completed, but the implementation patterns and architectural decisions are not yet documented in a reusable format. This analysis extracts the key constraints, patterns, and success criteria from the existing implementation to serve as a reference for future similar features.

## What Changes

This is an **analysis-only change** - no code modifications. The goal is to document:

- The three-phase async generation pattern (`generate_*` → `run_*_generation_task` → `complete_*_generation`)
- Backend async generation implementation for Figure Plan, Evidence Matrix, Outline, and Section Draft
- Frontend G4/G5 workbench integration patterns
- React Query state management and invalidation strategies
- WebSocket-based real-time task feedback mechanisms
- Hard and soft constraints discovered in the implementation
- Known risks and mitigation strategies

## Capabilities

### New Capabilities

- `async-generation-pattern`: Documents the three-phase async generation pattern used in evidence and drafts modules
- `frontend-gate-integration`: Documents the GatePanel routing, React Query hooks, and WebSocket integration patterns
- `workflow-task-event-model`: Documents the thin workflow + task event persistence model

### Modified Capabilities

<!-- No existing capabilities are being modified - this is pure documentation -->

## Impact

**Documentation Impact**:
- Creates reusable reference documentation for async generation patterns
- Establishes constraints and conventions for future G-series implementations
- Provides success criteria for similar async workflows

**No Code Impact**:
- This change does not modify any source code
- All analysis is based on existing Phase 5 implementation
