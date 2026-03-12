## Context

**Current State:**
- G0-G3 gate validation logic exists in `gates.service.py`
- Workflow/task event infrastructure is operational
- WebSocket broadcaster supports real-time task status
- Generation endpoints exist but return placeholders
- System sections table exists but records are not created

**Constraints:**
- Continue using thin workflow + task event pattern (no Temporal expansion)
- Follow existing `Manifest` async pattern as the template
- Preserve existing gate validation logic without modification
- All generation must be truly async (no sync fallback)

**Stakeholders:**
- Backend services (systems, evidence, drafts modules)
- Frontend workbench (expects JobHandle + WebSocket events)
- Gate validation (depends on materialized sections for G4/G5)

## Goals / Non-Goals

**Goals:**
- System sections are materialized during `create_system` based on project thesis schema
- All generation endpoints return `202 + JobHandle` immediately
- Background tasks persist real records and broadcast task events
- G1-G3 gate validation can pass with real generated artifacts
- Frontend receives real-time progress via WebSocket

**Non-Goals:**
- Frontend UI implementation (separate phase)
- Temporal long-running workflow integration
- Executor real implementation (can use placeholders for now)
- G4/G5 frontend workbench panels

## Decisions

### Decision 1: Section Source Priority

**Choice:** `project.thesis_schema_json.outline` → `chapters` → default 4-section skeleton

**Rationale:**
- Outline is most specific and structured
- Chapters provides fallback for simpler schemas
- Default skeleton ensures sections always exist

**Alternatives Considered:**
- Always use default skeleton: Too rigid, ignores user schema
- Require outline in schema: Breaks existing projects

### Decision 2: Async Pattern Template

**Choice:** Copy `Manifest` generation pattern exactly

**Pattern:**
1. Router receives request, validates scope
2. Service creates workflow instance, returns handle
3. Background task (via `asyncio.create_task`) executes generation
4. On success: persist records + append `TASK_SUCCEEDED` event + broadcast
5. On failure: append `TASK_FAILED` event + broadcast

**Rationale:**
- Proven pattern already working for Manifest
- Consistent with existing codebase conventions
- No new infrastructure needed

**Alternatives Considered:**
- Celery/RQ: Adds external dependency, overkill for current scale
- Temporal: Explicitly out of scope for this phase

### Decision 3: Evidence Matrix Representation

**Choice:** Continue using `claims + claim_evidence_links` tables, no new `evidence_matrices` table

**Rationale:**
- Existing schema already supports the relationship
- Gate validation logic expects this structure
- Avoids migration complexity

**Alternatives Considered:**
- Add `evidence_matrices` snapshot table: Adds complexity without clear benefit
- Store as JSON in workflow: Loses queryability and referential integrity

### Decision 4: Version Number Generation

**Choice:** Repository layer provides `get_next_version(system_id, entity_type)` helper

**Rationale:**
- Centralizes version logic
- Prevents race conditions via DB-level max() query
- Reusable across all versioned entities

**Alternatives Considered:**
- Service layer manages versions: Harder to test, more error-prone
- Auto-increment column: Doesn't support per-system versioning

### Decision 5: Background Task Lifecycle

**Choice:** Service layer owns `run_*`, `complete_*`, `failure_*` three-phase pattern

**Pattern:**
```python
async def run_generate_figure_plan(system_id: str, db: AsyncSession):
    try:
        # 1. Fetch context
        # 2. Call executor (placeholder OK for now)
        # 3. Call complete_* with results
    except Exception as e:
        await failure_generate_figure_plan(system_id, str(e), db)

async def complete_generate_figure_plan(system_id: str, plan_data: dict, db: AsyncSession):
    # 1. Persist FigurePlan record
    # 2. Append workflow success event
    # 3. Broadcast task event

async def failure_generate_figure_plan(system_id: str, error: str, db: AsyncSession):
    # 1. Append workflow failure event
    # 2. Broadcast task event
```

**Rationale:**
- Clear separation of concerns
- Testable in isolation
- Consistent error handling

**Alternatives Considered:**
- Single monolithic function: Harder to test and maintain
- Router-level background tasks: Violates layering, harder to test

## Risks / Trade-offs

**[Risk]** Section materialization fails if thesis schema is malformed
→ **Mitigation:** Fallback to default 4-section skeleton on any parse error

**[Risk]** Background tasks may fail silently if broadcaster is down
→ **Mitigation:** Workflow events are persisted first, broadcast is best-effort

**[Risk]** Concurrent generation requests for same system may create duplicate records
→ **Mitigation:** Add workflow state check before starting generation (if workflow already running, reject)

**[Risk]** Version number gaps if transaction rolls back
→ **Mitigation:** Acceptable trade-off, version gaps don't break functionality

**[Trade-off]** Using `asyncio.create_task` instead of proper job queue
→ **Limitation:** Tasks die if server restarts, no retry mechanism
→ **Acceptable:** MVP scope, can upgrade to Celery/Temporal later

**[Trade-off]** Executor calls are placeholders (return mock data)
→ **Limitation:** Generated content is not real
→ **Acceptable:** Phase 4 focuses on async infrastructure, real executors come later

## Migration Plan

**Deployment Steps:**
1. Deploy backend changes (no schema migration needed, tables exist)
2. Verify existing systems can still be queried
3. Create new test system, verify sections are materialized
4. Trigger generation endpoints, verify handles returned
5. Monitor WebSocket for task events
6. Verify records appear in database

**Rollback Strategy:**
- No schema changes, safe to rollback code
- Existing systems unaffected (sections will be empty but non-breaking)
- New systems created during rollback window will lack sections (can be backfilled)

**Backfill Plan (if needed):**
```sql
-- Identify systems without sections
SELECT id FROM systems WHERE id NOT IN (SELECT DISTINCT system_id FROM system_sections);

-- Backfill via API or script
-- (Call section materialization logic for each system)
```

## Open Questions

**Q1:** Should section materialization be idempotent (safe to call multiple times)?
**A:** Yes, add check: if sections exist for system, skip creation

**Q2:** What happens if project thesis schema changes after system is created?
**A:** Sections are immutable after creation (matches current design, no auto-sync)

**Q3:** Should we validate section_key uniqueness at DB level?
**A:** Yes, add unique constraint `(system_id, section_key)` in future migration (not blocking for Phase 4)

**Q4:** How to handle partial generation failures (e.g., 3 of 5 figures succeed)?
**A:** All-or-nothing: transaction rolls back on any failure, task event shows failure
