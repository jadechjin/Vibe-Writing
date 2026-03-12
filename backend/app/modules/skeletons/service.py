from __future__ import annotations

from datetime import UTC, datetime
from inspect import isawaitable
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.common.enums import EventType, GateKey, TaskStatus
from app.common.errors import ErrorCode
from app.common.schemas import JobHandle
from app.core.exceptions import AppException
from app.modules.skeletons import repository
from app.modules.skeletons.schemas import (
    SkeletonConfirmResponse,
    SkeletonDetail,
    SkeletonGenerateRequest,
    SkeletonPatchRequest,
    SkeletonReviseRequest,
    SkeletonSummary,
)
from app.modules.tasks.service import TaskWorkflowService
from app.persistence.models.evidence import Claim
from app.persistence.models.skeleton import StructureSkeleton
from app.persistence.models.system import ExperimentalSystem, SystemSection
from app.realtime.broadcaster import TaskBroadcaster
from app.workflows.system_workflow import WorkflowCommand, start_system_workflow

SessionLike = AsyncSession | Session
T = TypeVar("T")


async def _maybe_await(value: T) -> T:
    if isawaitable(value):
        return await value
    return value


def _to_detail(s: StructureSkeleton) -> SkeletonDetail:
    return SkeletonDetail(
        id=s.id,
        system_id=s.system_id,
        version=s.version,
        skeleton_json=s.skeleton_json or {},
        change_summary=s.change_summary,
        source_asset_ids=s.source_asset_ids or [],
        status=s.status,
        confirmed_at=s.confirmed_at,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _to_summary(s: StructureSkeleton) -> SkeletonSummary:
    return SkeletonSummary(
        id=s.id,
        version=s.version,
        status=s.status,
        change_summary=s.change_summary,
        created_at=s.created_at,
    )


async def _load_system(session: SessionLike, system_id: str) -> ExperimentalSystem:
    system = await repository.get_system(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )
    return system


async def _load_skeleton(session: SessionLike, skeleton_id: str) -> StructureSkeleton:
    skeleton = await repository.get_skeleton_by_id(session, skeleton_id)
    if skeleton is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Skeleton not found",
            status_code=404,
            details={"skeleton_id": skeleton_id},
        )
    return skeleton


def _get_task_session(session: SessionLike) -> AsyncSession:
    if isinstance(session, AsyncSession):
        return session
    raise TypeError("Expected AsyncSession for workflow operations")


async def generate_skeleton(
    session: SessionLike,
    system_id: str,
    payload: SkeletonGenerateRequest,
    broadcaster: TaskBroadcaster | None = None,
) -> JobHandle:
    system = await _load_system(session, system_id)
    task_service = TaskWorkflowService(_get_task_session(session))
    started = await start_system_workflow(
        task_service,
        WorkflowCommand(
            project_id=system.project_id,
            system_id=system.id,
            workflow_key="skeleton_generate",
            current_state=system.status,
            target_state=system.status,
            current_gate=GateKey.G0.value,
            status=TaskStatus.QUEUED,
            context={
                "source_asset_ids": payload.source_asset_ids,
                "user_intent": payload.user_intent,
            },
            message="Skeleton generation started",
            event_type=EventType.TASK_CREATED,
        ),
    )
    await _maybe_await(session.commit())
    return started.handle


async def list_skeletons(session: SessionLike, system_id: str) -> list[SkeletonSummary]:
    await _load_system(session, system_id)
    skeletons = await repository.list_skeletons(session, system_id)
    return [_to_summary(s) for s in skeletons]


async def get_skeleton(session: SessionLike, skeleton_id: str) -> SkeletonDetail:
    skeleton = await _load_skeleton(session, skeleton_id)
    return _to_detail(skeleton)


async def patch_skeleton(
    session: SessionLike,
    skeleton_id: str,
    payload: SkeletonPatchRequest,
) -> SkeletonDetail:
    skeleton = await _load_skeleton(session, skeleton_id)

    if skeleton.status == "confirmed":
        next_version = await repository.get_next_version(session, skeleton.system_id)
        new_skeleton = StructureSkeleton(
            system_id=skeleton.system_id,
            version=next_version,
            skeleton_json=payload.skeleton_json or skeleton.skeleton_json,
            change_summary=payload.change_summary or skeleton.change_summary,
            source_asset_ids=skeleton.source_asset_ids,
            status="draft",
        )
        session.add(new_skeleton)
        await _maybe_await(session.flush())
        await _maybe_await(session.commit())
        return _to_detail(new_skeleton)

    if payload.skeleton_json is not None:
        skeleton.skeleton_json = payload.skeleton_json
    if payload.change_summary is not None:
        skeleton.change_summary = payload.change_summary
    skeleton.updated_at = datetime.now(UTC)
    await _maybe_await(session.flush())
    await _maybe_await(session.commit())
    return _to_detail(skeleton)


async def confirm_skeleton(
    session: SessionLike,
    skeleton_id: str,
) -> SkeletonConfirmResponse:
    skeleton = await _load_skeleton(session, skeleton_id)

    if skeleton.status == "confirmed":
        return SkeletonConfirmResponse(skeleton=_to_detail(skeleton), affected_claims=[])

    skeleton.status = "confirmed"
    skeleton.confirmed_at = datetime.now(UTC)
    skeleton.updated_at = datetime.now(UTC)

    sections_data = (skeleton.skeleton_json or {}).get("sections", [])
    system_id = skeleton.system_id

    result = await _maybe_await(session.execute(
        select(SystemSection).where(SystemSection.system_id == system_id)
    ))
    existing_sections = list(result.scalars().all())
    for sec in existing_sections:
        await _maybe_await(session.delete(sec))
    await _maybe_await(session.flush())

    for idx, sec in enumerate(sections_data):
        new_section = SystemSection(
            system_id=system_id,
            section_key=sec.get("key", f"section_{idx}"),
            title=sec.get("title", ""),
            order_no=idx,
        )
        session.add(new_section)
    await _maybe_await(session.flush())

    new_section_keys = {sec.get("key", f"section_{idx}") for idx, sec in enumerate(sections_data)}
    claim_result = await _maybe_await(session.execute(
        select(Claim).where(
            Claim.system_id == system_id,
            Claim.status == "approved",
        )
    ))
    all_approved_claims = list(claim_result.scalars().all())
    affected = [
        {"claim_id": c.claim_id, "section_ref": c.section_ref}
        for c in all_approved_claims
        if c.section_ref not in new_section_keys
    ]

    await _maybe_await(session.commit())
    return SkeletonConfirmResponse(skeleton=_to_detail(skeleton), affected_claims=affected)
async def revise_skeleton(
    session: SessionLike,
    system_id: str,
    payload: SkeletonReviseRequest,
    broadcaster: TaskBroadcaster | None = None,
) -> JobHandle:
    system = await _load_system(session, system_id)
    skeleton = await _load_skeleton(session, payload.skeleton_id)
    task_service = TaskWorkflowService(_get_task_session(session))
    started = await start_system_workflow(
        task_service,
        WorkflowCommand(
            project_id=system.project_id,
            system_id=system.id,
            workflow_key="skeleton_revise",
            current_state=system.status,
            target_state=system.status,
            current_gate=GateKey.G0.value,
            status=TaskStatus.QUEUED,
            context={
                "skeleton_id": skeleton.id,
                "feedback": payload.feedback,
            },
            message="Skeleton revision started",
            event_type=EventType.TASK_CREATED,
        ),
    )
    await _maybe_await(session.commit())
    return started.handle
