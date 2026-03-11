from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.common.enums import EventType, GateKey, SystemState, TaskStatus
from app.common.schemas import Blocker, JobHandle


class WorkflowStartInput(BaseModel):
    project_id: str
    system_id: str
    workflow_key: str
    current_state: SystemState | str = SystemState.DRAFT
    current_gate: GateKey | str | None = None
    status: TaskStatus = TaskStatus.QUEUED
    context: dict[str, Any] = Field(default_factory=dict)
    message: str = "workflow queued"
    initial_event_type: EventType | str = EventType.TASK_CREATED
    created_by: str | None = None


class WorkflowEventAppend(BaseModel):
    event_type: EventType | str
    message: str
    status: TaskStatus | None = None
    from_state: SystemState | str | None = None
    to_state: SystemState | str | None = None
    current_state: SystemState | str | None = None
    current_gate: GateKey | str | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    context_update: dict[str, Any] = Field(default_factory=dict)
    last_error: str | None = None
    completed_at: datetime | None = None
    created_by: str | None = None


class WorkflowEventRecord(BaseModel):
    id: str
    event_type: str
    status: TaskStatus
    message: str
    from_state: str | None = None
    to_state: str | None = None
    progress: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class WorkflowSnapshot(BaseModel):
    workflow_id: str
    job_id: str
    project_id: str
    system_id: str
    workflow_key: str
    current_state: str
    current_gate: str | None = None
    status: TaskStatus
    context: dict[str, Any] = Field(default_factory=dict)
    version: int
    started_at: datetime
    completed_at: datetime | None = None
    last_error: str | None = None
    latest_event: WorkflowEventRecord | None = None
    latest_blockers: list[Blocker] = Field(default_factory=list)
    events: list[WorkflowEventRecord] = Field(default_factory=list)


class WorkflowStartResult(BaseModel):
    handle: JobHandle
    snapshot: WorkflowSnapshot


__all__ = [
    "WorkflowEventAppend",
    "WorkflowEventRecord",
    "WorkflowSnapshot",
    "WorkflowStartInput",
    "WorkflowStartResult",
]
