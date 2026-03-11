from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.common.enums import GateKey, GateRequirementKey, SystemState, TaskStatus

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total: int | None = None
    page: int | None = None
    limit: int | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: str | None = None
    meta: PaginationMeta | None = None


class Blocker(BaseModel):
    code: str
    message: str
    gate: GateKey | None = None
    current_state: SystemState | None = None
    required_checks: list[GateRequirementKey] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class GateReview(BaseModel):
    gate: GateKey
    satisfied: bool
    required_checks: list[GateRequirementKey]
    blockers: list[Blocker] = Field(default_factory=list)


class JobHandle(BaseModel):
    workflow_id: str | None = None
    job_id: str
    status: TaskStatus = TaskStatus.QUEUED
