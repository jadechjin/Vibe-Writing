from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

from app.common.enums import GateKey, GateRequirementKey, SystemState, TaskStatus, coerce_gate_key

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

    @field_validator("gate", mode="before")
    @classmethod
    def _coerce_gate(cls, v: Any) -> GateKey | None:
        if v is None:
            return None
        if isinstance(v, GateKey):
            return v
        if isinstance(v, str):
            return coerce_gate_key(v)
        return None


class GateReview(BaseModel):
    gate: GateKey
    satisfied: bool
    required_checks: list[GateRequirementKey]
    blockers: list[Blocker] = Field(default_factory=list)


class JobHandle(BaseModel):
    workflow_id: str | None = None
    job_id: str
    status: TaskStatus = TaskStatus.QUEUED
