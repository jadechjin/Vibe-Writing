# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

Backend quality in this repository is centered on stable contracts, thin routers, explicit workflow semantics, and integration-heavy tests.

Current enforced tooling from `backend/pyproject.toml`:

- Python `>=3.11`
- Ruff with `line-length = 100`
- Ruff lint rules `E`, `F`, `I`, `B`
- Pytest with `pytest-asyncio`

The repo already prefers API-level and workflow-level tests over isolated mock-heavy unit tests. Generated work must keep the existing thin workflow model intact: generation endpoints return `202 + handle`, background completion persists results, and workflow/task events become the source of truth.

---

## Forbidden Patterns

Avoid these patterns because they fight the current codebase shape:

- fat routers that validate business rules or mutate workflow state directly
- repositories that call `commit()`
- synchronous "generate and return final artifact immediately" endpoints for long-running work
- inconsistent response bodies that bypass `ApiResponse[T]`
- implicit schema behavior for critical constraints that should live in Alembic migrations
- mock-only tests for behavior that already has stable API coverage

Examples of the intended alternative live in `backend/app/modules/projects/router.py`, `backend/app/modules/assets/service.py`, and `backend/app/modules/assets/repository.py`.

---

## Required Patterns

New backend work should follow these repository conventions:

- routers compose request dependencies and return typed `ApiResponse[...]`
- services own domain validation, transaction boundaries, and workflow coordination
- repositories are the preferred home for reusable SQLAlchemy statements, eager loading, flushes, and deterministic ordering, even though the current codebase still has some service-level queries in gate and workflow paths
- shared errors use `AppException` + `ErrorCode`
- generation flows return accepted handles and complete work in a background path using a fresh session
- workflow failures write task/workflow events instead of disappearing into logs only

If a feature touches workflow state, make sure the persisted workflow snapshot remains the backend truth, not an in-memory executor variable.

---

## Testing Requirements

The current backend testing baseline is visible in `backend/tests/modules/*` and `backend/tests/models/*`:

- API contract tests use `fastapi.testclient.TestClient`
- tests commonly create a temporary SQLite database with foreign keys enabled
- tests cover both accepted async handles and eventual persisted results
- migration behavior can be asserted directly from migration source or schema behavior

Reference examples:

- `backend/tests/modules/evidence/test_evidence_api.py`
- `backend/tests/modules/drafts/test_drafts_api.py`
- `backend/tests/models/evidence_draft_workflow/test_migration.py`

For new API work, cover at least:

- success path
- missing-resource path
- invalid-input or conflict path
- workflow/event side effects when applicable

---

## Code Review Checklist

Reviewers should check:

- Is the router still thin?
- Does the feature preserve `ApiResponse[T]` and typed error envelopes?
- Are `commit()` and `flush()` in the right layer?
- For generation flows, does the endpoint return `202 + handle` instead of the final artifact?
- Are workflow events and failure states persisted correctly?
- Are tests covering both contract shape and persistence side effects?
- Are ordering, eager loading, and foreign-key semantics explicit where needed?
