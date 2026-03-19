from __future__ import annotations

import re
from inspect import isawaitable
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.common.enums import EventType, GateKey, SystemState, TaskStatus
from app.common.errors import ErrorCode
from app.common.events import TaskEvent
from app.common.schemas import Blocker, GateReview
from app.core.exceptions import AppException
from app.modules.gates.service import resolve_active_gate, review_gate
from app.modules.systems import repository
from app.modules.systems.schemas import (
    AdvanceResponse,
    SystemCreateRequest,
    SystemDetail,
    SystemSectionSummary,
    SystemUpdateRequest,
)
from app.modules.tasks.schemas import WorkflowEventRecord, WorkflowSnapshot, WorkflowStartResult
from app.modules.tasks.service import TaskWorkflowService
from app.persistence.models.system import ExperimentalSystem
from app.persistence.models.workflow import WorkflowEvent, WorkflowInstance
from app.realtime.broadcaster import TaskBroadcaster
from app.workflows.system_workflow import WorkflowCommand, start_system_workflow

SessionLike = AsyncSession | Session
T = TypeVar("T")

GATE_TARGET_STATE: dict[GateKey, SystemState] = {
    GateKey.G0: SystemState.SYSTEM_DEFINED,
    GateKey.G1: SystemState.ANALYSIS_READY,
    GateKey.G2: SystemState.OUTLINE_READY,
    GateKey.G3: SystemState.CHAPTER_APPROVED,
}

DEFAULT_SYSTEM_SECTIONS: tuple[tuple[str, str], ...] = (
    ("introduction", "引言"),
    ("materials_and_methods", "实验材料与方法"),
    ("results_and_discussion", "结果与讨论"),
    ("chapter_summary", "本章小结"),
)


async def _maybe_await(value: T) -> T:
    if isawaitable(value):
        return await value
    return value


async def create_system(
    session: SessionLike,
    project_id: str,
    payload: SystemCreateRequest,
) -> SystemDetail:
    from app.modules.projects import repository as project_repo

    project = await project_repo.get_project_detail(session, project_id)
    if project is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Project not found",
            status_code=404,
            details={"project_id": project_id},
        )

    system_no = await repository.get_next_system_no(session, project_id)
    try:
        system = await repository.create_system(
            session,
            project_id=project_id,
            system_no=system_no,
            title=payload.title,
        )

        # Idempotency check: only create sections if none exist
        from app.modules.evidence import repository as evidence_repo

        existing_sections = await evidence_repo.list_system_sections(session, system.id)
        if not existing_sections:
            await repository.create_system_sections(
                session,
                system_id=system.id,
                sections=_resolve_system_sections(project.thesis_schema_json),
            )

        await _maybe_await(session.commit())
    except IntegrityError as exc:
        await _maybe_await(session.rollback())
        exc_text = str(exc)
        is_system_no_conflict = (
            "uq_experimental_systems_project_system_no" in exc_text
            or "experimental_systems.project_id, experimental_systems.system_no" in exc_text
        )
        if is_system_no_conflict:
            raise AppException(
                code=ErrorCode.CONFLICT.value,
                message="System number conflict, please retry",
                status_code=409,
                details={"project_id": project_id},
            ) from exc
        raise

    stored = await repository.get_system_by_id(session, system.id)
    if stored is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found after creation",
            status_code=500,
            details={"system_id": system.id},
        )
    return _build_system_detail(stored)


async def delete_system(
    session: SessionLike,
    system_id: str,
) -> None:
    system = await repository.get_system_by_id(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    await repository.delete_system_by_id(session, system_id)
    await _maybe_await(session.commit())


async def get_system_detail(
    session: SessionLike,
    system_id: str,
) -> SystemDetail:
    system = await repository.get_system_by_id(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )
    return _build_system_detail(system)


async def update_system_definition(
    session: SessionLike,
    system_id: str,
    payload: SystemUpdateRequest,
) -> SystemDetail:
    system = await repository.get_system_by_id(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    update_fields = payload.model_dump(exclude_none=True)
    if update_fields:
        await repository.update_system_fields(session, system, **update_fields)
    await _maybe_await(session.commit())

    stored = await repository.get_system_by_id(session, system_id)
    if stored is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found after update",
            status_code=500,
            details={"system_id": system_id},
        )
    return _build_system_detail(stored)


async def get_workflow_snapshot(
    session: SessionLike,
    system_id: str,
) -> WorkflowSnapshot | None:
    system = await repository.get_system_by_id(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    statement = (
        select(WorkflowInstance)
        .where(
            WorkflowInstance.system_id == system_id,
            WorkflowInstance.workflow_key == "system_advance",
        )
        .order_by(WorkflowInstance.created_at.desc(), WorkflowInstance.version.desc())
        .limit(1)
    )
    result = await _maybe_await(session.execute(statement))
    instance = result.scalar_one_or_none()
    if instance is None:
        return None

    event_statement = (
        select(WorkflowEvent)
        .where(WorkflowEvent.instance_id == instance.id)
        .order_by(WorkflowEvent.created_at.asc(), WorkflowEvent.id.asc())
    )
    event_result = await _maybe_await(session.execute(event_statement))
    events = list(event_result.scalars().all())
    snapshot = _build_workflow_snapshot(instance, events)
    active_gate = resolve_active_gate(system)
    gate_review = await _review_gate(session, system, active_gate)

    snapshot.current_state = system.status
    snapshot.current_gate = active_gate.value
    snapshot.latest_blockers = gate_review.blockers

    return snapshot


async def advance_system(
    session: SessionLike,
    system_id: str,
    broadcaster: TaskBroadcaster | None = None,
) -> AdvanceResponse:
    system = await repository.get_system_by_id(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    active_gate = resolve_active_gate(system)

    gate_review = await _review_gate(session, system, active_gate)

    current_state = SystemState(system.status)
    target_state = GATE_TARGET_STATE.get(active_gate, SystemState.SYSTEM_DEFINED)

    task_service = TaskWorkflowService(session)  # type: ignore[arg-type]

    if not gate_review.satisfied:
        return await _handle_gate_blocked(
            session=session,
            task_service=task_service,
            system=system,
            active_gate=active_gate,
            current_state=current_state,
            blockers=gate_review.blockers,
            broadcaster=broadcaster,
        )

    return await _handle_gate_passed(
        session=session,
        task_service=task_service,
        system=system,
        active_gate=active_gate,
        current_state=current_state,
        target_state=target_state,
        broadcaster=broadcaster,
    )


async def _handle_gate_blocked(
    *,
    session: SessionLike,
    task_service: TaskWorkflowService,
    system: ExperimentalSystem,
    active_gate: GateKey,
    current_state: SystemState,
    blockers: list[Blocker],
    broadcaster: TaskBroadcaster | None,
) -> AdvanceResponse:
    wf_result: WorkflowStartResult = await start_system_workflow(
        task_service,
        WorkflowCommand(
            project_id=system.project_id,
            system_id=system.id,
            workflow_key="system_advance",
            current_state=current_state.value,
            target_state=current_state.value,
            current_gate=active_gate.value,
            status=TaskStatus.WAITING_USER,
            message=f"Gate {active_gate} blocked: requirements not met",
            event_type=EventType.GATE_BLOCKED,
        ),
    )

    snapshot = await task_service.record_gate_blocked(
        workflow_id=wf_result.handle.workflow_id,
        message=f"Gate {active_gate} blocked",
        blockers=blockers,
        current_gate=active_gate.value,
        current_state=current_state.value,
    )

    await _maybe_await(session.commit())

    if broadcaster is not None:
        await broadcaster.publish(
            TaskEvent(
                type=EventType.GATE_BLOCKED,
                task_id=wf_result.handle.job_id,
                workflow_id=wf_result.handle.workflow_id,
                project_id=system.project_id,
                system_id=system.id,
                status=TaskStatus.WAITING_USER,
                message=f"Gate {active_gate} blocked: requirements not met",
            )
        )

    return AdvanceResponse(
        outcome="blocked",
        gate=active_gate,
        current_state=current_state,
        blockers=blockers,
        snapshot=snapshot,
    )


async def _handle_gate_passed(
    *,
    session: SessionLike,
    task_service: TaskWorkflowService,
    system: ExperimentalSystem,
    active_gate: GateKey,
    current_state: SystemState,
    target_state: SystemState,
    broadcaster: TaskBroadcaster | None,
) -> AdvanceResponse:
    system.status = target_state.value
    await _maybe_await(session.flush())

    wf_result: WorkflowStartResult = await start_system_workflow(
        task_service,
        WorkflowCommand(
            project_id=system.project_id,
            system_id=system.id,
            workflow_key="system_advance",
            current_state=target_state.value,
            target_state=target_state.value,
            current_gate=active_gate.value,
            status=TaskStatus.SUCCEEDED,
            message=f"Gate {active_gate} passed: {current_state} -> {target_state}",
            event_type=EventType.GATE_PASSED,
        ),
    )

    snapshot = await task_service.record_gate_passed(
        workflow_id=wf_result.handle.workflow_id,
        message=f"Gate {active_gate} passed",
        current_gate=active_gate.value,
        from_state=current_state.value,
        to_state=target_state.value,
    )

    await _maybe_await(session.commit())

    if broadcaster is not None:
        await broadcaster.publish(
            TaskEvent(
                type=EventType.GATE_PASSED,
                task_id=wf_result.handle.job_id,
                workflow_id=wf_result.handle.workflow_id,
                project_id=system.project_id,
                system_id=system.id,
                status=TaskStatus.SUCCEEDED,
                message=f"Gate {active_gate} passed: {current_state} -> {target_state}",
            )
        )

    return AdvanceResponse(
        outcome="accepted",
        gate=active_gate,
        from_state=current_state,
        to_state=target_state,
        handle=wf_result.handle,
        snapshot=snapshot,
    )


async def _review_gate(
    session: SessionLike,
    system: ExperimentalSystem,
    active_gate: GateKey,
) -> GateReview:
    if isinstance(session, AsyncSession):
        return await session.run_sync(
            lambda sync_session: review_gate(sync_session, system, active_gate)
        )

    sync_session = _get_sync_session(session)
    return review_gate(sync_session, system, active_gate)


def _resolve_system_sections(thesis_schema_json: Any) -> list[tuple[str, str]]:
    schema = thesis_schema_json if isinstance(thesis_schema_json, dict) else {}
    for source_key in ("outline", "chapters"):
        sections = _parse_section_source(schema.get(source_key))
        if sections:
            return sections
    return list(DEFAULT_SYSTEM_SECTIONS)


def _parse_section_source(raw_sections: Any) -> list[tuple[str, str]]:
    if not isinstance(raw_sections, list):
        return []

    parsed_sections: list[tuple[str, str]] = []
    seen_section_keys: set[str] = set()
    for index, raw_section in enumerate(raw_sections, start=1):
        parsed = _normalize_section_source_item(raw_section, fallback_index=index)
        if parsed is None:
            continue

        section_key, title = parsed
        if section_key in seen_section_keys:
            continue

        seen_section_keys.add(section_key)
        parsed_sections.append((section_key, title))

    return parsed_sections


def _normalize_section_source_item(
    raw_section: Any,
    *,
    fallback_index: int,
) -> tuple[str, str] | None:
    raw_key: str | None = None
    title: str | None = None
    explicit_key_provided = False

    if isinstance(raw_section, str):
        title = raw_section.strip()
        raw_key = title
    elif isinstance(raw_section, dict):
        raw_key = _first_non_blank_str(
            raw_section.get("section_key"),
            raw_section.get("sectionKey"),
            raw_section.get("key"),
            raw_section.get("id"),
        )
        explicit_key_provided = raw_key is not None
        title = (
            _first_non_blank_str(
                raw_section.get("title"),
                raw_section.get("name"),
                raw_section.get("label"),
            )
            or raw_key
        )

    if not title:
        return None

    if explicit_key_provided and raw_key:
        return raw_key, title

    section_key = _normalize_section_key(title, fallback_index=fallback_index)
    return section_key, title


def _normalize_section_key(raw_value: str, *, fallback_index: int) -> str:
    candidate = raw_value.strip()
    if not candidate:
        return f"section_{fallback_index}"

    normalized = re.sub(r"\s+", "_", candidate.lower())
    normalized = re.sub(r"[^\w]+", "_", normalized)
    normalized = normalized.strip("_")
    return normalized or f"section_{fallback_index}"


def _first_non_blank_str(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized
    return None


def _build_system_detail(system: ExperimentalSystem) -> SystemDetail:
    sections = sorted(system.sections, key=lambda s: (s.order_no, s.section_key))
    return SystemDetail(
        id=system.id,
        project_id=system.project_id,
        system_no=system.system_no,
        title=system.title,
        status=system.status,
        sections=[
            SystemSectionSummary(
                id=section.id,
                section_key=section.section_key,
                title=section.title,
                order_no=section.order_no,
            )
            for section in sections
        ],
        created_at=system.created_at,
        updated_at=system.updated_at,
    )


def _build_workflow_snapshot(
    instance: WorkflowInstance,
    events: list[WorkflowEvent],
) -> WorkflowSnapshot:
    event_records = [_serialize_event(e) for e in events]
    latest_event = event_records[-1] if event_records else None
    latest_blockers = instance.context_json.get("latest_blockers", [])

    return WorkflowSnapshot(
        workflow_id=instance.id,
        job_id=f"{instance.workflow_key}:{instance.system_id}:{instance.version}",
        project_id=instance.project_id,
        system_id=instance.system_id,
        workflow_key=instance.workflow_key,
        current_state=instance.current_state,
        current_gate=instance.current_gate,
        status=TaskStatus(instance.status),
        context=dict(instance.context_json),
        version=instance.version,
        started_at=instance.started_at,
        completed_at=instance.completed_at,
        last_error=instance.last_error,
        latest_event=latest_event,
        latest_blockers=[Blocker.model_validate(b) for b in latest_blockers],
        events=event_records,
    )


def _serialize_event(event: WorkflowEvent) -> WorkflowEventRecord:
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


def _get_sync_session(session: SessionLike) -> Session:
    if isinstance(session, AsyncSession):
        return session.sync_session
    if isinstance(session, Session):
        return session
    return getattr(session, "sync_session", session)  # type: ignore[return-value]


__all__ = [
    "advance_system",
    "create_system",
    "delete_system",
    "get_system_detail",
    "get_workflow_snapshot",
    "update_system_definition",
]
