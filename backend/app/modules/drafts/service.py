from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
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
    DraftChatMessageDetail,
    DraftContextClaimDetail,
    DraftContextPack,
    DraftValidateResponse,
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
from app.persistence.models.evidence import AnalysisRun, ClaimEvidenceLink
from app.persistence.models.system import SystemSection
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
            current_gate=GateKey.G2.value,
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

        # Fetch evidence links and snapshot fingerprint for enhanced outline
        from app.modules.evidence import repository as evidence_repo
        all_links = await evidence_repo.list_claim_evidence_links_for_system(session, system.id)
        snapshot = await evidence_repo.get_latest_g4_snapshot(session, system.id)
        fingerprint = snapshot.fingerprint if snapshot else None

        sections = await evidence_repo.list_system_sections(session, system.id)
        all_runs = await evidence_repo.list_analysis_runs_for_system(session, system.id)
        succeeded_runs = [r for r in all_runs if r.status == "succeeded"]

        version = await repository.get_next_outline_version(session, system.id)
        outline = await repository.create_outline(
            session,
            system_id=system.id,
            version=version,
            status="draft",
            outline_json=_build_generated_outline_json(
                sections, claims, all_links, succeeded_runs, fingerprint,
            ),
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
                current_gate=GateKey.G2.value,
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

    # Coverage validation: every section needs ≥1 binding
    bindings = await repository.list_outline_bindings(session, outline_id)
    sections = await repository.list_system_sections(session, outline.system_id)
    bound_sections = {b.section_key for b in bindings}
    missing_bindings = [s for s in sections if s.section_key not in bound_sections]
    if missing_bindings:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Every section needs at least one binding before confirming",
            status_code=422,
            details={
                "outline_id": outline_id,
                "missing_sections": [s.section_key for s in missing_bindings],
            },
        )

    # Coverage validation: every referenced claim needs ≥1 evidence link
    outline_json = outline.outline_json or {}
    referenced_claim_ids: set[str] = set()
    for sec in outline_json.get("sections", []):
        for cid in sec.get("claimIds", sec.get("claim_ids", [])):
            referenced_claim_ids.add(cid)
    if referenced_claim_ids:
        from app.modules.evidence import repository as evidence_repo
        all_links = await evidence_repo.list_claim_evidence_links_for_system(
            session, outline.system_id
        )
        claims_with_links = {lnk.claim_record_id for lnk in all_links}
        claims_without_links = referenced_claim_ids - claims_with_links
        if claims_without_links:
            raise AppException(
                code=ErrorCode.VALIDATION_ERROR.value,
                message="Referenced claims must have at least one evidence link",
                status_code=422,
                details={
                    "outline_id": outline_id,
                    "claims_without_links": list(claims_without_links),
                },
            )

    # Staleness detection (warning only, stored in response)
    staleness_warning: str | None = None
    outline_fingerprint = (outline_json.get("meta") or {}).get("fingerprint")
    if outline_fingerprint:
        from app.modules.evidence import repository as evidence_repo
        snapshot = await evidence_repo.get_latest_g4_snapshot(session, outline.system_id)
        if snapshot and snapshot.fingerprint != outline_fingerprint:
            staleness_warning = (
                f"Outline fingerprint ({outline_fingerprint}) does not match "
                f"current snapshot ({snapshot.fingerprint}). Consider regenerating."
            )

    target_status = payload.status if payload is not None else "confirmed"
    outline = await repository.update_outline_status(session, outline, target_status)
    await _maybe_await(session.commit())

    detail = await _build_outline_detail_with_bindings(session, outline)
    if staleness_warning:
        detail.staleness_warning = staleness_warning
    return detail


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
            current_gate=GateKey.G3.value,
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
                current_gate=GateKey.G3.value,
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
        traceability_json=draft.traceability_json or [],
        traceability_stale=bool(draft.traceability_stale),
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


def _build_generated_outline_json(
    sections: list[SystemSection],
    claims: list[Claim],
    links: list[ClaimEvidenceLink] | None = None,
    runs: list[AnalysisRun] | None = None,
    fingerprint: str | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "generatedAt": datetime.now(UTC).isoformat(),
    }
    if fingerprint:
        meta["fingerprint"] = fingerprint
    meta["claimRefs"] = [
        {"claimId": c.claim_id, "version": c.version} for c in claims
    ]
    meta["inputSummary"] = {
        "sectionCount": len(sections),
        "claimCount": len(claims),
        "linkCount": len(links or []),
        "runCount": len(runs or []),
    }

    links_by_claim: dict[str, list[ClaimEvidenceLink]] = {}
    for lnk in (links or []):
        links_by_claim.setdefault(lnk.claim_record_id, []).append(lnk)

    claims_by_section: dict[str, list[Claim]] = {}
    for claim in claims:
        claims_by_section.setdefault(claim.section_ref, []).append(claim)

    runs_by_id: dict[str, AnalysisRun] = {}
    for r in (runs or []):
        runs_by_id[r.id] = r

    sections_out: list[dict[str, Any]] = []
    for section in sections:
        section_claims = claims_by_section.get(section.section_key, [])

        evidence_link_refs: list[dict[str, Any]] = []
        linked_run_ids: set[str] = set()
        for claim in section_claims:
            for lnk in links_by_claim.get(claim.id, []):
                strength = (
                    lnk.statistical_support.get("strength")
                    if lnk.statistical_support
                    else None
                )
                evidence_link_refs.append({
                    "claimId": claim.claim_id,
                    "assetId": lnk.asset_id,
                    "strength": strength or "unknown",
                })
                if lnk.analysis_run_id:
                    linked_run_ids.add(lnk.analysis_run_id)

        analysis_run_refs: list[dict[str, Any]] = []
        for run_id in linked_run_ids:
            run = runs_by_id.get(run_id)
            if run is not None:
                analysis_run_refs.append({
                    "runId": run.id,
                    "status": run.status,
                    "summary": run.summary,
                })

        has_claims = len(section_claims) > 0
        has_links = len(evidence_link_refs) > 0
        if has_claims and has_links:
            coverage = "covered"
        elif has_claims:
            coverage = "partial"
        else:
            coverage = "uncovered"

        nodes = _build_outline_nodes(section_claims, links_by_claim)
        binding_suggestions = _suggest_outline_bindings_for_section(
            section_claims, links_by_claim
        )
        sections_out.append({
            "sectionKey": section.section_key,
            "sectionTitle": section.title,
            "claimIds": [c.id for c in section_claims],
            "evidenceLinkRefs": evidence_link_refs,
            "analysisRunRefs": analysis_run_refs,
            "nodes": nodes,
            "bindingSuggestions": binding_suggestions,
            "coverage": coverage,
        })

    return {"meta": meta, "sections": sections_out}


def _infer_node_type(claim: Claim) -> str:
    text = (claim.statement or "").lower()
    if any(kw in text for kw in ("背景", "综述", "文献", "background", "literature", "review")):
        return "background"
    if any(kw in text for kw in ("方法", "实验", "材料", "method", "experiment", "material")):
        return "method"
    if any(kw in text for kw in ("结果", "数据", "图", "result", "data", "figure")):
        return "result"
    return "summary"


def _get_claim_strength(
    claim: Claim, links_by_claim: dict[str, list[ClaimEvidenceLink]]
) -> str:
    claim_links = links_by_claim.get(claim.id, [])
    if not claim_links:
        return "none"
    strengths = []
    for lnk in claim_links:
        s = lnk.statistical_support.get("strength") if lnk.statistical_support else None
        if s:
            strengths.append(s)
    if not strengths:
        return "unknown"
    priority = {"strong": 3, "medium": 2, "weak": 1}
    return max(strengths, key=lambda x: priority.get(x, 0))


def _build_outline_nodes(
    section_claims: list[Claim],
    links_by_claim: dict[str, list[ClaimEvidenceLink]],
) -> list[dict[str, Any]]:
    by_type: dict[str, list[dict[str, Any]]] = {}
    for claim in section_claims:
        node_type = _infer_node_type(claim)
        strength = _get_claim_strength(claim, links_by_claim)
        entry = {"claimId": claim.claim_id, "strength": strength}
        by_type.setdefault(node_type, []).append(entry)

    nodes: list[dict[str, Any]] = []
    for node_type in ("background", "method", "result", "summary"):
        entries = by_type.get(node_type, [])
        if entries:
            best_strength = max(
                (e["strength"] for e in entries),
                key=lambda x: {"strong": 3, "medium": 2, "weak": 1, "none": 0}.get(x, 0),
            )
            nodes.append({
                "nodeType": node_type,
                "claimIds": [e["claimId"] for e in entries],
                "evidenceStrength": best_strength,
            })
    return nodes


def _suggest_outline_bindings_for_section(
    section_claims: list[Claim],
    links_by_claim: dict[str, list[ClaimEvidenceLink]],
) -> list[dict[str, Any]]:
    scored_assets: dict[str, float] = {}
    for claim in section_claims:
        for lnk in links_by_claim.get(claim.id, []):
            score = 0.0
            if lnk.statistical_support:
                score = lnk.statistical_support.get("score", 0.0)
            current = scored_assets.get(lnk.asset_id, 0.0)
            if score > current:
                scored_assets[lnk.asset_id] = score

    ranked = sorted(scored_assets.items(), key=lambda x: x[1], reverse=True)[:3]
    return [
        {"assetId": asset_id, "reason": f"Highest strength evidence (score={score})"}
        for asset_id, score in ranked
    ]


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
        if section_entry.get("sectionKey", section_entry.get("section_key")) != section_key:
            continue
        claim_ids = section_entry.get("claimIds", section_entry.get("claim_ids"))
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


# ---------------------------------------------------------------------------
# Smart Draft Generation (G4.5 → G5)
# ---------------------------------------------------------------------------

_CLAIM_TAG_RE = re.compile(r"\[Claim:([^\]]+)\]")

_DRAFT_SYSTEM_PROMPT = """你是严谨的工科材料/化学领域学术写手。
任务：将提供的结构化证据转化为连贯的学术正文。
禁止：编造数据、改变章节结构。
必须：在引用结论时标注 [Claim:claim_id] 标签。

[执行约束]
你运行在非交互式管道模式。严禁使用 AskUserQuestion 或任何需要用户交互的工具调用。
如果你有疑问或需要澄清，直接在回复正文中说明，不要试图向用户提问。
如果当前章节缺少大纲节点或已批准 claims，仍然尽可能基于已有上下文（骨架、图表计划、分析结论等）生成草稿内容。
将缺失的证据标记为 [Claim:PENDING] 占位，用户后续补充。

[项目约束 — 资产流入协议]
本系统是证据驱动的论文工作流平台。当你认为需要引入外部文献或新证据来源时，
请用以下标记包裹，解析器会自动将其流入项目资产体系：

<!-- ASSET_INGEST: type=literature_reference -->
{"title":"文献标题","authors":"作者","year":2024,"doi":"10.xxx/xxx","relevance":"为什么这篇文献对当前章节有价值"}
<!-- /ASSET_INGEST -->

当你对已生成的草稿有审阅意见时，可用：
<!-- REVIEW_SCORE -->
{"dimensions":{"originality":75,"methodology":82,"evidence_sufficiency":70,"argument_coherence":85,"writing_quality":80},"verdict":"minor_revision","key_issues":["issue1"]}
<!-- /REVIEW_SCORE -->

当你发现需要修订的具体问题时，可用：
<!-- REVISION_ITEM -->
{"severity":"major","section":"3.2","issue":"问题描述","suggestion":"修改建议"}
<!-- /REVISION_ITEM -->

这些标记是可选的——仅在你判断确实需要引入外部资源或记录审阅意见时使用。
标记之外的正文内容照常作为草稿文本处理。"""


async def assemble_draft_context(
    session: SessionLike,
    system_id: str,
    section_key: str,
) -> DraftContextPack:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    system_summary = f"实验体系: {system.title or system_id}"
    sections = await repository.list_system_sections(session, system_id)
    if section_key not in {section.section_key for section in sections}:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Section key is not defined for this system",
            status_code=422,
            details={"system_id": system_id, "section_key": section_key},
        )

    # Outline nodes for this section
    outlines = await repository.list_outlines(session, system_id)
    confirmed = [o for o in outlines if o.status in ("confirmed", "approved")]
    latest_outline = max(confirmed, key=lambda o: o.version) if confirmed else None
    section_nodes: list[dict] = []
    if latest_outline and isinstance(latest_outline.outline_json, dict):
        for sec in latest_outline.outline_json.get("sections", []):
            sk = sec.get("sectionKey", sec.get("section_key", ""))
            if sk == section_key:
                section_nodes = sec.get("nodes", [])
                break

    # Approved claims for this section
    from app.modules.evidence import repository as evidence_repo

    all_claims = await evidence_repo.list_claims(session, system_id)
    section_claims = [c for c in all_claims if c.status == "approved" and c.section_ref == section_key]

    # Build claim details with asset descriptions
    claim_details: list[DraftContextClaimDetail] = []
    for claim in section_claims:
        links = await evidence_repo.list_links_for_claim(session, claim.id)
        asset_descs: list[str] = []
        for link in links:
            asset, meta = await repository.get_asset_with_metadata(session, link.asset_id)
            if asset is None:
                continue
            if meta and meta.semantic_description:
                asset_descs.append(f"Asset {asset.id[:8]}: {meta.semantic_description}")
            else:
                asset_descs.append(f"Asset {asset.id[:8]}: {asset.file_name or 'unknown'}")
        claim_details.append(DraftContextClaimDetail(
            claim_id=claim.claim_id,
            statement=claim.statement or "",
            section_ref=claim.section_ref or "",
            asset_descriptions=asset_descs,
        ))

    # Assemble prompt text
    # --- G0: Skeleton research context ---
    skeleton_context = ""
    try:
        from app.modules.skeletons import repository as skeleton_repo
        skeletons = await skeleton_repo.list_skeletons(session, system_id)
        confirmed = [s for s in skeletons if s.status == "confirmed"]
        if confirmed:
            latest_sk = max(confirmed, key=lambda s: s.version)
            sk_json = latest_sk.skeleton_json or {}
            rq_items = sk_json.get("research_questions", [])
            arg_items = sk_json.get("argument_chains", [])
            fig_items = sk_json.get("figure_framework", [])
            analysis_items = sk_json.get("analysis_strategy", [])
            parts = []
            if rq_items:
                parts.append("研究问题:\n" + "\n".join(
                    f"  - {q.get('question', q) if isinstance(q, dict) else q}" for q in rq_items[:5]
                ))
            if arg_items:
                parts.append("论证链:\n" + "\n".join(
                    f"  - {a.get('claim', a) if isinstance(a, dict) else a}" for a in arg_items[:5]
                ))
            if analysis_items:
                parts.append("分析策略:\n" + "\n".join(
                    f"  - {a.get('method', a) if isinstance(a, dict) else a}" for a in analysis_items[:3]
                ))
            if fig_items:
                parts.append("图表框架:\n" + "\n".join(
                    f"  - Fig{f.get('figure_no', '?')}: {f.get('title', '?')} (importance={f.get('importance', 'N/A')})"
                    for f in fig_items[:5]
                ))
            if parts:
                skeleton_context = "\n".join(parts)
    except Exception:
        pass  # Skeleton module may not be available

    # --- G1: Figure Plans context ---
    figure_plan_context = ""
    try:
        from app.modules.evidence import repository as evidence_repo_fp
        all_plans = await evidence_repo_fp.list_figure_plans(session, system_id)
        section_plans = [p for p in all_plans if p.section_key == section_key]
        if section_plans:
            fp_lines = []
            for p in section_plans[:8]:
                status_tag = f"[{p.status}]" if hasattr(p, "status") else ""
                dq = f" | 数据问题: {p.data_question}" if getattr(p, "data_question", None) else ""
                et = f" | 分析结论: {p.evidence_text}" if getattr(p, "evidence_text", None) else ""
                fp_lines.append(f"  - Fig{p.figure_no}: {p.title} {status_tag}{dq}{et}")
            figure_plan_context = "图表计划:\n" + "\n".join(fp_lines)
    except Exception:
        pass

    # --- G4: Evidence gaps context ---
    evidence_gap_context = ""
    try:
        from app.modules.evidence.service import detect_evidence_gaps as _detect_gaps
        gaps = await _detect_gaps(session, system_id)
        section_gaps = [g for g in gaps if getattr(g, "section_key", None) == section_key]
        if section_gaps:
            gap_lines = [f"  - [{g.gap_type}] {g.description}" for g in section_gaps[:5]]
            evidence_gap_context = "证据缺口:\n" + "\n".join(gap_lines)
    except Exception:
        pass

    nodes_text = "\n".join(
        f"  - {n.get('title', n.get('label', ''))}: {n.get('type', '')}"
        for n in section_nodes
    ) or "  (无大纲节点)"

    claims_text = "\n".join(
        f"Claim {cd.claim_id}: \"{cd.statement}\" "
        f"(来源: {', '.join(cd.asset_descriptions) or '无关联资产'})"
        for cd in claim_details
    ) or "(无已批准 claims)"

    prompt_text = f"""{_DRAFT_SYSTEM_PROMPT}

[章节上下文]
{system_summary}
当前撰写：第 {section_key} 节
大纲结构：
{nodes_text}

[证据素材]
{claims_text}
"""

    # Append enriched G0-G4 context blocks if available
    if skeleton_context:
        prompt_text += f"\n[G0 研究框架]\n{skeleton_context}\n"
    if figure_plan_context:
        prompt_text += f"\n[G1 图表计划]\n{figure_plan_context}\n"
    if evidence_gap_context:
        prompt_text += f"\n[G4 证据缺口]\n{evidence_gap_context}\n"

    prompt_text += "\n[输出格式]\nMarkdown 正文。每个结论句末标注 [Claim:claim_id]。"

    return DraftContextPack(
        system_summary=system_summary,
        section_key=section_key,
        outline_nodes=section_nodes,
        claims=claim_details,
        prompt_text=prompt_text,
    )


def _parse_claim_tags(content_md: str) -> set[str]:
    return set(_CLAIM_TAG_RE.findall(content_md))


def _build_traceability(content_md: str) -> list[dict]:
    entries: list[dict] = []
    for match in _CLAIM_TAG_RE.finditer(content_md):
        start = content_md.rfind(".", 0, match.start()) + 1
        entries.append({
            "claim_tag": match.group(1),
            "text_excerpt": content_md[start:match.end()].strip(),
            "char_start": match.start(),
            "char_end": match.end(),
        })
    return entries


async def validate_and_save_draft(
    session: SessionLike,
    system_id: str,
    section_key: str,
    content_md: str,
    outline_id: str | None = None,
) -> DraftValidateResponse:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    sections = await repository.list_system_sections(session, system_id)
    if section_key not in {section.section_key for section in sections}:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Section key is not defined for this system",
            status_code=422,
            details={"system_id": system_id, "section_key": section_key},
        )

    # Get required claims for this section
    from app.modules.evidence import repository as evidence_repo

    all_claims = await evidence_repo.list_claims(session, system_id)
    required_ids = {c.claim_id for c in all_claims if c.status == "approved" and c.section_ref == section_key}

    # Parse tags from content
    found_tags = _parse_claim_tags(content_md)

    # Validation
    errors: list[dict] = []
    missing = required_ids - found_tags
    if missing:
        errors.append({"code": "coverage_incomplete", "missing_claims": sorted(missing)})
    invented = found_tags - required_ids
    if invented:
        errors.append({"code": "hallucinated_claims", "invented_claims": sorted(invented)})

    # Build traceability
    traceability = _build_traceability(content_md)

    # Save draft regardless (with validation status)
    version = await repository.get_next_section_draft_version(session, system_id, section_key)
    draft = await repository.create_section_draft(
        session,
        system_id=system_id,
        section_key=section_key,
        content_md=content_md,
        outline_id=outline_id,
        generated_from_claims_json=sorted(found_tags),
        status="draft" if errors else "needs_review",
        created_by_agent="claude",
        version=version,
    )
    draft.traceability_json = traceability
    draft.traceability_stale = False
    await _maybe_await(session.commit())

    # Build detail
    comments = await repository.list_review_comments(session, draft.id)
    detail = _build_draft_detail(draft, comments)

    return DraftValidateResponse(
        draft=detail,
        validation_passed=len(errors) == 0,
        errors=errors,
    )


async def send_draft_chat_message_stream(
    session: SessionLike,
    system_id: str,
    section_key: str,
    provider_name: str,
    content: str,
) -> AsyncGenerator[str, None]:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    from app.modules.evidence.chat_provider import ChatProvider as ChatCliProvider, invoke_chat_stream

    provider_value = str(provider_name)
    try:
        provider = ChatCliProvider(provider_value)
    except ValueError as exc:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message=f"Unsupported provider: {provider_value}",
            status_code=422,
            details={"provider": provider_value},
        ) from exc

    chat_session = await repository.get_active_draft_chat_session(
        session, system_id, section_key, provider_value,
    )
    if chat_session is None:
        chat_session = await repository.create_draft_chat_session(
            session, system_id=system_id, section_key=section_key, provider=provider_value,
        )
        await _maybe_await(session.commit())

    if await repository.is_draft_chat_busy(session, chat_session.id):
        raise AppException(
            code=ErrorCode.CONFLICT.value,
            message="Chat session is busy",
            status_code=409,
            details={"system_id": system_id, "section_key": section_key},
        )

    from sqlalchemy.exc import IntegrityError as _IntegrityError

    try:
        turn_index = await repository.get_draft_chat_next_turn(session, chat_session.id)
        await repository.create_draft_chat_message(
            session, session_id=chat_session.id, role="user",
            content=content, status="completed", turn_index=turn_index,
        )
        assistant_msg = await repository.create_draft_chat_message(
            session, session_id=chat_session.id, role="assistant",
            content="", status="streaming", turn_index=turn_index + 1,
        )
        from datetime import UTC
        chat_session.last_message_at = datetime.now(UTC)
        await _maybe_await(session.commit())
    except _IntegrityError:
        await _maybe_await(session.rollback())
        raise AppException(
            code=ErrorCode.CONFLICT.value,
            message="Chat session conflict",
            status_code=409,
        )

    # Build context for every message (no --resume, each call is self-contained)
    ctx = await assemble_draft_context(session, system_id, section_key)
    context = ctx.prompt_text

    # For non-first messages, prepend conversation history
    if turn_index > 0:
        history_msgs = await repository.list_draft_chat_messages(
            session, chat_session.id,
        )
        # Include last 10 turns to keep prompt reasonable
        recent = [m for m in history_msgs if m.status == "completed"][-10:]
        if recent:
            history_text = "\n\n[对话历史]\n" + "\n".join(
                f"{'用户' if m.role == 'user' else '助手'}: {m.content[:500]}"
                for m in recent
            )
            context = context + history_text

    async def _stream() -> AsyncGenerator[str, None]:
        collected: list[str] = []

        try:
            async for chunk in invoke_chat_stream(
                provider, content,
                session_id=None,
                context=context,
            ):
                if chunk.strip().startswith("__SESSION_ID__:"):
                    continue  # Skip session_id lines (no-session-persistence mode)
                collected.append(chunk)
                yield f"data: {json.dumps({'type': 'delta', 'content': chunk})}\n\n"

            assistant_msg.content = "".join(collected)
            assistant_msg.status = "completed"
            from datetime import UTC
            chat_session.last_message_at = datetime.now(UTC)

            # --- Skill output parsing: extract structured blocks ---
            from app.modules.drafts.skill_output_parser import parse_skill_output

            parse_result = parse_skill_output(assistant_msg.content)
            if parse_result.has_structured_blocks:
                # Store clean text (blocks removed) as the message content
                assistant_msg.content = parse_result.clean_text
                # Notify frontend about extracted assets/reviews
                if parse_result.assets:
                    yield f"data: {json.dumps({'type': 'skill_assets', 'content': json.dumps([{'asset_type': a.asset_type, 'payload': a.payload} for a in parse_result.assets])})}\n\n"
                if parse_result.review_scores:
                    yield f"data: {json.dumps({'type': 'skill_review', 'content': json.dumps([r.payload for r in parse_result.review_scores])})}\n\n"
                if parse_result.revision_items:
                    yield f"data: {json.dumps({'type': 'skill_revisions', 'content': json.dumps([r.payload for r in parse_result.revision_items])})}\n\n"

            await _maybe_await(session.commit())
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
        except Exception as exc:
            assistant_msg.content = "".join(collected)
            assistant_msg.status = "failed"
            assistant_msg.error_text = str(exc)
            # Reset provider_session_id so next call starts fresh
            chat_session.provider_session_id = None
            await _maybe_await(session.commit())
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"

    return _stream()


async def list_draft_chat_messages(
    session: SessionLike,
    system_id: str,
    section_key: str,
    provider: str = "claude",
) -> list[DraftChatMessageDetail]:
    chat_session = await repository.get_active_draft_chat_session(
        session, system_id, section_key, provider,
    )
    if chat_session is None:
        return []

    messages = await repository.list_draft_chat_messages(session, chat_session.id)
    return [
        DraftChatMessageDetail(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            status=m.status,
            turn_index=m.turn_index,
            error_text=m.error_text,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in messages
        if m.status != "streaming"
    ]


__all__ = [
    "DRAFT_TASK_START_DELAY_SECONDS",
    "add_review_comment",
    "approve_section_draft",
    "assemble_draft_context",
    "bind_outline_assets",
    "complete_outline_generation",
    "complete_section_draft_generation",
    "confirm_outline",
    "generate_outline",
    "generate_section_draft",
    "get_draft_task_session_bind",
    "list_draft_chat_messages",
    "list_outlines",
    "list_section_drafts",
    "run_outline_generation_task",
    "run_section_draft_generation_task",
    "send_draft_chat_message_stream",
    "validate_and_save_draft",
]
