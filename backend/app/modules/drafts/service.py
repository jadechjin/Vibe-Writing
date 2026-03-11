from __future__ import annotations

import asyncio
from inspect import isawaitable
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.common.enums import EventType, GateKey, TaskStatus
from app.common.errors import ErrorCode
from app.common.events import TaskEvent
from app.core.exceptions import AppException
from app.modules.drafts import repository
from app.modules.drafts.schemas import (
    OutlineBindingCreateRequest,
    OutlineBindingDetail,
    OutlineConfirmRequest,
    OutlineDetail,
    OutlineGenerateAcceptedResponse,
    ReviewCommentCreateRequest,
    ReviewCommentDetail,
    SectionDraftApproveRequest,
    SectionDraftDetail,
    SectionDraftGenerateAcceptedResponse,
)
from app.modules.tasks.service import TaskWorkflowService
from app.persistence.models import Claim, Outline, OutlineAssetBinding, ReviewComment, SectionDraft
from app.realtime.broadcaster import TaskBroadcaster
from app.workflows.system_workflow import (
    WorkflowCommand,
    WorkflowEventCommand,
    append_system_workflow_event,
    start_system_workflow,
)

SessionLike = AsyncSession | Session
T = TypeVar("T")

DRAFT_TASK_START_DELAY_SECONDS = 0.05


class _SyncTaskSessionAdapter:
    def __init__(self, session: Session) -> None:
        self.sync_session = session

    def add(self, instance: object) -> None:
        self.sync_session.add(instance)

    async def flush(self) -> None:
        self.sync_session.flush()

    async def refresh(self, instance: object) -> None:
        self.sync_session.refresh(instance)

    async def execute(self, statement):
        return self.sync_session.execute(statement)

    async def commit(self) -> None:
        self.sync_session.commit()


async def _maybe_await(value: T) -> T:
    if isawaitable(value):
        return await value
    return value


async def generate_outline(
    session: SessionLike,
    system_id: str,
    broadcaster: TaskBroadcaster | None = None,
) -> OutlineGenerateAcceptedResponse:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    task_service = TaskWorkflowService(_get_task_session(session))  # type: ignore[arg-type]
    started = await start_system_workflow(
        task_service,
        WorkflowCommand(
            project_id=system.project_id,
            system_id=system.id,
            workflow_key="outline_generate",
            current_state=system.status,
            target_state=system.status,
            current_gate=GateKey.G4.value,
            status=TaskStatus.QUEUED,
            context={},
            message="Outline generation started",
            event_type=EventType.TASK_CREATED,
        ),
    )
    await _maybe_await(session.commit())

    if broadcaster is not None:
        await _publish_task_event(
            broadcaster,
            type=EventType.TASK_CREATED,
            task_id=started.handle.job_id,
            workflow_id=started.handle.workflow_id,
            project_id=system.project_id,
            system_id=system.id,
            status=TaskStatus.QUEUED,
            message="Outline generation started",
        )

    return OutlineGenerateAcceptedResponse(handle=started.handle)


async def run_outline_generation_task(
    *,
    bind: object,
    use_async_session: bool,
    workflow_id: str,
    system_id: str,
    broadcaster: TaskBroadcaster | None = None,
    delay_seconds: float = 0.0,
) -> None:
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)

    if use_async_session:
        session_factory = AsyncSession(bind=bind, expire_on_commit=False)
        async with session_factory as task_session:
            await complete_outline_generation(
                task_session,
                workflow_id=workflow_id,
                system_id=system_id,
                broadcaster=broadcaster,
            )
        return

    with Session(bind=bind, expire_on_commit=False) as task_session:
        await complete_outline_generation(
            task_session,
            workflow_id=workflow_id,
            system_id=system_id,
            broadcaster=broadcaster,
        )


async def complete_outline_generation(
    session: SessionLike,
    *,
    workflow_id: str,
    system_id: str,
    broadcaster: TaskBroadcaster | None = None,
) -> None:
    task_service = TaskWorkflowService(_get_task_session(session))  # type: ignore[arg-type]
    workflow_snapshot = await task_service.get_workflow_snapshot(workflow_id=workflow_id)
    if workflow_snapshot is None or workflow_snapshot.status != TaskStatus.QUEUED:
        return

    try:
        system = await repository.get_system_with_project(session, system_id)
        if system is None:
            raise AppException(
                code=ErrorCode.NOT_FOUND.value,
                message="System not found",
                status_code=404,
                details={"system_id": system_id},
            )

        claims = await _list_approved_claims_for_system(session, system.id)
        version = await repository.get_next_outline_version(session, system.id)
        outline = await repository.create_outline(
            session,
            system_id=system.id,
            version=version,
            status="draft",
            outline_json=_build_generated_outline_json(claims),
            generated_from_claims_json=[claim.id for claim in claims],
        )

        await append_system_workflow_event(
            task_service,
            WorkflowEventCommand(
                workflow_id=workflow_id,
                event_type=EventType.TASK_SUCCEEDED,
                message="Outline generation completed",
                status=TaskStatus.SUCCEEDED,
                from_state=system.status,
                to_state=system.status,
                current_state=system.status,
                current_gate=GateKey.G4.value,
                payload={
                    "outline_id": outline.id,
                    "outline_version": outline.version,
                    "outline_status": outline.status,
                },
                context_update={
                    "outline_id": outline.id,
                    "outline_version": outline.version,
                    "outline_status": outline.status,
                },
            ),
        )
        await _maybe_await(session.commit())

        if broadcaster is not None:
            await _publish_task_event(
                broadcaster,
                type=EventType.TASK_SUCCEEDED,
                task_id=workflow_snapshot.job_id,
                workflow_id=workflow_snapshot.workflow_id,
                project_id=workflow_snapshot.project_id,
                system_id=system.id,
                status=TaskStatus.SUCCEEDED,
                message="Outline generation completed",
                payload={
                    "outlineId": outline.id,
                    "outlineVersion": outline.version,
                    "outlineStatus": outline.status,
                },
            )
    except AppException as exc:
        await _record_generation_failure(
            session=session,
            task_service=task_service,
            workflow_id=workflow_id,
            workflow_snapshot=workflow_snapshot,
            message=exc.message,
            payload={"code": exc.code, "details": exc.details},
            broadcaster=broadcaster,
        )
    except Exception:
        await _record_generation_failure(
            session=session,
            task_service=task_service,
            workflow_id=workflow_id,
            workflow_snapshot=workflow_snapshot,
            message="Outline generation failed unexpectedly",
            payload={"code": ErrorCode.WORKFLOW_ERROR.value, "details": {}},
            broadcaster=broadcaster,
        )


async def list_outlines(session: SessionLike, system_id: str) -> list[OutlineDetail]:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    outlines = await repository.list_outlines(session, system_id)
    return await _build_outline_details(session, outlines)


async def confirm_outline(
    session: SessionLike,
    outline_id: str,
    payload: OutlineConfirmRequest | None = None,
) -> OutlineDetail:
    outline = await repository.get_outline(session, outline_id)
    if outline is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Outline not found",
            status_code=404,
            details={"outline_id": outline_id},
        )

    target_status = payload.status if payload is not None else "confirmed"
    outline = await repository.update_outline_status(session, outline, target_status)
    await _maybe_await(session.commit())

    return await _build_outline_detail_with_bindings(session, outline)


async def bind_outline_assets(
    session: SessionLike,
    outline_id: str,
    payload: OutlineBindingCreateRequest,
) -> OutlineBindingDetail:
    outline = await repository.get_outline(session, outline_id)
    if outline is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Outline not found",
            status_code=404,
            details={"outline_id": outline_id},
        )

    asset = await repository.get_asset(session, payload.asset_id)
    if asset is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Asset not found",
            status_code=404,
            details={"asset_id": payload.asset_id},
        )
    if asset.system_id != outline.system_id:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Asset must belong to the same system as the outline",
            status_code=422,
            details={
                "outline_id": outline.id,
                "outline_system_id": outline.system_id,
                "asset_id": asset.id,
                "asset_system_id": asset.system_id,
            },
        )

    sections = await repository.list_system_sections(session, outline.system_id)
    allowed_section_keys = {section.section_key for section in sections}
    if payload.section_key not in allowed_section_keys:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Section key is not defined for this system",
            status_code=422,
            details={
                "outline_id": outline.id,
                "section_key": payload.section_key,
            },
        )

    try:
        binding = await repository.create_outline_binding(
            session,
            outline_id=outline_id,
            asset_id=payload.asset_id,
            section_key=payload.section_key,
            binding_note=payload.description,
        )
        await _maybe_await(session.commit())
    except IntegrityError as exc:
        await _maybe_await(session.rollback())
        raise AppException(
            code=ErrorCode.CONFLICT.value,
            message="Outline asset binding already exists",
            status_code=409,
            details={
                "outline_id": outline.id,
                "asset_id": payload.asset_id,
                "section_key": payload.section_key,
            },
        ) from exc

    return _build_binding_detail(binding)


async def _build_outline_details(
    session: SessionLike,
    outlines: list[Outline],
) -> list[OutlineDetail]:
    outline_ids = [outline.id for outline in outlines]
    bindings = await repository.list_outline_bindings_for_outlines(session, outline_ids)
    bindings_by_outline_id: dict[str, list[OutlineAssetBinding]] = {}
    for binding in bindings:
        bindings_by_outline_id.setdefault(binding.outline_id, []).append(binding)

    return [
        _build_outline_detail(outline, bindings_by_outline_id.get(outline.id, []))
        for outline in outlines
    ]


async def _build_outline_detail_with_bindings(
    session: SessionLike,
    outline: Outline,
) -> OutlineDetail:
    bindings = await repository.list_outline_bindings(session, outline.id)
    return _build_outline_detail(outline, bindings)


def _build_outline_detail(
    outline: Outline,
    bindings: list[OutlineAssetBinding] | None = None,
) -> OutlineDetail:
    return OutlineDetail(
        id=outline.id,
        system_id=outline.system_id,
        version=outline.version,
        outline_json=outline.outline_json,
        generated_from_claims_json=outline.generated_from_claims_json,
        status=outline.status,
        bindings=[_build_binding_detail(binding) for binding in bindings or []],
        approved_at=outline.approved_at,
        created_at=outline.created_at,
        updated_at=outline.updated_at,
    )


def _build_binding_detail(binding: OutlineAssetBinding) -> OutlineBindingDetail:
    return OutlineBindingDetail(
        id=binding.id,
        outline_id=binding.outline_id,
        section_key=binding.section_key,
        asset_id=binding.asset_id,
        binding_note=binding.binding_note,
        created_at=binding.created_at,
        updated_at=binding.updated_at,
    )


async def _publish_task_event(
    broadcaster: TaskBroadcaster,
    *,
    type: EventType,
    task_id: str,
    workflow_id: str | None,
    project_id: str,
    system_id: str | None,
    status: TaskStatus,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    await broadcaster.publish(
        TaskEvent(
            type=type,
            task_id=task_id,
            workflow_id=workflow_id,
            project_id=project_id,
            system_id=system_id,
            status=status,
            message=message,
            payload=payload or {},
        )
    )


def _get_task_session(session: SessionLike) -> AsyncSession | _SyncTaskSessionAdapter:
    if isinstance(session, AsyncSession):
        return session
    if isinstance(session, Session):
        return _SyncTaskSessionAdapter(session)
    return _SyncTaskSessionAdapter(session.sync_session)  # type: ignore[arg-type]


def get_draft_task_session_bind(session: SessionLike) -> tuple[object, bool]:
    if isinstance(session, AsyncSession):
        bind = session.bind
        if bind is None:
            raise RuntimeError("Async session is not bound")
        return bind, True

    if isinstance(session, Session):
        return session.get_bind(), False

    return session.sync_session.get_bind(), False  # type: ignore[attr-defined]


async def generate_section_draft(
    session: SessionLike,
    system_id: str,
    section_key: str,
    outline_id: str | None = None,
    claim_ids: list[str] | None = None,
    broadcaster: TaskBroadcaster | None = None,
) -> SectionDraftGenerateAcceptedResponse:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    sections = await repository.list_system_sections(session, system.id)
    allowed_section_keys = {section.section_key for section in sections}
    if section_key not in allowed_section_keys:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Section key is not defined for this system",
            status_code=422,
            details={"system_id": system.id, "section_key": section_key},
        )

    outline: Outline | None = None
    if outline_id is not None:
        outline = await repository.get_outline(session, outline_id)
        if outline is None:
            raise AppException(
                code=ErrorCode.NOT_FOUND.value,
                message="Outline not found",
                status_code=404,
                details={"outline_id": outline_id},
            )
        if outline.system_id != system.id:
            raise AppException(
                code=ErrorCode.VALIDATION_ERROR.value,
                message="Outline must belong to the same system as the draft",
                status_code=422,
                details={
                    "system_id": system.id,
                    "outline_id": outline.id,
                    "outline_system_id": outline.system_id,
                },
            )

    normalized_claim_ids = _resolve_requested_claim_ids(
        outline=outline,
        section_key=section_key,
        requested_claim_ids=claim_ids,
    )
    claims = await repository.list_claims_by_ids(session, normalized_claim_ids)
    _validate_section_draft_claims(
        claims=claims,
        requested_claim_ids=normalized_claim_ids,
        system_id=system.id,
        section_key=section_key,
    )

    task_service = TaskWorkflowService(_get_task_session(session))  # type: ignore[arg-type]
    started = await start_system_workflow(
        task_service,
        WorkflowCommand(
            project_id=system.project_id,
            system_id=system.id,
            workflow_key="section_draft_generate",
            current_state=system.status,
            target_state=system.status,
            current_gate=GateKey.G5.value,
            status=TaskStatus.QUEUED,
            context={
                "section_key": section_key,
                "outline_id": outline_id or "",
                "claim_ids": normalized_claim_ids,
            },
            message=f"Section draft generation started for {section_key}",
            event_type=EventType.TASK_CREATED,
        ),
    )
    await _maybe_await(session.commit())

    if broadcaster is not None:
        await _publish_task_event(
            broadcaster,
            type=EventType.TASK_CREATED,
            task_id=started.handle.job_id,
            workflow_id=started.handle.workflow_id,
            project_id=system.project_id,
            system_id=system.id,
            status=TaskStatus.QUEUED,
            message=f"Section draft generation started for {section_key}",
        )

    return SectionDraftGenerateAcceptedResponse(handle=started.handle)


async def run_section_draft_generation_task(
    *,
    bind: object,
    use_async_session: bool,
    workflow_id: str,
    system_id: str,
    section_key: str,
    outline_id: str | None = None,
    claim_ids: list[str] | None = None,
    broadcaster: TaskBroadcaster | None = None,
    delay_seconds: float = 0.0,
) -> None:
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)

    normalized_claim_ids = list(claim_ids or [])

    if use_async_session:
        session_factory = AsyncSession(bind=bind, expire_on_commit=False)
        async with session_factory as task_session:
            await complete_section_draft_generation(
                task_session,
                workflow_id=workflow_id,
                system_id=system_id,
                section_key=section_key,
                outline_id=outline_id,
                claim_ids=normalized_claim_ids,
                broadcaster=broadcaster,
            )
        return

    with Session(bind=bind, expire_on_commit=False) as task_session:
        await complete_section_draft_generation(
            task_session,
            workflow_id=workflow_id,
            system_id=system_id,
            section_key=section_key,
            outline_id=outline_id,
            claim_ids=normalized_claim_ids,
            broadcaster=broadcaster,
        )


async def complete_section_draft_generation(
    session: SessionLike,
    *,
    workflow_id: str,
    system_id: str,
    section_key: str,
    outline_id: str | None = None,
    claim_ids: list[str] | None = None,
    broadcaster: TaskBroadcaster | None = None,
) -> None:
    task_service = TaskWorkflowService(_get_task_session(session))  # type: ignore[arg-type]
    workflow_snapshot = await task_service.get_workflow_snapshot(workflow_id=workflow_id)
    if workflow_snapshot is None or workflow_snapshot.status != TaskStatus.QUEUED:
        return

    try:
        system = await repository.get_system_with_project(session, system_id)
        if system is None:
            raise AppException(
                code=ErrorCode.NOT_FOUND.value,
                message="System not found",
                status_code=404,
                details={"system_id": system_id},
            )

        outline: Outline | None = None
        if outline_id is not None:
            outline = await repository.get_outline(session, outline_id)
            if outline is None:
                raise AppException(
                    code=ErrorCode.NOT_FOUND.value,
                    message="Outline not found",
                    status_code=404,
                    details={"outline_id": outline_id},
                )
            if outline.system_id != system.id:
                raise AppException(
                    code=ErrorCode.VALIDATION_ERROR.value,
                    message="Outline must belong to the same system as the draft",
                    status_code=422,
                    details={
                        "system_id": system.id,
                        "outline_id": outline.id,
                        "outline_system_id": outline.system_id,
                    },
                )

        context_claim_ids = (
            workflow_snapshot.context.get("claim_ids") if workflow_snapshot.context else None
        )
        normalized_claim_ids = (
            list(context_claim_ids) if isinstance(context_claim_ids, list) else []
        )
        if not normalized_claim_ids:
            normalized_claim_ids = _resolve_requested_claim_ids(
                outline=outline,
                section_key=section_key,
                requested_claim_ids=claim_ids,
            )
        claims = await repository.list_claims_by_ids(session, normalized_claim_ids)
        ordered_claims = _validate_section_draft_claims(
            claims=claims,
            requested_claim_ids=normalized_claim_ids,
            system_id=system.id,
            section_key=section_key,
        )
        version = await repository.get_next_section_draft_version(session, system.id, section_key)
        draft = await repository.create_section_draft(
            session,
            system_id=system.id,
            section_key=section_key,
            version=version,
            outline_id=outline_id,
            content_md=_build_generated_section_draft_content(section_key, ordered_claims),
            generated_from_claims_json=[claim.id for claim in ordered_claims],
            status="draft",
            created_by_agent="thin_workflow",
        )

        await append_system_workflow_event(
            task_service,
            WorkflowEventCommand(
                workflow_id=workflow_id,
                event_type=EventType.TASK_SUCCEEDED,
                message=f"Section draft generation completed for {section_key}",
                status=TaskStatus.SUCCEEDED,
                from_state=system.status,
                to_state=system.status,
                current_state=system.status,
                current_gate=GateKey.G5.value,
                payload={
                    "draft_id": draft.id,
                    "section_key": draft.section_key,
                    "draft_version": draft.version,
                    "draft_status": draft.status,
                },
                context_update={
                    "draft_id": draft.id,
                    "section_key": draft.section_key,
                    "draft_version": draft.version,
                    "draft_status": draft.status,
                    "claim_ids": normalized_claim_ids,
                },
            ),
        )
        await _maybe_await(session.commit())

        if broadcaster is not None:
            await _publish_task_event(
                broadcaster,
                type=EventType.TASK_SUCCEEDED,
                task_id=workflow_snapshot.job_id,
                workflow_id=workflow_snapshot.workflow_id,
                project_id=workflow_snapshot.project_id,
                system_id=system.id,
                status=TaskStatus.SUCCEEDED,
                message=f"Section draft generation completed for {section_key}",
                payload={
                    "draftId": draft.id,
                    "sectionKey": draft.section_key,
                    "draftVersion": draft.version,
                    "draftStatus": draft.status,
                },
            )
    except AppException as exc:
        await _record_generation_failure(
            session=session,
            task_service=task_service,
            workflow_id=workflow_id,
            workflow_snapshot=workflow_snapshot,
            message=exc.message,
            payload={"code": exc.code, "details": exc.details},
            broadcaster=broadcaster,
        )
    except Exception:
        await _record_generation_failure(
            session=session,
            task_service=task_service,
            workflow_id=workflow_id,
            workflow_snapshot=workflow_snapshot,
            message=f"Section draft generation failed unexpectedly for {section_key}",
            payload={"code": ErrorCode.WORKFLOW_ERROR.value, "details": {}},
            broadcaster=broadcaster,
        )


async def list_section_drafts(session: SessionLike, system_id: str) -> list[SectionDraftDetail]:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )
    drafts = await repository.list_section_drafts(session, system_id)
    return await _build_draft_details(session, drafts)


async def approve_section_draft(
    session: SessionLike,
    draft_id: str,
    payload: SectionDraftApproveRequest | None = None,
) -> SectionDraftDetail:
    draft = await repository.get_section_draft(session, draft_id)
    if draft is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Section draft not found",
            status_code=404,
            details={"draft_id": draft_id},
        )

    target_status = payload.status if payload is not None else "approved"
    draft = await repository.update_draft_status(session, draft, target_status)
    await _maybe_await(session.commit())
    return await _build_draft_detail_with_comments(session, draft)


async def add_review_comment(
    session: SessionLike,
    draft_id: str,
    payload: ReviewCommentCreateRequest,
) -> ReviewCommentDetail:
    draft = await repository.get_section_draft(session, draft_id)
    if draft is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Section draft not found",
            status_code=404,
            details={"draft_id": draft_id},
        )

    comment = await repository.create_review_comment(
        session,
        draft_id=draft_id,
        commenter_id=payload.commenter_id,
        comment_text=payload.comment_text,
        decision=payload.decision,
        context_json=payload.context_json,
    )
    await _maybe_await(session.commit())
    return _build_comment_detail(comment)


async def _build_draft_details(
    session: SessionLike,
    drafts: list[SectionDraft],
) -> list[SectionDraftDetail]:
    draft_ids = [draft.id for draft in drafts]
    comments = await repository.list_review_comments_for_drafts(session, draft_ids)
    comments_by_draft_id: dict[str, list[ReviewComment]] = {}
    for comment in comments:
        comments_by_draft_id.setdefault(comment.draft_id, []).append(comment)

    return [_build_draft_detail(draft, comments_by_draft_id.get(draft.id, [])) for draft in drafts]


async def _build_draft_detail_with_comments(
    session: SessionLike,
    draft: SectionDraft,
) -> SectionDraftDetail:
    comments = await repository.list_review_comments(session, draft.id)
    return _build_draft_detail(draft, comments)


def _build_draft_detail(
    draft: SectionDraft,
    review_comments: list[ReviewComment] | None = None,
) -> SectionDraftDetail:
    return SectionDraftDetail(
        id=draft.id,
        system_id=draft.system_id,
        outline_id=draft.outline_id,
        section_key=draft.section_key,
        version=draft.version,
        content_md=draft.content_md,
        generated_from_claims_json=draft.generated_from_claims_json,
        status=draft.status,
        review_comments=[_build_comment_detail(comment) for comment in review_comments or []],
        created_by_agent=draft.created_by_agent,
        approved_at=draft.approved_at,
        frozen_at=draft.frozen_at,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


def _build_comment_detail(comment: ReviewComment) -> ReviewCommentDetail:
    return ReviewCommentDetail(
        id=comment.id,
        draft_id=comment.draft_id,
        commenter_id=comment.commenter_id,
        comment_text=comment.comment_text,
        decision=comment.decision,
        context_json=comment.context_json,
        resolved_at=comment.resolved_at,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


async def _list_approved_claims_for_system(session: SessionLike, system_id: str) -> list[Claim]:
    statement = (
        select(Claim)
        .where(Claim.system_id == system_id, Claim.status == "approved")
        .order_by(Claim.created_at.asc(), Claim.id.asc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


def _build_generated_outline_json(claims: list[Claim]) -> dict[str, Any]:
    sections: dict[str, list[str]] = {}
    for claim in claims:
        sections.setdefault(claim.section_ref, []).append(claim.id)

    return {
        "sections": [
            {"section_key": section_key, "claim_ids": claim_ids}
            for section_key, claim_ids in sections.items()
        ]
    }


def _build_generated_section_draft_content(section_key: str, claims: list[Claim]) -> str:
    claim_lines = "\n".join(f"- {claim.statement}" for claim in claims)
    if not claim_lines:
        claim_lines = "- No approved claims provided"

    return f"# {section_key}\n\nGenerated from approved claims:\n{claim_lines}\n"


def _resolve_requested_claim_ids(
    *,
    outline: Outline | None,
    section_key: str,
    requested_claim_ids: list[str] | None,
) -> list[str]:
    normalized_claim_ids = list(requested_claim_ids or [])
    if normalized_claim_ids:
        return normalized_claim_ids

    if outline is None:
        return []

    if isinstance(outline.outline_json, dict):
        sections_payload = outline.outline_json.get("sections")
    elif isinstance(outline.outline_json, list):
        sections_payload = outline.outline_json
    else:
        return []

    if not isinstance(sections_payload, list):
        return []

    for section_entry in sections_payload:
        if not isinstance(section_entry, dict):
            continue
        if section_entry.get("section_key") != section_key:
            continue
        claim_ids = section_entry.get("claim_ids")
        if not isinstance(claim_ids, list):
            return []
        return [claim_id for claim_id in claim_ids if isinstance(claim_id, str)]

    return []


def _validate_section_draft_claims(
    *,
    claims: list[Claim],
    requested_claim_ids: list[str],
    system_id: str,
    section_key: str,
) -> list[Claim]:
    if not requested_claim_ids:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Section draft generation requires at least one approved claim",
            status_code=422,
            details={"system_id": system_id, "claim_ids": requested_claim_ids},
        )

    claim_index = {claim.id: claim for claim in claims}
    missing_claim_ids = [
        claim_id for claim_id in requested_claim_ids if claim_id not in claim_index
    ]
    if missing_claim_ids:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="One or more claims were not found",
            status_code=404,
            details={"missing_claim_ids": missing_claim_ids},
        )

    ordered_claims = [claim_index[claim_id] for claim_id in requested_claim_ids]

    cross_system_claim_ids = [claim.id for claim in ordered_claims if claim.system_id != system_id]
    if cross_system_claim_ids:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="All claims must belong to the same system as the draft",
            status_code=422,
            details={
                "system_id": system_id,
                "cross_system_claim_ids": cross_system_claim_ids,
            },
        )

    unapproved_claim_ids = [claim.id for claim in ordered_claims if claim.status != "approved"]
    if unapproved_claim_ids:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Section draft generation only accepts approved claims",
            status_code=422,
            details={"unapproved_claim_ids": unapproved_claim_ids},
        )

    mismatched_section_claim_ids = [
        claim.id for claim in ordered_claims if claim.section_ref != section_key
    ]
    if mismatched_section_claim_ids:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="All claims must belong to the requested section",
            status_code=422,
            details={
                "section_key": section_key,
                "mismatched_section_claim_ids": mismatched_section_claim_ids,
            },
        )

    return ordered_claims


async def _record_generation_failure(
    *,
    session: SessionLike,
    task_service: TaskWorkflowService,
    workflow_id: str,
    workflow_snapshot,
    message: str,
    payload: dict[str, Any],
    broadcaster: TaskBroadcaster | None,
) -> None:
    await _maybe_await(session.rollback())
    await append_system_workflow_event(
        task_service,
        WorkflowEventCommand(
            workflow_id=workflow_id,
            event_type=EventType.TASK_FAILED,
            message=message,
            status=TaskStatus.FAILED,
            current_state=workflow_snapshot.current_state,
            current_gate=workflow_snapshot.current_gate,
            payload=payload,
            last_error=message,
        ),
    )
    await _maybe_await(session.commit())

    if broadcaster is not None:
        await _publish_task_event(
            broadcaster,
            type=EventType.TASK_FAILED,
            task_id=workflow_snapshot.job_id,
            workflow_id=workflow_snapshot.workflow_id,
            project_id=workflow_snapshot.project_id,
            system_id=workflow_snapshot.system_id,
            status=TaskStatus.FAILED,
            message=message,
            payload=payload,
        )


__all__ = [
    "DRAFT_TASK_START_DELAY_SECONDS",
    "add_review_comment",
    "approve_section_draft",
    "bind_outline_assets",
    "complete_outline_generation",
    "complete_section_draft_generation",
    "confirm_outline",
    "generate_outline",
    "generate_section_draft",
    "get_draft_task_session_bind",
    "list_outlines",
    "list_section_drafts",
    "run_outline_generation_task",
    "run_section_draft_generation_task",
]
