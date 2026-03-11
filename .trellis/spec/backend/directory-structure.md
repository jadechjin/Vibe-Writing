# Directory Structure

> How backend code is organized in this project.

---

## Overview

The backend lives under `backend/app/` and is organized by domain modules instead of by technical layer alone. The stable split in this repository is:

- API entrypoints in `backend/app/api/*`
- shared contracts in `backend/app/common/*`
- runtime/config in `backend/app/core/*`
- persistence primitives in `backend/app/persistence/*`
- business modules in `backend/app/modules/*`
- executor integrations in `backend/app/executors/*`
- workflow orchestration in `backend/app/workflows/*`
- realtime push in `backend/app/realtime/*`

Routers stay thin. Domain rules, workflow decisions, and transaction boundaries belong in services. Repositories are the preferred home for reusable SQLAlchemy statements, eager loading, flush helpers, and deterministic ordering, even though some workflow and gate paths still issue `select(...)` directly from services today.

---

## Directory Layout

```text
backend/  (representative, non-exhaustive)
├── app/
│   ├── api/
│   │   ├── router.py
│   │   └── websocket.py
│   ├── common/
│   │   ├── enums.py
│   │   ├── errors.py
│   │   └── schemas.py
│   ├── core/
│   │   ├── config.py
│   │   └── exceptions.py
│   ├── executors/
│   │   ├── claude_code.py
│   │   ├── python_analysis.py
│   │   └── vision.py
│   ├── persistence/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models/
│   │       ├── project.py
│   │       ├── system.py
│   │       ├── asset.py
│   │       ├── manifest.py
│   │       ├── evidence.py
│   │       ├── draft.py
│   │       └── workflow.py
│   ├── modules/
│   │   ├── projects/
│   │   ├── systems/
│   │   ├── assets/
│   │   ├── evidence/
│   │   ├── drafts/
│   │   ├── gates/
│   │   └── tasks/
│   ├── realtime/
│   │   └── broadcaster.py
│   ├── workflows/
│   │   └── system_workflow.py
│   └── main.py
├── alembic/
│   └── versions/
└── tests/
    ├── modules/
    └── models/
```

---

## Module Organization

Each business module usually follows this shape:

- `router.py` — request wiring and response models only
- `service.py` — domain validation, orchestration, transaction boundary, workflow/task event coordination
- `schemas.py` — request/response DTOs
- `repository.py` — reusable SQLAlchemy statements, eager loading, flush helpers
- `__init__.py` — re-export when needed

Current examples:

- `backend/app/modules/projects/router.py` is a thin FastAPI layer returning `ApiResponse[T]`.
- `backend/app/modules/assets/service.py` owns validation, workflow start/completion, and `session.commit()`.
- `backend/app/modules/assets/repository.py` owns `select(...)`, `selectinload(...)`, `order_by(...)`, and `flush()`.
- `backend/app/modules/gates/service.py` and `backend/app/modules/systems/service.py` show that some read-side workflow queries still live in services in the current codebase.

Cross-cutting runtime pieces are intentionally outside domain modules:

- `backend/app/api/router.py` mounts all HTTP routers.
- `backend/app/api/websocket.py` exposes `/ws/tasks`.
- `backend/app/realtime/broadcaster.py` handles in-process pub/sub.
- `backend/app/workflows/system_workflow.py` owns workflow/task-event persistence helpers.
- `backend/app/executors/*` contains external execution adapters.

---

## Naming Conventions

- Directories and files use `snake_case`.
- Domain folders use plural nouns: `projects`, `systems`, `assets`, `evidence`, `drafts`.
- FastAPI entry files are named `router.py`.
- Domain orchestration files are named `service.py`.
- SQLAlchemy data-access files are named `repository.py`.
- DTO files are named `schemas.py`.
- ORM models are split by domain under `backend/app/persistence/models/*.py`, not collapsed into one giant `models.py`.
- Database tables are plural `snake_case`, for example `projects`, `experimental_systems`, `workflow_instances`, `section_drafts`.
- Alembic revisions use numeric prefixes plus a short description, for example `001_project_system.py` and `003_evidence_draft_workflow.py`.

---

## Examples

Use these files as the reference set before adding a new module:

- `backend/app/modules/projects/router.py` — minimal thin router pattern
- `backend/app/modules/assets/service.py` — service orchestration + async workflow completion pattern
- `backend/app/modules/assets/repository.py` — repository query composition pattern
- `backend/app/persistence/models/system.py` — domain model file split + constraint naming
- `backend/app/api/websocket.py` — non-CRUD endpoint placed at API boundary
- `backend/app/realtime/broadcaster.py` — realtime runtime utility outside business modules

Practical anti-patterns in this repository:

- Do not put business rules directly in `router.py`.
- Do not commit transactions in `repository.py`.
- Do not hide domain tables inside a single monolithic model file.
- Do not return final generated artifacts directly from generation routers; return a queued handle and let background completion persist results.
