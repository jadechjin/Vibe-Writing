## Context

Phase 5 (G4-G5 async closure) implemented async generation for four key workflows:
- **G1**: Figure Plan generation
- **G4**: Evidence Matrix generation (Claims + Evidence Links) and Outline generation
- **G5**: Section Draft generation

The implementation is complete and operational. This design document analyzes the architectural patterns, technical decisions, and constraints discovered during implementation to serve as a reference for future async generation features.

**Current State**:
- Backend: `evidence` and `drafts` modules with three-phase async generation
- Frontend: G4/G5 panels integrated into GatePanel with React Query state management
- Infrastructure: Thin workflow + task event model with WebSocket real-time feedback

**Stakeholders**:
- Future developers implementing similar async generation features
- Architects evaluating async workflow patterns
- QA engineers understanding success criteria and failure modes

## Goals / Non-Goals

**Goals:**
- Document the three-phase async generation pattern (`generate_*` → `run_*_generation_task` → `complete_*_generation`)
- Extract hard and soft constraints from the implementation
- Identify risks and mitigation strategies
- Establish success criteria for similar async workflows
- Provide reusable patterns for frontend-backend integration

**Non-Goals:**
- Modify or refactor existing Phase 5 code
- Implement new features or capabilities
- Change the thin workflow architecture
- Add durable worker/queue infrastructure

## Decisions

### Decision 1: Three-Phase Async Generation Pattern

**Choice**: Standardize on `generate_*` → `run_*_generation_task` → `complete_*_generation` pattern

**Rationale**:
- **Phase 1 (generate_*)**: Validates inputs, creates workflow instance, returns 202 + JobHandle
- **Phase 2 (run_*)**: Spawns background task with fresh DB session, delays 50ms, calls complete
- **Phase 3 (complete_*)**: Checks workflow still queued (idempotency), creates business records, appends success/failure events

**Alternatives Considered**:
- **Single-phase sync generation**: Rejected - blocks HTTP request, no progress feedback
- **Two-phase (generate + complete)**: Rejected - loses session isolation boundary
- **Durable worker queue**: Rejected - adds infrastructure complexity, not needed for current scale

**Trade-offs**:
- ✅ Simple to implement and understand
- ✅ Works with existing thin workflow model
- ❌ No durability - process restart loses in-flight tasks
- ❌ No retry mechanism for transient failures

### Decision 2: Session Binding Pattern

**Choice**: Use `get_*_task_session_bind()` to extract bind object and rebuild session in background task

**Rationale**:
- Background tasks cannot reuse request session (connection pool exhaustion)
- Need fresh session with same engine/bind for transaction isolation
- Support both AsyncSession and sync Session for flexibility

**Implementation**:
```python
bind, use_async_session = get_evidence_task_session_bind(session)
asyncio.create_task(
    run_figure_plan_generation_task(
        bind=bind,
        use_async_session=use_async_session,
        workflow_id=result.handle.workflow_id,
        ...
    )
)
```

**Alternatives Considered**:
- **Reuse request session**: Rejected - connection pool issues, transaction conflicts
- **Global session factory**: Rejected - loses per-request configuration

### Decision 3: Workflow Idempotency Protection

**Choice**: Check `workflow.status == QUEUED` before executing complete phase

**Rationale**:
- Prevents duplicate execution if task is triggered multiple times
- Allows safe retry without side effects
- Protects against race conditions

**Implementation**:
```python
workflow_snapshot = await task_service.get_workflow_snapshot(workflow_id)
if workflow_snapshot is None or workflow_snapshot.status != TaskStatus.QUEUED:
    return  # Already processed or invalid
```

**Alternatives Considered**:
- **Database-level locks**: Rejected - adds complexity, potential deadlocks
- **No protection**: Rejected - duplicate records, inconsistent state

### Decision 4: Input Snapshot Strategy

**Choice**: Section Draft snapshots claim_ids in workflow context; others read latest DB state

**Rationale**:
- **Section Draft**: User explicitly selects claims → must honor selection even if claims change later
- **Figure Plan/Evidence Matrix/Outline**: Generated from current system state → should reflect latest data

**Trade-offs**:
- ✅ Section Draft behavior matches user expectations
- ❌ Inconsistent snapshot strategy across workflows
- ❌ Figure Plan/Evidence Matrix/Outline vulnerable to input drift

**Open Question**: Should Outline also snapshot approved claim IDs for consistency?

### Decision 5: Frontend State Management

**Choice**: Separate hooks (`useEvidence`, `useDrafts`) with namespaced React Query keys

**Rationale**:
- Isolates G4 and G5 state management
- Prevents query key collisions
- Allows independent invalidation strategies
- Keeps `useProjectStatus` focused on workflow/gate state

**Implementation**:
```typescript
// useEvidence.ts
const queryKey = ['evidence', 'figure-plans', systemId];
const { data } = useQuery(queryKey, () => api.listFigurePlans(systemId));

// useDrafts.ts
const queryKey = ['drafts', 'outlines', systemId];
const { data } = useQuery(queryKey, () => api.listOutlines(systemId));
```

**Alternatives Considered**:
- **Single unified hook**: Rejected - too complex, tight coupling
- **Extend useProjectStatus**: Rejected - violates single responsibility

### Decision 6: Real-Time Feedback via WebSocket

**Choice**: Use `GateTaskStatus` component with `useWebSocketContext` for task progress

**Rationale**:
- Provides immediate feedback when generation starts
- Shows task status without polling
- Integrates with existing StatusTray infrastructure

**Trade-offs**:
- ✅ Real-time updates, better UX
- ❌ Requires WebSocket connection
- ❌ No fallback if WebSocket unavailable

**Open Question**: Should we add polling fallback for WebSocket failures?

## Risks / Trade-offs

### Risk 1: Durability

**Risk**: Process restart causes in-flight workflows to stay in `queued` state forever

**Mitigation**:
- Add workflow timeout detection (e.g., mark as failed after 5 minutes)
- Implement recovery job to clean up stale workflows
- Consider durable queue if scale increases

### Risk 2: Evidence Failure Path Inconsistency

**Risk**: Evidence module doesn't rollback on failure, may leave partial records + workflow failed

**Mitigation**:
- Add `session.rollback()` in evidence failure handlers (align with drafts)
- Add integration tests for failure scenarios
- Document expected behavior in specs

### Risk 3: Concurrent Version Conflicts

**Risk**: Rapid repeated clicks create multiple workflow instances with version collisions

**Mitigation**:
- Frontend: Disable generate button while workflow is queued
- Backend: Add unique constraint check and return existing workflow if duplicate
- Consider advisory locks for version allocation

### Risk 4: Input Drift

**Risk**: Figure Plan/Evidence Matrix/Outline read latest DB state, may differ from accepted request

**Mitigation**:
- Document this behavior as intentional (reflects current system state)
- Consider snapshotting inputs if consistency is critical
- Add tests to verify behavior matches expectations

### Risk 5: Frontend Race Conditions

**Risk**: Manual `setQueryData` and background refetch may conflict

**Mitigation**:
- Use React Query's optimistic updates mechanism
- Rely on query invalidation rather than manual updates
- Add version/timestamp checks to detect stale data

### Risk 6: WebSocket Event Loss

**Risk**: If WebSocket events are missed or arrive out of order, UI may be inconsistent

**Mitigation**:
- Use `workbenchSelectors.ts` deduplication and versioning logic
- Add polling fallback for critical state updates
- Implement event sequence numbers for ordering

## Migration Plan

**Not Applicable** - This is a documentation-only change. No migration needed.

## Open Questions

1. **Outline Input Snapshot**: Should Outline generation snapshot approved claim IDs like Section Draft does?
   - **Impact**: Consistency vs. flexibility trade-off
   - **Decision Needed**: Before implementing similar workflows

2. **Evidence Rollback**: Should evidence failure handlers add `session.rollback()` to match drafts?
   - **Impact**: Data consistency in failure scenarios
   - **Decision Needed**: Before next release

3. **Event Granularity**: Should we add `task.started` / `task.progress` events for better observability?
   - **Impact**: More events = better UX but more complexity
   - **Decision Needed**: Based on user feedback

4. **WebSocket Fallback**: Should we implement polling fallback if WebSocket is unavailable?
   - **Impact**: Reliability vs. complexity
   - **Decision Needed**: Based on production metrics

5. **Durability Strategy**: At what scale should we migrate to durable worker/queue?
   - **Impact**: Infrastructure complexity vs. reliability
   - **Decision Needed**: Monitor production load and failure rates
