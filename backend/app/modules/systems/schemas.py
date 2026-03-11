from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.enums import GateKey, SystemState, TaskStatus
from app.common.schemas import Blocker, JobHandle
from app.modules.tasks.schemas import WorkflowSnapshot


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


class SystemCreateRequest(CamelModel):
    title: str = Field(min_length=1, max_length=255)
    research_goal: str | None = Field(default=None, max_length=5000)
    samples_subjects: str | None = Field(default=None, max_length=5000)
    variables_controls: str | None = Field(default=None, max_length=5000)
    output_metrics: str | None = Field(default=None, max_length=5000)
    methods_summary: str | None = Field(default=None, max_length=5000)
    system_card_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class SystemUpdateRequest(CamelModel):
    title: str | None = Field(default=None, max_length=255)
    research_goal: str | None = Field(default=None, max_length=5000)
    samples_subjects: str | None = Field(default=None, max_length=5000)
    variables_controls: str | None = Field(default=None, max_length=5000)
    output_metrics: str | None = Field(default=None, max_length=5000)
    methods_summary: str | None = Field(default=None, max_length=5000)
    system_card_json: dict[str, Any] | None = None

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
    research_goal: str | None = None
    samples_subjects: str | None = None
    variables_controls: str | None = None
    output_metrics: str | None = None
    methods_summary: str | None = None
    system_card_json: dict[str, Any] = Field(default_factory=dict)
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
