## Why

Current G0-G3 gate logic and workflow foundation exist, but generation endpoints (Figure Plan, Evidence Matrix, Outline, Section Draft) return placeholder responses without real async persistence. System sections are not materialized during system creation, blocking G4 claim approval and G5 section draft workflows. This change completes the G1-G3 async generation closure to enable real experimental asset management workflow.

## What Changes

- Materialize system sections during system creation based on project thesis schema
- Implement async Figure Plan generation with real persistence and task event broadcasting
- Implement async Evidence Matrix generation (claims + claim_evidence_links) with real persistence
- Implement async Outline generation with real persistence and task event broadcasting
- Implement async Section Draft generation with real persistence and task event broadcasting
- All generation endpoints return `202 + JobHandle` and complete via background tasks
- Background tasks write workflow events and broadcast task status via WebSocket

## Capabilities

### New Capabilities
- `system-sections-materialization`: System section records are created during system creation based on project thesis schema (outline → chapters → default 4-section skeleton)
- `figure-plan-async-generation`: Figure Plan generation returns handle immediately and completes asynchronously with real FigurePlan records
- `evidence-matrix-async-generation`: Evidence Matrix generation returns handle immediately and completes asynchronously with real Claim and ClaimEvidenceLink records
- `outline-async-generation`: Outline generation returns handle immediately and completes asynchronously with real Outline records
- `section-draft-async-generation`: Section Draft generation returns handle immediately and completes asynchronously with real SectionDraft records

### Modified Capabilities
<!-- No existing spec requirements are changing - these are net-new implementations -->

## Impact

**Backend modules**:
- `backend/app/modules/systems/service.py` - add section materialization logic
- `backend/app/modules/systems/repository.py` - add section creation helpers
- `backend/app/modules/evidence/service.py` - implement async generation tasks
- `backend/app/modules/evidence/router.py` - update endpoints to return handles
- `backend/app/modules/evidence/repository.py` - add version helpers and queries
- `backend/app/modules/drafts/service.py` - implement async generation tasks
- `backend/app/modules/drafts/router.py` - update endpoints to return handles
- `backend/app/modules/drafts/repository.py` - add version helpers and queries

**Tests**:
- `backend/tests/modules/systems/test_systems_api.py` - verify section materialization
- `backend/tests/modules/evidence/test_evidence_api.py` - verify async generation
- `backend/tests/modules/drafts/test_drafts_api.py` - verify async generation

**Dependencies**:
- Existing workflow/task event infrastructure
- Existing WebSocket broadcaster
- Existing gate validation logic (no changes needed)
