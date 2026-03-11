# Logging Guidelines

> How logging is done in this project.

---

## Overview

The backend currently uses the Python standard library logging module via `logging.getLogger(__name__)`.

Logging is concentrated around runtime boundaries instead of being sprayed across every service function. The strongest examples are the realtime/WebSocket layer in `backend/app/api/websocket.py` and `backend/app/realtime/broadcaster.py`.

This repository does not yet define a custom structured logging wrapper. Until that changes, keep logs small, contextual, and focused on operational events rather than dumping large payloads.

---

## Log Levels

Use levels the way the current code already does:

- `debug` — normal but low-level lifecycle events
  - example: `client disconnected from /ws/tasks` in `backend/app/api/websocket.py`
- `info` — noteworthy operational state changes that are not failures
  - example: `dropped %d stale subscriber(s)` in `backend/app/realtime/broadcaster.py`
- `warning` — degraded behavior where the request can continue but something is wrong
  - example: subscriber queue full and dropped in `backend/app/realtime/broadcaster.py`
- `exception` / error-level logging — unexpected failures with traceback
  - example: `unexpected error on /ws/tasks` in `backend/app/api/websocket.py`

Do not log expected validation failures at exception level if they are already represented as typed API errors.

---

## Structured Logging

There is no project-specific JSON logger yet. The current practical standard is:

- get a module logger with `logging.getLogger(__name__)`
- include the smallest useful identifiers in the message
- prefer stable operational wording over noisy object dumps
- let `logger.exception(...)` capture traceback for unexpected errors

If you need more context, log IDs and status values, not full ORM objects or request payloads.

---

## What to Log

Good logging targets in this codebase:

- WebSocket connection lifecycle problems
- dropped subscribers / backpressure signals
- unexpected background-task failures
- workflow or task-event failures that are hard to diagnose from API responses alone
- infrastructure availability problems at runtime boundaries

Keep the source of truth in the database and workflow events. Logging should help operators understand runtime behavior, not replace persisted workflow state.

---

## What NOT to Log

Do not log:

- secrets, tokens, or credentials
- large JSON payloads from manifests, workflow context, or generated content
- raw uploaded file contents
- full ORM objects or unbounded exception-adjacent dumps
- reviewer comments or other user-authored long-form content unless there is a clear debugging need

This is especially important because the project handles generated drafts, evidence metadata, and workflow payloads that can grow quickly.
