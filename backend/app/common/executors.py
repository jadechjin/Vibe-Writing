from typing import Any

from pydantic import BaseModel, Field

from app.common.enums import ExecutorKind, TaskStatus


class ExecutorRequest(BaseModel):
    executor: ExecutorKind
    correlation_id: str
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutorResult(BaseModel):
    executor: ExecutorKind
    correlation_id: str
    task_type: str
    status: TaskStatus
    output: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    error: str | None = None
