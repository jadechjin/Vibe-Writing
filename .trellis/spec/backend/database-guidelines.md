# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

This backend uses SQLAlchemy 2.x models plus Alembic migrations.

The active baseline is:

- ORM base and shared mixins in `backend/app/persistence/base.py`
- async engine and session factory in `backend/app/persistence/session.py`
- domain models split across `backend/app/persistence/models/*.py`
- schema changes in `backend/alembic/versions/*.py`
- migration behavior verified by tests under `backend/tests/models/*`

The project mixes `AsyncSession` request handling with background completion paths that may reopen a session from the current bind. Because of that, some repositories and services accept `AsyncSession | Session` and use `_maybe_await(...)` helpers.

---

## Query Patterns

Repository rules in the current codebase:

- Build SQLAlchemy statements in repository functions.
- Use eager loading explicitly when response builders need related data.
- Use deterministic ordering for list endpoints.
- `flush()` in repositories when the caller needs generated IDs immediately.
- `commit()` in services, not repositories.

Reference examples:

- `backend/app/modules/assets/repository.py`
  - `get_asset_by_id(...)` uses `selectinload(Asset.metadata_entry)`.
  - `list_assets_for_system(...)` uses stable ordering by `created_at`, `file_name`, and `id`.
  - `create_asset(...)` and `create_manifest(...)` call `flush()` but do not commit.
- `backend/app/modules/assets/service.py`
  - validates domain state first
  - calls repository helpers
  - commits once the unit of work is complete

Transaction boundary rule:

- Request/session lifecycle is owned by FastAPI dependency injection.
- Background completion paths reopen a fresh session from the request session bind before writing final workflow results.
- Do not reuse a request-scoped session inside fire-and-forget background work.

---

## Migrations

Alembic migrations live in `backend/alembic/versions/`.

Current migration conventions visible in the repo:

- revision identifiers are explicit strings, for example `001_project_system` and `003_evidence_draft_workflow`
- complex migrations define constraints and indexes explicitly
- repeated audit columns may be factored into helpers such as `_audit_columns()` in `backend/alembic/versions/003_evidence_draft_workflow.py`
- partial indexes are written in the migration, not left to implicit ORM behavior

Important real example:

- `backend/alembic/versions/003_evidence_draft_workflow.py` creates two partial unique indexes for `claim_evidence_links`, separating links with and without `analysis_run_id`.

The repository already tests migration contracts. See:

- `backend/tests/models/evidence_draft_workflow/test_migration.py`

That means important DDL behavior should be asserted, not trusted implicitly.

---

## Naming Conventions

From the current schema:

- table names use plural `snake_case`
- primary keys are string UUIDs via `UUIDPrimaryKeyMixin`
- audit/timestamp columns come from shared mixins in `backend/app/persistence/base.py`
- unique constraints are named with `uq_<table>_<scope>` style
- indexes are named with `ix_<table>_<purpose>` style

Examples:

- `experimental_systems`
- `system_sections`
- `workflow_instances`
- `uq_experimental_systems_project_system_no`
- `uq_system_sections_system_section_key`
- `ix_claim_evidence_links_unique_with_run`

Field naming convention:

- Python model attributes use `snake_case`
- JSON payload columns end with `_json`
- foreign keys usually end with `_id`
- state/status fields use short string columns instead of separate lookup tables at this stage

---

## Common Mistakes

These are the mistakes to avoid because the existing codebase already chose a different pattern:

- Committing inside repositories instead of services.
- Returning unordered lists from repository functions.
- Reusing the request session in background completion code.
- Depending on ORM defaults for critical partial indexes or delete behavior.
- Turning `claim_evidence_links.analysis_run_id` into `SET NULL` semantics when the link is meant to preserve "bound to a specific analysis run" meaning.
- Adding new tables without shared audit/timestamp columns unless there is a strong reason.
