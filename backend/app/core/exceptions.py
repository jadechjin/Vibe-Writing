from typing import Any


class AppException(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class GateBlockedException(AppException):
    def __init__(self, *, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="gate_blocked",
            message=message,
            status_code=409,
            details=details,
        )
