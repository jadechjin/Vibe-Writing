from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from temporalio import workflow

from app.common.enums import EventType, TaskStatus
from app.modules.tasks.schemas import (
    WorkflowEventAppend,
    WorkflowSnapshot,
    WorkflowStartInput,
    WorkflowStartResult,
)
from app.modules.tasks.service import TaskWorkflowService


@workflow.defn
class SystemWorkflow:
    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


@dataclass
class WorkflowCommand:
    project_id: str
    system_id: str
    workflow_key: str
    current_state: str
    target_state: str
    current_gate: str | None = None
    status: TaskStatus = TaskStatus.QUEUED
    context: dict[str, Any] | None = None
    message: str = "workflow queued"
    event_type: EventType | str = EventType.TASK_CREATED
    created_by: str | None = None


@dataclass
class WorkflowEventCommand:
    workflow_id: str
    event_type: EventType | str
    message: str
    status: TaskStatus | None = None
    from_state: str | None = None
    to_state: str | None = None
    current_state: str | None = None
    current_gate: str | None = None
    progress: int | None = None
    payload: dict[str, Any] | None = None
    context_update: dict[str, Any] | None = None
    last_error: str | None = None
    created_by: str | None = None


async def start_system_workflow(
    service: TaskWorkflowService,
    command: WorkflowCommand,
) -> WorkflowStartResult:
    merged_context = {**(command.context or {}), "target_state": command.target_state}
    result = await service.start_workflow(
        WorkflowStartInput(
            project_id=command.project_id,
            system_id=command.system_id,
            workflow_key=command.workflow_key,
            current_state=command.current_state,
            current_gate=command.current_gate,
            status=command.status,
            context=merged_context,
            message=command.message,
            initial_event_type=command.event_type,
            created_by=command.created_by,
        )
    )
    return result


async def append_system_workflow_event(
    service: TaskWorkflowService,
    command: WorkflowEventCommand,
) -> WorkflowSnapshot:
    payload = asdict(command)
    payload.pop("workflow_id")
    payload["payload"] = payload.get("payload") or {}
    payload["context_update"] = payload.get("context_update") or {}
    return await service.append_event(command.workflow_id, WorkflowEventAppend(**payload))


__all__ = [
    "SystemWorkflow",
    "WorkflowCommand",
    "WorkflowEventCommand",
    "WorkflowStartResult",
    "append_system_workflow_event",
    "start_system_workflow",
]
