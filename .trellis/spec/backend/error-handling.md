# Error Handling

> How errors are handled in this project.

---

## Overview

The backend uses explicit application exceptions instead of ad-hoc HTTP error bodies.

The stable path is:

1. service detects a domain or validation problem
2. service raises `AppException` (or a subclass)
3. `backend/app/main.py` converts that exception into the shared `ApiResponse` error envelope

Reference files:

- `backend/app/core/exceptions.py`
- `backend/app/common/errors.py`
- `backend/app/common/schemas.py`
- `backend/app/main.py`

---

## Error Types

Current shared error types:

- `AppException` in `backend/app/core/exceptions.py`
  - carries `code`, `message`, `status_code`, `details`
- `GateBlockedException` in `backend/app/core/exceptions.py`
  - specialization of `AppException`
  - uses HTTP `409`
- `ErrorCode` enum in `backend/app/common/errors.py`
  - `validation_error`
  - `not_found`
  - `conflict`
  - `gate_blocked`
  - `executor_error`
  - `workflow_error`

Use `AppException` for domain failures that clients should understand. Do not invent a new response shape in routers.

---

## Error Handling Patterns

What the codebase does today:

- routers usually do not wrap service calls in local try/except blocks
- services validate ownership, existence, workflow state, and cross-entity consistency
- services raise `AppException` with a stable `ErrorCode` and structured `details`
- background completion paths catch unexpected exceptions and record workflow failure events

Real examples:

- `backend/app/modules/assets/service.py`
  - returns `404` when a system or asset is missing
  - returns `409` for cross-system binding conflicts or invalid workflow preconditions
  - writes failure context when async manifest generation crashes
- `backend/app/modules/projects/router.py`
  - simply delegates to the service and returns `ApiResponse(data=...)`
- `backend/app/main.py`
  - serializes all `AppException` instances centrally

Guideline:

- raise a typed application exception for expected business failures
- reserve bare unexpected exceptions for true bugs or infrastructure failures
- if a background task fails, persist the failure into workflow/event state instead of silently swallowing it

---

## API Error Responses

Error responses are returned through the same shared envelope as success responses.

Current shape from `backend/app/main.py` + `backend/app/common/schemas.py`:

```json
{
  "success": false,
  "error": "Human-readable message",
  "data": {
    "code": "not_found",
    "details": {
      "system_id": "..."
    }
  }
}
```

Practical rules:

- `error` is the user-facing summary string
- machine-readable error type goes in `data.code`
- structured context goes in `data.details`
- HTTP status code must still be meaningful (`404`, `409`, `422`, `500`, etc.)

Frontend code already depends on this contract through `frontend/lib/api.ts`, which reads `body.error` and throws `ApiError`.

---

## Common Mistakes

Do not introduce these patterns:

- Raising plain `Exception` for a known domain failure.
- Returning custom `{ message: ... }` or `{ detail: ... }` bodies from a router while the rest of the API uses `ApiResponse`.
- Hiding useful context instead of filling `details`.
- Leaking raw stack traces or internal object dumps to clients.
- Catching an exception in async workflow completion and doing nothing; failed generation paths must update workflow/task-event state.
- Treating gate blocking as a successful `200` response. The current convention is a typed error or a structured blocked outcome, depending on the endpoint contract.
