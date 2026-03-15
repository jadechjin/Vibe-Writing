from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.enums import GateKey, SystemState
from app.common.schemas import Blocker, JobHandle
from app.modules.tasks.schemas import WorkflowSnapshot


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


class SystemCreateRequest(CamelModel):
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class SystemUpdateRequest(CamelModel):
    title: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class SystemSectionSummary(CamelModel):
    id: str
    section_key: str
    title: str
    order_no: int


class SystemSummary(CamelModel):
    id: str
    project_id: str
    system_no: int
    title: str
    status: str
    section_count: int = 0
    created_at: datetime
    updated_at: datetime


class SystemDetail(CamelModel):
    id: str
    project_id: str
    system_no: int
    title: str
    status: str
    sections: list[SystemSectionSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AdvanceBlockedResponse(CamelModel):
    outcome: str = "blocked"
    gate: GateKey
    current_state: SystemState
    blockers: list[Blocker] = Field(default_factory=list)
    snapshot: WorkflowSnapshot


class AdvanceAcceptedResponse(CamelModel):
    outcome: str = "accepted"
    gate: GateKey
    from_state: SystemState
    to_state: SystemState
    handle: JobHandle
    snapshot: WorkflowSnapshot


class AdvanceResponse(CamelModel):
    outcome: str
    gate: GateKey
    current_state: SystemState | None = None
    from_state: SystemState | None = None
    to_state: SystemState | None = None
    blockers: list[Blocker] = Field(default_factory=list)
    handle: JobHandle | None = None
    snapshot: WorkflowSnapshot


__all__ = [
    "AdvanceAcceptedResponse",
    "AdvanceBlockedResponse",
    "AdvanceResponse",
    "SystemCreateRequest",
    "SystemDetail",
    "SystemSectionSummary",
    "SystemSummary",
    "SystemUpdateRequest",
]
