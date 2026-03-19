from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import EventType, TaskStatus, coerce_gate_key
from app.common.schemas import Blocker, JobHandle
from app.modules.tasks.repository import TaskWorkflowRepository
from app.modules.tasks.schemas import (
    WorkflowEventAppend,
    WorkflowEventRecord,
    WorkflowSnapshot,
    WorkflowStartInput,
    WorkflowStartResult,
)
from app.persistence.models.workflow import WorkflowEvent, WorkflowInstance


class TaskWorkflowService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = TaskWorkflowRepository(session)

    async def start_workflow(self, payload: WorkflowStartInput) -> WorkflowStartResult:
        version = await self._repository.get_next_version(
            project_id=payload.project_id,
            system_id=payload.system_id,
            workflow_key=payload.workflow_key,
        )
        instance = WorkflowInstance(
            project_id=payload.project_id,
            system_id=payload.system_id,
            workflow_key=payload.workflow_key,
            current_state=str(payload.current_state),
            current_gate=None if payload.current_gate is None else str(payload.current_gate),
            status=payload.status.value,
            context_json=self._merge_context({}, payload.context),
            version=version,
            created_by=payload.created_by,
            updated_by=payload.created_by,
        )
        instance = await self._repository.add_instance(instance)

        event_payload = self._merge_event_payload(
            payload.context,
            message=payload.message,
            status=payload.status,
        )
        event = WorkflowEvent(
            instance_id=instance.id,
            event_type=str(payload.initial_event_type),
            from_state=None,
            to_state=instance.current_state,
            payload_json=event_payload,
            created_by=payload.created_by,
            updated_by=payload.created_by,
        )
        event = await self._repository.add_event(event)
        snapshot = self._build_snapshot(instance=instance, events=[event])
        return WorkflowStartResult(handle=self.build_job_handle(instance), snapshot=snapshot)

    async def append_event(self, workflow_id: str, payload: WorkflowEventAppend) -> WorkflowSnapshot:
        instance = await self._require_instance(workflow_id)
        previous_state = instance.current_state

        if payload.current_state is not None:
            instance.current_state = str(payload.current_state)
        elif payload.to_state is not None:
            instance.current_state = str(payload.to_state)

        if payload.current_gate is not None:
            instance.current_gate = str(payload.current_gate)
        if payload.status is not None:
            instance.status = payload.status.value
        if payload.context_update:
            instance.context_json = self._merge_context(instance.context_json, payload.context_update)
        if payload.last_error is not None:
            instance.last_error = payload.last_error
        if payload.completed_at is not None:
            instance.completed_at = payload.completed_at
        elif payload.status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            instance.completed_at = datetime.now(UTC)

        instance.updated_by = payload.created_by
        await self._session.flush()

        event = WorkflowEvent(
            instance_id=instance.id,
            event_type=str(payload.event_type),
            from_state=payload.from_state and str(payload.from_state) or previous_state,
            to_state=payload.to_state and str(payload.to_state) or instance.current_state,
            payload_json=self._merge_event_payload(
                payload.payload,
                message=payload.message,
                status=payload.status or TaskStatus(instance.status),
                progress=payload.progress,
            ),
            created_by=payload.created_by,
            updated_by=payload.created_by,
        )
        event = await self._repository.add_event(event)
        events = await self._repository.list_events(instance.id)
        return self._build_snapshot(instance=instance, events=events, latest_event=event)

    async def get_workflow_snapshot(
        self,
        *,
        workflow_id: str | None = None,
        system_id: str | None = None,
        workflow_key: str | None = None,
    ) -> WorkflowSnapshot | None:
        instance: WorkflowInstance | None = None
        if workflow_id is not None:
            instance = await self._repository.get_instance(workflow_id)
        elif system_id is not None:
            instance = await self._repository.get_latest_instance_for_system(
                system_id=system_id,
                workflow_key=workflow_key,
            )
        else:
            raise ValueError("workflow_id or system_id is required")

        if instance is None:
            return None

        events = await self._repository.list_events(instance.id)
        return self._build_snapshot(instance=instance, events=events)

    async def record_gate_blocked(
        self,
        *,
        workflow_id: str,
        message: str,
        blockers: list[Blocker],
        current_gate: str | None,
        current_state: str | None,
        created_by: str | None = None,
    ) -> WorkflowSnapshot:
        blocker_payload = [blocker.model_dump(mode="json") for blocker in blockers]
        return await self.append_event(
            workflow_id,
            WorkflowEventAppend(
                event_type=EventType.GATE_BLOCKED,
                message=message,
                status=TaskStatus.WAITING_USER,
                current_gate=current_gate,
                current_state=current_state,
                payload={"blockers": blocker_payload},
                context_update={"latest_blockers": blocker_payload},
                created_by=created_by,
            ),
        )

    async def record_gate_passed(
        self,
        *,
        workflow_id: str,
        message: str,
        current_gate: str | None,
        from_state: str | None,
        to_state: str,
        created_by: str | None = None,
    ) -> WorkflowSnapshot:
        return await self.append_event(
            workflow_id,
            WorkflowEventAppend(
                event_type=EventType.GATE_PASSED,
                message=message,
                status=TaskStatus.SUCCEEDED,
                from_state=from_state,
                to_state=to_state,
                current_state=to_state,
                current_gate=current_gate,
                context_update={"latest_blockers": []},
                created_by=created_by,
            ),
        )

    def build_job_handle(self, instance: WorkflowInstance) -> JobHandle:
        return JobHandle(
            workflow_id=instance.id,
            job_id=self._build_job_id(instance),
            status=TaskStatus(instance.status),
        )

    async def _require_instance(self, workflow_id: str) -> WorkflowInstance:
        instance = await self._repository.get_instance(workflow_id)
        if instance is None:
            raise ValueError(f"Workflow instance not found: {workflow_id}")
        return instance

    def _build_snapshot(
        self,
        *,
        instance: WorkflowInstance,
        events: list[WorkflowEvent] | tuple[WorkflowEvent, ...],
        latest_event: WorkflowEvent | None = None,
    ) -> WorkflowSnapshot:
        event_records = [self._serialize_event(event) for event in events]
        resolved_latest_event = latest_event or (events[-1] if events else None)
        latest_blockers = instance.context_json.get("latest_blockers", [])
        coerced_gate = coerce_gate_key(instance.current_gate) if instance.current_gate else None
        return WorkflowSnapshot(
            workflow_id=instance.id,
            job_id=self._build_job_id(instance),
            project_id=instance.project_id,
            system_id=instance.system_id,
            workflow_key=instance.workflow_key,
            current_state=instance.current_state,
            current_gate=coerced_gate.value if coerced_gate else instance.current_gate,
            status=TaskStatus(instance.status),
            context=dict(instance.context_json),
            version=instance.version,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
            last_error=instance.last_error,
            latest_event=None
            if resolved_latest_event is None
            else self._serialize_event(resolved_latest_event),
            latest_blockers=[Blocker.model_validate(blocker) for blocker in latest_blockers],
            events=event_records,
        )

    def _serialize_event(self, event: WorkflowEvent) -> WorkflowEventRecord:
        payload = dict(event.payload_json)
        raw_status = payload.pop("status", TaskStatus.QUEUED.value)
        raw_progress = payload.pop("progress", None)
        raw_message = payload.pop("message", event.event_type)
        return WorkflowEventRecord(
            id=event.id,
            event_type=event.event_type,
            status=TaskStatus(raw_status),
            message=str(raw_message),
            from_state=event.from_state,
            to_state=event.to_state,
            progress=raw_progress,
            payload=payload,
            created_at=event.created_at,
        )

    def _merge_context(
        self,
        current: dict[str, Any],
        update: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            **current,
            **update,
        }

    def _merge_event_payload(
        self,
        payload: dict[str, Any],
        *,
        message: str,
        status: TaskStatus,
        progress: int | None = None,
    ) -> dict[str, Any]:
        merged_payload = {
            **payload,
            "message": message,
            "status": status.value,
        }
        if progress is not None:
            merged_payload["progress"] = progress
        return merged_payload

    def _build_job_id(self, instance: WorkflowInstance) -> str:
        return f"{instance.workflow_key}:{instance.system_id}:{instance.version}"


__all__ = ["TaskWorkflowService"]
