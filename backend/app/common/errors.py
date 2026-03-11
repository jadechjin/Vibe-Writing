from enum import StrEnum


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    GATE_BLOCKED = "gate_blocked"
    EXECUTOR_ERROR = "executor_error"
    WORKFLOW_ERROR = "workflow_error"
