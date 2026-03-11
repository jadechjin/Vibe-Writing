# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

These documents describe the backend as it exists today: thin FastAPI routers, service-owned domain validation and workflow coordination, SQLAlchemy 2.x persistence with Alembic migrations, shared `ApiResponse[T]` contracts, and integration-heavy tests.

Current async generation flows return queued handles and complete through in-process background tasks plus workflow/task-event persistence; they do not imply a separate durable worker or queue architecture yet.

Use these guides to match the current repository shape instead of inventing a new architecture.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module boundaries across `api`, `modules`, `persistence`, `executors`, `workflows`, and `realtime` | Documented |
| [Database Guidelines](./database-guidelines.md) | SQLAlchemy 2.x, Alembic migrations, commit/flush boundaries, and naming conventions | Documented |
| [Error Handling](./error-handling.md) | `AppException`, `GateBlockedException`, `ErrorCode`, and shared `ApiResponse` error envelopes | Documented |
| [Quality Guidelines](./quality-guidelines.md) | Tooling baseline, async workflow rules, forbidden patterns, and review checklist | Documented |
| [Logging Guidelines](./logging-guidelines.md) | Current Python logging usage, log levels, and what to log or avoid | Documented |

---

## Recommended Reading Order

1. [Directory Structure](./directory-structure.md)
2. [Quality Guidelines](./quality-guidelines.md)
3. [Database Guidelines](./database-guidelines.md)
4. [Error Handling](./error-handling.md)
5. [Logging Guidelines](./logging-guidelines.md)

---

## Scope Notes

These guides intentionally document current reality from files such as:

- `backend/app/modules/projects/router.py`
- `backend/app/modules/assets/service.py`
- `backend/app/modules/assets/repository.py`
- `backend/app/main.py`
- `backend/app/api/websocket.py`
- `backend/tests/modules/drafts/test_drafts_api.py`

When the codebase changes, update the relevant guide instead of leaving stale assumptions in the index.
