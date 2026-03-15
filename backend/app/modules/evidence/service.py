from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from inspect import isawaitable
from io import SEEK_END
from typing import Any, BinaryIO, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.common.enums import EventType, GateKey, TaskStatus
from app.common.errors import ErrorCode
from app.common.events import TaskEvent
from app.common.storage import generate_presigned_url
from app.core.exceptions import AppException
from app.modules.assets.schemas import (
    AnalysisRunSummary,
    FigurePlanAnalyzeRequest,
    ImageAnalysisItem,
    ImageAnalysisListResponse,
)
from app.modules.assets.schemas import (
    FigurePlanAssetDetail as ImageAnalysisAssetDetail,
)
from app.modules.assets.service import create_asset_from_upload
from app.modules.evidence import repository
from app.modules.evidence.chat_provider import (
    ChatProvider as ChatCliProvider,
)
from app.modules.evidence.chat_provider import (
    invoke_chat_stream,
)
from app.modules.evidence.schemas import (
    BatchApproveClaimsResponse,
    ChatMessageDetail,
    ClaimApproveRequest,
    ClaimDetail,
    ClaimEvidenceLinkCreateRequest,
    ClaimEvidenceLinkDetail,
    EvidenceMatrixGenerateAcceptedResponse,
    FigurePlanAssetDetail,
    FigurePlanConfirmRequest,
    FigurePlanDetail,
    FigurePlanGenerateAcceptedResponse,
    FigurePlanPatchRequest,
    FigurePlanStatusTransitionRequest,
    FigurePlanUpdateBriefRequest,
)
from app.modules.tasks.service import TaskWorkflowService
from app.persistence.models import (
    AnalysisRun,
    Asset,
    Claim,
    ClaimEvidenceLink,
    FigurePlan,
    FigurePlanAsset,
    FigurePlanChatMessage,
    FigurePlanChatSession,
    SystemSection,
)
from app.persistence.models.skeleton import StructureSkeleton
from app.realtime.broadcaster import TaskBroadcaster
from app.workflows.system_workflow import (
    WorkflowCommand,
    WorkflowEventCommand,
    append_system_workflow_event,
    start_system_workflow,
)

SessionLike = AsyncSession | Session
T = TypeVar("T")

logger = logging.getLogger(__name__)

EVIDENCE_TASK_START_DELAY_SECONDS = 0.05


async def _get_confirmed_skeleton(session: SessionLike, system_id: str) -> StructureSkeleton | None:
    result = await _maybe_await(
        session.execute(
            select(StructureSkeleton)
            .where(
                StructureSkeleton.system_id == system_id,
                StructureSkeleton.status == "confirmed",
            )
            .order_by(StructureSkeleton.version.desc())
            .limit(1)
        )
    )
    return result.scalar_one_or_none()


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


async def generate_figure_plan(
    session: SessionLike,
    system_id: str,
    broadcaster: TaskBroadcaster | None = None,
) -> FigurePlanGenerateAcceptedResponse:
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
            workflow_key="figure_plan_generate",
            current_state=system.status,
            target_state=system.status,
            current_gate=GateKey.G1.value,
            status=TaskStatus.QUEUED,
            context={},
            message="Figure plan generation started",
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
            message="Figure plan generation started",
        )

    return FigurePlanGenerateAcceptedResponse(handle=started.handle)


async def run_figure_plan_generation_task(
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
            await complete_figure_plan_generation(
                task_session,
                workflow_id=workflow_id,
                system_id=system_id,
                broadcaster=broadcaster,
            )
        return

    with Session(bind=bind, expire_on_commit=False) as task_session:
        await complete_figure_plan_generation(
            task_session,
            workflow_id=workflow_id,
            system_id=system_id,
            broadcaster=broadcaster,
        )


async def complete_figure_plan_generation(
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

        skeleton = await _get_confirmed_skeleton(session, system_id)
        if skeleton is None:
            raise AppException(
                code=ErrorCode.NOT_FOUND.value,
                message="No confirmed skeleton found",
                status_code=404,
                details={"system_id": system_id},
            )

        # Idempotency: skip if this skeleton_version already has plans
        existing_plans = await repository.list_figure_plans(session, system_id)
        if any(p.skeleton_version == skeleton.version for p in existing_plans):
            await append_system_workflow_event(
                task_service,
                WorkflowEventCommand(
                    workflow_id=workflow_id,
                    event_type=EventType.TASK_SUCCEEDED,
                    message="Figure plans already exist for this skeleton version",
                    status=TaskStatus.SUCCEEDED,
                    from_state=system.status,
                    to_state=system.status,
                    current_state=system.status,
                    current_gate=GateKey.G1.value,
                    payload={"skeleton_version": skeleton.version, "skipped": True},
                    context_update={"skeleton_version": skeleton.version},
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
                    message="Figure plans already exist for this skeleton version",
                    payload={"skeletonVersion": skeleton.version, "skipped": True},
                )
            return

        figures = (skeleton.skeleton_json or {}).get("figure_framework", [])
        if not isinstance(figures, list) or not figures:
            figures = [{"figure_id": "fig1", "title": "Figure 1", "type": "chart"}]

        created_plans: list[FigurePlan] = []
        for idx, fig in enumerate(figures):
            if not isinstance(fig, dict):
                continue
            figure_id = fig.get("figure_id", f"fig{idx + 1}")
            version = await repository.get_next_figure_plan_version(session, system.id, figure_id)
            related_sections = fig.get("related_sections", [])
            section_key = (
                related_sections[0]
                if isinstance(related_sections, list) and related_sections
                else None
            )
            plan = await repository.create_figure_plan(
                session,
                system_id=system.id,
                figure_no=figure_id,
                title=fig.get("title", "Untitled"),
                claim_text=fig.get("purpose", ""),
                status="pending",
                version=version,
                section_key=section_key,
                skeleton_version=skeleton.version,
                data_needed_json=[{"assetType": "figure"}],
                method_json={"mode": "skeleton_driven"},
                acceptance_criteria_json=[{"type": "status", "value": "confirmed"}],
            )
            created_plans.append(plan)

        await append_system_workflow_event(
            task_service,
            WorkflowEventCommand(
                workflow_id=workflow_id,
                event_type=EventType.TASK_SUCCEEDED,
                message="Figure plan generation completed",
                status=TaskStatus.SUCCEEDED,
                from_state=system.status,
                to_state=system.status,
                current_state=system.status,
                current_gate=GateKey.G1.value,
                payload={
                    "figure_plan_count": len(created_plans),
                    "skeleton_version": skeleton.version,
                    "figure_plan_ids": [p.id for p in created_plans],
                },
                context_update={
                    "figure_plan_count": len(created_plans),
                    "skeleton_version": skeleton.version,
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
                message="Figure plan generation completed",
                payload={
                    "figurePlanCount": len(created_plans),
                    "skeletonVersion": skeleton.version,
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
            message="Figure plan generation failed unexpectedly",
            payload={"code": ErrorCode.WORKFLOW_ERROR.value, "details": {}},
            broadcaster=broadcaster,
        )


async def list_figure_plans(session: SessionLike, system_id: str) -> list[FigurePlanDetail]:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    plans = await repository.list_figure_plans(session, system_id)
    return [_build_figure_plan_detail(plan) for plan in plans]


async def list_image_analyses(
    session: SessionLike,
    system_id: str,
) -> ImageAnalysisListResponse:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    plans = await repository.list_figure_plans(session, system_id)
    if not plans:
        return ImageAnalysisListResponse(items=[], total=0, analyzed=0, pending=0)

    plan_ids = [plan.id for plan in plans]
    asset_rows = await repository.list_figure_plan_assets_for_system(session, system_id)
    assets_by_plan_id: dict[str, list[ImageAnalysisAssetDetail]] = {plan.id: [] for plan in plans}
    for binding, asset in asset_rows:
        assets_by_plan_id.setdefault(binding.figure_plan_id, []).append(
            _build_image_analysis_asset_detail(asset)
        )

    analysis_runs = await repository.list_analysis_runs_for_figure_plans(session, plan_ids)
    latest_run_by_plan_id = _index_latest_succeeded_runs_by_figure_plan_id(analysis_runs)

    items: list[ImageAnalysisItem] = []
    analyzed = 0
    for plan in plans:
        latest_analysis = None
        run = latest_run_by_plan_id.get(plan.id)
        if run is not None:
            latest_analysis = _build_analysis_run_summary(run)
            analyzed += 1

        items.append(
            ImageAnalysisItem(
                figure_plan_id=plan.id,
                figure_no=plan.figure_no,
                title=plan.title,
                section_key=plan.section_key,
                assets=assets_by_plan_id.get(plan.id, []),
                latest_analysis=latest_analysis,
            )
        )

    total = len(items)
    return ImageAnalysisListResponse(
        items=items,
        total=total,
        analyzed=analyzed,
        pending=total - analyzed,
    )


async def trigger_figure_plan_analysis(
    session: SessionLike,
    plan_id: str,
    payload: FigurePlanAnalyzeRequest,
) -> AnalysisRunSummary:
    plan = await repository.get_figure_plan(session, plan_id)
    if plan is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Figure plan not found",
            status_code=404,
            details={"plan_id": plan_id},
        )

    binding = await repository.get_figure_plan_asset_by_asset_id(
        session,
        figure_plan_id=plan_id,
        asset_id=payload.asset_id,
    )
    if binding is None:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Asset is not bound to this figure plan",
            status_code=422,
            details={"plan_id": plan_id, "asset_id": payload.asset_id},
        )

    run = await repository.create_analysis_run(
        session,
        system_id=plan.system_id,
        figure_plan_id=plan.id,
        asset_id=binding.asset_id,
        run_type="image_analysis",
        analysis_type=payload.analysis_type,
        status=TaskStatus.QUEUED.value,
        input_payload_json={
            "figure_plan_id": plan.id,
            "asset_id": binding.asset_id,
            "analysis_type": payload.analysis_type,
        },
    )
    await _maybe_await(session.commit())
    return _build_analysis_run_summary(run)


async def confirm_figure_plan(
    session: SessionLike,
    plan_id: str,
    payload: FigurePlanConfirmRequest | None = None,
) -> FigurePlanDetail:
    plan = await repository.get_figure_plan(session, plan_id)
    if plan is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Figure plan not found",
            status_code=404,
            details={"plan_id": plan_id},
        )

    target_status = payload.status if payload is not None else "confirmed"
    plan = await repository.update_figure_plan_status(session, plan_id, target_status)
    await _maybe_await(session.commit())

    return _build_figure_plan_detail(plan)


VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"uploaded"},
    "uploaded": {"analyzing"},
    "analyzing": {"discussing"},
    "discussing": {"draft_brief"},
    "draft_brief": {"confirmed"},
    "confirmed": {"delivered"},
    "needs_review": {"pending", "uploaded", "analyzing", "discussing", "draft_brief", "confirmed"},
}


async def update_figure_plan_brief(
    session: SessionLike,
    plan_id: str,
    payload: FigurePlanUpdateBriefRequest,
) -> FigurePlanDetail:
    plan = await repository.get_figure_plan(session, plan_id)
    if plan is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Figure plan not found",
            status_code=404,
            details={"plan_id": plan_id},
        )
    plan = await repository.update_figure_plan_brief(session, plan_id, payload.brief_text)
    await _maybe_await(session.commit())
    return _build_figure_plan_detail(plan)


async def patch_figure_plan(
    session: SessionLike,
    plan_id: str,
    payload: FigurePlanPatchRequest,
) -> FigurePlanDetail:
    plan = await repository.get_figure_plan(session, plan_id)
    if plan is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Figure plan not found",
            status_code=404,
            details={"plan_id": plan_id},
        )

    if "section_key" in payload.model_fields_set and payload.section_key is not None:
        allowed_section_keys = {
            section.section_key
            for section in await repository.list_system_sections(session, plan.system_id)
        }
        if payload.section_key not in allowed_section_keys:
            raise AppException(
                code=ErrorCode.VALIDATION_ERROR.value,
                message="Figure plan section_key is not defined for this system",
                status_code=422,
                details={
                    "plan_id": plan_id,
                    "system_id": plan.system_id,
                    "section_key": payload.section_key,
                },
            )

    old_figure_no = plan.figure_no
    try:
        plan = await repository.update_figure_plan_fields(
            session,
            plan,
            payload.model_dump(exclude_unset=True),
        )

        # Sync changes back to skeleton figure_framework
        await _sync_figure_plan_to_skeleton(
            session,
            plan=plan,
            old_figure_no=old_figure_no,
            changed_fields=payload.model_fields_set,
        )

        await _maybe_await(session.commit())
    except IntegrityError as exc:
        await _maybe_await(session.rollback())
        raise AppException(
            code=ErrorCode.CONFLICT.value,
            message="Figure plan update conflicts with an existing record",
            status_code=409,
            details={"plan_id": plan_id},
        ) from exc

    return _build_figure_plan_detail(plan)


async def _sync_figure_plan_to_skeleton(
    session: SessionLike,
    *,
    plan: FigurePlan,
    old_figure_no: str,
    changed_fields: set[str],
) -> None:
    """Sync figure_no/title changes back to the skeleton's figure_framework."""
    syncable = {"figure_no", "title", "claim_text"}
    if not (changed_fields & syncable):
        logger.debug("_sync_figure_plan_to_skeleton: no syncable fields in %s", changed_fields)
        return

    logger.info(
        "_sync_figure_plan_to_skeleton: plan=%s old_figure_no=%s skeleton_version=%s changed=%s",
        plan.id,
        old_figure_no,
        plan.skeleton_version,
        changed_fields & syncable,
    )

    # Find skeleton: by exact version if available, fallback to latest
    skeleton = None
    if plan.skeleton_version is not None:
        result = await _maybe_await(
            session.execute(
                select(StructureSkeleton)
                .where(
                    StructureSkeleton.system_id == plan.system_id,
                    StructureSkeleton.version == plan.skeleton_version,
                )
                .limit(1)
            )
        )
        skeleton = result.scalar_one_or_none()

    # Fallback: use latest skeleton if exact version not found or not set
    if skeleton is None:
        result = await _maybe_await(
            session.execute(
                select(StructureSkeleton)
                .where(StructureSkeleton.system_id == plan.system_id)
                .order_by(StructureSkeleton.version.desc())
                .limit(1)
            )
        )
        skeleton = result.scalar_one_or_none()
    if skeleton is None:
        logger.warning(
            "_sync_figure_plan_to_skeleton: no skeleton found for system=%s", plan.system_id
        )
        return

    framework = (skeleton.skeleton_json or {}).get("figure_framework")
    if not isinstance(framework, list):
        logger.warning(
            "_sync_figure_plan_to_skeleton: figure_framework is not a list in skeleton=%s",
            skeleton.id,
        )
        return

    updated = False
    for entry in framework:
        if not isinstance(entry, dict):
            continue
        if entry.get("figure_id") != old_figure_no:
            continue
        if "figure_no" in changed_fields:
            entry["figure_id"] = plan.figure_no
        if "title" in changed_fields:
            entry["title"] = plan.title
        if "claim_text" in changed_fields:
            entry["purpose"] = plan.claim_text
        updated = True
        break

    if updated:
        skeleton.skeleton_json = {**skeleton.skeleton_json, "figure_framework": framework}
        skeleton.updated_at = datetime.now(UTC)
        await _maybe_await(session.flush())
        logger.info(
            "_sync_figure_plan_to_skeleton: synced skeleton=%s version=%s",
            skeleton.id,
            skeleton.version,
        )
    else:
        logger.warning(
            (
                "_sync_figure_plan_to_skeleton: no matching figure_id=%s "
                "in skeleton=%s framework (entries: %s)"
            ),
            old_figure_no,
            skeleton.id,
            [
                entry.get("figure_id")
                for entry in framework
                if isinstance(entry, dict)
            ],
        )
        skeleton.updated_at = datetime.now(UTC)
        await _maybe_await(session.flush())


async def delete_figure_plan(
    session: SessionLike,
    plan_id: str,
) -> None:
    plan = await repository.get_figure_plan(session, plan_id)
    if plan is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Figure plan not found",
            status_code=404,
            details={"plan_id": plan_id},
        )

    await repository.delete_figure_plan(session, plan)
    await _maybe_await(session.commit())


async def transition_figure_plan_status(
    session: SessionLike,
    plan_id: str,
    payload: FigurePlanStatusTransitionRequest,
) -> FigurePlanDetail:
    plan = await repository.get_figure_plan(session, plan_id)
    if plan is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Figure plan not found",
            status_code=404,
            details={"plan_id": plan_id},
        )
    allowed = VALID_STATUS_TRANSITIONS.get(plan.status, set())
    if payload.status not in allowed:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message=f"Cannot transition from '{plan.status}' to '{payload.status}'",
            status_code=422,
            details={
                "plan_id": plan_id,
                "current_status": plan.status,
                "target_status": payload.status,
            },
        )
    plan = await repository.update_figure_plan_status(session, plan_id, payload.status)
    await _maybe_await(session.commit())
    return _build_figure_plan_detail(plan)


def _build_figure_plan_detail(plan: FigurePlan) -> FigurePlanDetail:
    return FigurePlanDetail(
        id=plan.id,
        system_id=plan.system_id,
        figure_no=plan.figure_no,
        title=plan.title,
        claim_text=plan.claim_text,
        data_needed_json=plan.data_needed_json,
        method_json=plan.method_json,
        acceptance_criteria_json=plan.acceptance_criteria_json,
        status=plan.status,
        version=plan.version,
        section_key=plan.section_key,
        skeleton_version=plan.skeleton_version,
        brief_text=plan.brief_text,
        brief_confirmed_at=plan.brief_confirmed_at,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def _build_image_analysis_asset_detail(asset: Asset) -> ImageAnalysisAssetDetail:
    return ImageAnalysisAssetDetail(
        id=asset.id,
        file_name=asset.file_name,
        mime_type=asset.mime_type,
        preview_url=_safe_presigned_url(asset.storage_key),
    )


def _build_analysis_run_summary(run: AnalysisRun) -> AnalysisRunSummary:
    return AnalysisRunSummary(
        id=run.id,
        status=run.status,
        summary=run.summary,
        confidence=_extract_analysis_confidence(run),
        updated_at=run.updated_at,
    )


def _extract_analysis_confidence(run: AnalysisRun) -> float | None:
    raw_value = (run.result_payload_json or {}).get("confidence")
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    if isinstance(raw_value, str):
        try:
            return float(raw_value)
        except ValueError:
            return None
    return None


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


def get_evidence_task_session_bind(session: SessionLike) -> tuple[object, bool]:
    if isinstance(session, AsyncSession):
        bind = session.bind
        if bind is None:
            raise RuntimeError("Async session is not bound")
        return bind, True

    if isinstance(session, Session):
        return session.get_bind(), False

    return session.sync_session.get_bind(), False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Claim & Evidence Matrix services (Task 9 – G4)
# ---------------------------------------------------------------------------


async def generate_evidence_matrix(
    session: SessionLike,
    system_id: str,
    broadcaster: TaskBroadcaster | None = None,
) -> EvidenceMatrixGenerateAcceptedResponse:
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
            workflow_key="evidence_matrix_generate",
            current_state=system.status,
            target_state=system.status,
            current_gate=GateKey.G4.value,
            status=TaskStatus.QUEUED,
            context={},
            message="Evidence matrix generation started",
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
            message="Evidence matrix generation started",
        )

    return EvidenceMatrixGenerateAcceptedResponse(handle=started.handle)


async def run_evidence_matrix_generation_task(
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
            await complete_evidence_matrix_generation(
                task_session,
                workflow_id=workflow_id,
                system_id=system_id,
                broadcaster=broadcaster,
            )
        return

    with Session(bind=bind, expire_on_commit=False) as task_session:
        await complete_evidence_matrix_generation(
            task_session,
            workflow_id=workflow_id,
            system_id=system_id,
            broadcaster=broadcaster,
        )


async def complete_evidence_matrix_generation(
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

        sections = await repository.list_system_sections(session, system.id)
        if not sections:
            raise AppException(
                code=ErrorCode.CONFLICT.value,
                message="Cannot generate evidence matrix without system sections",
                status_code=409,
                details={"system_id": system.id, "section_count": 0},
            )

        assets = await repository.list_assets_for_system(session, system.id)
        if not assets:
            raise AppException(
                code=ErrorCode.CONFLICT.value,
                message="Cannot generate evidence matrix without assets",
                status_code=409,
                details={"system_id": system.id, "asset_count": 0},
            )

        analysis_runs = await repository.list_analysis_runs_for_system(session, system.id)
        latest_run_by_asset_id = _index_latest_succeeded_runs(analysis_runs)

        generated_claims: list[Claim] = []
        generated_links: list[ClaimEvidenceLink] = []
        for index, section in enumerate(sections, start=1):
            asset = assets[(index - 1) % len(assets)]
            analysis_run = latest_run_by_asset_id.get(asset.id)
            claim_id = f"C{index}"
            version = await repository.get_next_claim_version(session, system.id, claim_id)
            claim = await repository.create_claim(
                session,
                system_id=system.id,
                claim_id=claim_id,
                statement=_build_generated_claim_statement(section, asset),
                section_ref=section.section_key,
                confidence_level="unreviewed",
                status="draft",
                version=version,
            )
            link = await repository.create_claim_evidence_link(
                session,
                claim_record_id=claim.id,
                asset_id=asset.id,
                analysis_run_id=None if analysis_run is None else analysis_run.id,
                statistical_support={"source": "generated"},
            )
            generated_claims.append(claim)
            generated_links.append(link)

        await append_system_workflow_event(
            task_service,
            WorkflowEventCommand(
                workflow_id=workflow_id,
                event_type=EventType.TASK_SUCCEEDED,
                message="Evidence matrix generation completed",
                status=TaskStatus.SUCCEEDED,
                from_state=system.status,
                to_state=system.status,
                current_state=system.status,
                current_gate=GateKey.G4.value,
                payload={
                    "claim_ids": [claim.id for claim in generated_claims],
                    "claim_count": len(generated_claims),
                    "link_count": len(generated_links),
                },
                context_update={
                    "claim_count": len(generated_claims),
                    "link_count": len(generated_links),
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
                message="Evidence matrix generation completed",
                payload={
                    "claimCount": len(generated_claims),
                    "linkCount": len(generated_links),
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
            message="Evidence matrix generation failed unexpectedly",
            payload={"code": ErrorCode.WORKFLOW_ERROR.value, "details": {}},
            broadcaster=broadcaster,
        )


async def list_claims(session: SessionLike, system_id: str) -> list[ClaimDetail]:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    claims = await repository.list_claims(session, system_id)
    return [_build_claim_detail(claim) for claim in claims]


async def approve_claim(
    session: SessionLike,
    claim_id: str,
    payload: ClaimApproveRequest | None = None,
) -> ClaimDetail:
    claim = await repository.get_claim(session, claim_id)
    if claim is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Claim not found",
            status_code=404,
            details={"claim_id": claim_id},
        )

    target_status = payload.status if payload is not None else "approved"
    if target_status == "approved":
        allowed_section_keys = set(
            (
                await _maybe_await(
                    session.scalars(
                        select(SystemSection.section_key).where(
                            SystemSection.system_id == claim.system_id
                        )
                    )
                )
            ).all()
        )
        if claim.section_ref not in allowed_section_keys:
            raise AppException(
                code=ErrorCode.VALIDATION_ERROR.value,
                message="Claim section_ref is not defined for this system",
                status_code=422,
                details={
                    "claim_id": claim.id,
                    "system_id": claim.system_id,
                    "section_ref": claim.section_ref,
                },
            )

    claim = await repository.update_claim_status(session, claim, target_status)
    await _maybe_await(session.commit())

    return _build_claim_detail(claim)


async def bind_claim_evidence(
    session: SessionLike,
    claim_id: str,
    payload: ClaimEvidenceLinkCreateRequest,
) -> ClaimEvidenceLinkDetail:
    claim = await repository.get_claim(session, claim_id)
    if claim is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Claim not found",
            status_code=404,
            details={"claim_id": claim_id},
        )

    asset = await repository.get_asset(session, payload.asset_id)
    if asset is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Asset not found",
            status_code=404,
            details={"asset_id": payload.asset_id},
        )
    if asset.system_id != claim.system_id:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Asset must belong to the same system as the claim",
            status_code=422,
            details={
                "claim_id": claim.id,
                "claim_system_id": claim.system_id,
                "asset_id": asset.id,
                "asset_system_id": asset.system_id,
            },
        )

    if payload.analysis_run_id is not None:
        analysis_run = await repository.get_analysis_run(session, payload.analysis_run_id)
        if analysis_run is None:
            raise AppException(
                code=ErrorCode.NOT_FOUND.value,
                message="Analysis run not found",
                status_code=404,
                details={"analysis_run_id": payload.analysis_run_id},
            )
        if analysis_run.system_id != claim.system_id:
            raise AppException(
                code=ErrorCode.VALIDATION_ERROR.value,
                message="Analysis run must belong to the same system as the claim",
                status_code=422,
                details={
                    "claim_id": claim.id,
                    "claim_system_id": claim.system_id,
                    "analysis_run_id": analysis_run.id,
                    "analysis_run_system_id": analysis_run.system_id,
                },
            )
        if analysis_run.asset_id != payload.asset_id:
            raise AppException(
                code=ErrorCode.VALIDATION_ERROR.value,
                message="Analysis run must reference the same asset as the claim evidence link",
                status_code=422,
                details={
                    "claim_id": claim.id,
                    "asset_id": payload.asset_id,
                    "analysis_run_id": analysis_run.id,
                    "analysis_run_asset_id": analysis_run.asset_id,
                },
            )

    try:
        link = await repository.create_claim_evidence_link(
            session,
            claim_record_id=claim.id,
            asset_id=payload.asset_id,
            analysis_run_id=payload.analysis_run_id,
            statistical_support=payload.statistical_support,
        )
        await _maybe_await(session.commit())
    except IntegrityError as exc:
        await _maybe_await(session.rollback())
        raise AppException(
            code=ErrorCode.CONFLICT.value,
            message="Claim evidence link already exists",
            status_code=409,
            details={
                "claim_id": claim.id,
                "asset_id": payload.asset_id,
                "analysis_run_id": payload.analysis_run_id,
            },
        ) from exc

    return _build_claim_evidence_link_detail(link)


def _build_claim_detail(claim: Claim) -> ClaimDetail:
    return ClaimDetail(
        id=claim.id,
        system_id=claim.system_id,
        claim_id=claim.claim_id,
        statement=claim.statement,
        section_ref=claim.section_ref,
        confidence_level=claim.confidence_level,
        status=claim.status,
        version=claim.version,
        approved_at=claim.approved_at,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
    )


def _build_claim_evidence_link_detail(link: ClaimEvidenceLink) -> ClaimEvidenceLinkDetail:
    return ClaimEvidenceLinkDetail(
        id=link.id,
        claim_record_id=link.claim_record_id,
        asset_id=link.asset_id,
        analysis_run_id=link.analysis_run_id,
        statistical_support=link.statistical_support,
        created_at=link.created_at,
    )


def _build_generated_claim_statement(section: SystemSection, asset: Asset) -> str:
    asset_label = asset.file_name
    if asset.metadata_entry is not None and asset.metadata_entry.semantic_description:
        asset_label = asset.metadata_entry.semantic_description
    return f"{section.title} evidence claim based on {asset_label}"


def _index_latest_succeeded_runs(analysis_runs: list[AnalysisRun]) -> dict[str, AnalysisRun]:
    indexed: dict[str, AnalysisRun] = {}
    for run in analysis_runs:
        if run.asset_id is None or run.status != TaskStatus.SUCCEEDED.value:
            continue
        current = indexed.get(run.asset_id)
        if current is None or _analysis_run_recency_key(run) > _analysis_run_recency_key(current):
            indexed[run.asset_id] = run
    return indexed


def _index_latest_succeeded_runs_by_figure_plan_id(
    analysis_runs: list[AnalysisRun],
) -> dict[str, AnalysisRun]:
    indexed: dict[str, AnalysisRun] = {}
    for run in analysis_runs:
        if run.figure_plan_id is None or run.status != TaskStatus.SUCCEEDED.value:
            continue
        current = indexed.get(run.figure_plan_id)
        if current is None or _analysis_run_recency_key(run) > _analysis_run_recency_key(current):
            indexed[run.figure_plan_id] = run
    return indexed


def _analysis_run_recency_key(run: AnalysisRun) -> tuple[datetime, datetime, str]:
    timestamp_floor = datetime.min.replace(tzinfo=UTC)
    return (
        run.updated_at or timestamp_floor,
        run.created_at or timestamp_floor,
        run.id,
    )


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


async def batch_approve_claims(
    session: SessionLike,
    system_id: str,
    claim_ids: list[str],
) -> BatchApproveClaimsResponse:
    # Pre-fetch valid section keys for this system once
    allowed_section_keys = set(
        (
            await _maybe_await(
                session.scalars(
                    select(SystemSection.section_key).where(SystemSection.system_id == system_id)
                )
            )
        ).all()
    )

    succeeded: list[str] = []
    failed: list[dict[str, str]] = []

    for claim_id in claim_ids:
        claim = await repository.get_claim(session, claim_id)
        if claim is None:
            failed.append({"claimId": claim_id, "error": "Claim not found"})
            continue
        if claim.system_id != system_id:
            failed.append({"claimId": claim_id, "error": "Claim does not belong to this system"})
            continue
        if claim.section_ref not in allowed_section_keys:
            failed.append(
                {"claimId": claim_id, "error": "Claim section_ref is not defined for this system"}
            )
            continue
        await repository.update_claim_status(session, claim, "approved")
        succeeded.append(claim_id)

    await _maybe_await(session.commit())
    return BatchApproveClaimsResponse(succeeded=succeeded, failed=failed)


# ---------------------------------------------------------------------------
# FigurePlanAsset services (G1 – image upload)
# ---------------------------------------------------------------------------


async def upload_figure_plan_asset(
    session: SessionLike,
    plan_id: str,
    *,
    file_obj: BinaryIO,
    file_name: str,
    content_type: str,
    role: str = "source_image",
) -> FigurePlanAssetDetail:
    if not content_type.startswith("image/"):
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Only image files are allowed",
            status_code=400,
            details={"content_type": content_type, "plan_id": plan_id},
        )

    file_obj.seek(0, SEEK_END)
    size = file_obj.tell()
    file_obj.seek(0)
    if size > 10 * 1024 * 1024:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="File size exceeds 10MB limit",
            status_code=400,
            details={"file_name": file_name, "size": size, "plan_id": plan_id},
        )

    plan = await repository.get_figure_plan(session, plan_id)
    if plan is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Figure plan not found",
            status_code=404,
            details={"plan_id": plan_id},
        )

    asset = await create_asset_from_upload(
        session,
        system_id=plan.system_id,
        file_obj=file_obj,
        file_name=file_name,
        content_type=content_type,
        asset_type="image",
    )

    existing_bindings = await repository.list_figure_plan_assets(session, plan_id)
    position = len(existing_bindings)

    binding = await repository.create_figure_plan_asset(
        session,
        figure_plan_id=plan_id,
        asset_id=asset.id,
        role=role,
        position=position,
    )
    await _maybe_await(session.commit())

    preview_url = _safe_presigned_url(asset.storage_key)
    return _build_figure_plan_asset_detail(binding, asset, preview_url)


async def list_figure_plan_assets(
    session: SessionLike,
    plan_id: str,
) -> list[FigurePlanAssetDetail]:
    plan = await repository.get_figure_plan(session, plan_id)
    if plan is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Figure plan not found",
            status_code=404,
            details={"plan_id": plan_id},
        )

    rows = await repository.list_figure_plan_assets_with_details(session, plan_id)
    results: list[FigurePlanAssetDetail] = []
    for binding, asset in rows:
        preview_url = _safe_presigned_url(asset.storage_key)
        results.append(_build_figure_plan_asset_detail(binding, asset, preview_url))
    return results


async def delete_figure_plan_asset_binding(
    session: SessionLike,
    plan_id: str,
    binding_id: str,
) -> None:
    binding = await repository.get_figure_plan_asset(session, binding_id)
    if binding is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Figure plan asset binding not found",
            status_code=404,
            details={"binding_id": binding_id},
        )
    # Verify binding belongs to this plan (security check)
    if binding.figure_plan_id != plan_id:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Binding does not belong to this plan",
            status_code=403,
            details={"binding_id": binding_id, "plan_id": plan_id},
        )
    await repository.delete_figure_plan_asset(session, binding)
    await _maybe_await(session.commit())


def _safe_presigned_url(storage_key: str) -> str | None:
    try:
        return generate_presigned_url(storage_key)
    except Exception:
        logger.warning("Failed to generate presigned URL for %s", storage_key, exc_info=True)
        return None


def _build_figure_plan_asset_detail(
    binding: FigurePlanAsset,
    asset: Asset,
    preview_url: str | None,
) -> FigurePlanAssetDetail:
    return FigurePlanAssetDetail(
        id=binding.id,
        figure_plan_id=binding.figure_plan_id,
        asset_id=binding.asset_id,
        role=binding.role,
        position=binding.position,
        file_name=asset.file_name,
        mime_type=asset.mime_type,
        preview_url=preview_url,
        created_at=binding.created_at,
    )


# ---------------------------------------------------------------------------
# FigurePlanChat services (G1 – agent chat)
# ---------------------------------------------------------------------------


async def list_chat_messages_for_plan(
    session: SessionLike,
    plan_id: str,
    provider: str,
) -> list[ChatMessageDetail]:
    plan = await repository.get_figure_plan(session, plan_id)
    if plan is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Figure plan not found",
            status_code=404,
            details={"plan_id": plan_id},
        )

    chat_session = await repository.get_active_chat_session(session, plan_id, provider)
    if chat_session is None:
        return []

    messages = await repository.list_chat_messages(session, chat_session.id)
    return [_build_chat_message_detail(m) for m in messages]


async def send_chat_message_stream(
    session: SessionLike,
    plan_id: str,
    provider_name: str,
    content: str,
) -> AsyncGenerator[str, None]:
    plan = await repository.get_figure_plan(session, plan_id)
    if plan is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Figure plan not found",
            status_code=404,
            details={"plan_id": plan_id},
        )

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
    chat_session = await _get_or_create_chat_session(session, plan_id, provider_value)

    if await repository.is_chat_session_busy(session, chat_session.id):
        raise _build_chat_conflict(plan_id, provider_value)

    try:
        turn_index = await repository.get_next_turn_index(session, chat_session.id)
        await repository.create_chat_message(
            session,
            session_id=chat_session.id,
            role="user",
            content=content,
            status="completed",
            turn_index=turn_index,
        )
        assistant_msg = await repository.create_chat_message(
            session,
            session_id=chat_session.id,
            role="assistant",
            content="",
            status="streaming",
            turn_index=turn_index + 1,
        )
        chat_session.last_message_at = datetime.now(UTC)
        await _maybe_await(session.commit())
    except IntegrityError as exc:
        await _maybe_await(session.rollback())
        raise _build_chat_conflict(plan_id, provider_value) from exc

    context = await _build_context_prompt(session, plan_id)

    async def _stream() -> AsyncGenerator[str, None]:
        collected_text: list[str] = []
        extracted_session_id: str | None = None

        def _persist_session_id() -> None:
            """Write provider_session_id to the chat session if changed."""
            nonlocal extracted_session_id
            if extracted_session_id and extracted_session_id != chat_session.provider_session_id:
                chat_session.provider_session_id = extracted_session_id

        try:
            async for chunk in invoke_chat_stream(
                provider,
                content,
                session_id=chat_session.provider_session_id,
                context=context,
            ):
                if chunk.strip().startswith("__SESSION_ID__:"):
                    extracted_session_id = chunk.strip().split(":", 1)[1].strip()
                    _persist_session_id()
                    await _maybe_await(session.commit())
                    continue
                collected_text.append(chunk)
                yield f"data: {_json_event('delta', chunk)}\n\n"

            assistant_msg.content = "".join(collected_text)
            assistant_msg.status = "completed"
            _persist_session_id()
            chat_session.last_message_at = datetime.now(UTC)
            await _maybe_await(session.commit())
            yield f"data: {_json_event('done', '')}\n\n"
        except AppException as exc:
            user_message = _translate_provider_error(exc, provider)
            logger.warning("Chat provider error: %s (code=%s)", exc.message, exc.code)
            assistant_msg.content = "".join(collected_text)
            assistant_msg.status = "failed"
            assistant_msg.error_text = user_message
            _persist_session_id()
            await _maybe_await(session.commit())
            yield f"data: {_json_event('error', user_message)}\n\n"
        except Exception as exc:
            logger.exception("Chat stream error: %s", exc)
            assistant_msg.content = "".join(collected_text)
            assistant_msg.status = "failed"
            assistant_msg.error_text = str(exc)
            _persist_session_id()
            await _maybe_await(session.commit())
            yield f"data: {_json_event('error', str(exc))}\n\n"

    return _stream()


def _translate_provider_error(exc: AppException, provider: ChatCliProvider) -> str:
    """Translate technical errors to user-friendly messages."""
    if "CLI tool not found" in exc.message:
        return f"{provider.value} AI 助手未正确安装，请联系管理员"
    elif "timeout" in exc.message.lower():
        return "AI 助手响应超时，请稍后重试"
    elif "exited with code" in exc.message:
        return "AI 助手暂时遇到了一点小麻烦，请稍后重试"
    else:
        return "AI 服务暂时不可用，请稍后重试"


async def _get_or_create_chat_session(
    session: SessionLike,
    plan_id: str,
    provider: str,
) -> FigurePlanChatSession:
    chat_session = await repository.get_active_chat_session(session, plan_id, provider)
    if chat_session is not None:
        return chat_session

    try:
        chat_session = await repository.create_chat_session(
            session,
            figure_plan_id=plan_id,
            provider=provider,
        )
        await _maybe_await(session.commit())
        return chat_session
    except IntegrityError:
        await _maybe_await(session.rollback())
        chat_session = await repository.get_active_chat_session(session, plan_id, provider)
        if chat_session is None:
            raise
        return chat_session


def _build_chat_conflict(plan_id: str, provider: str) -> AppException:
    return AppException(
        code=ErrorCode.CONFLICT.value,
        message="Another message is being processed for this session. Please wait.",
        status_code=409,
        details={"plan_id": plan_id, "provider": provider},
    )


async def _build_context_prompt(session: SessionLike, plan_id: str) -> str:
    plan = await repository.get_figure_plan(session, plan_id)
    if plan is None:
        return ""

    section_title = "N/A"
    if plan.section_key:
        result = await _maybe_await(
            session.execute(
                select(SystemSection.title)
                .where(
                    SystemSection.system_id == plan.system_id,
                    SystemSection.section_key == plan.section_key,
                )
                .limit(1)
            )
        )
        section_title = result.scalar_one_or_none() or plan.section_key

    assets = await repository.list_figure_plan_assets_with_details(session, plan_id)
    context_parts = [
        "# FigurePlan Context",
        f"Title: {plan.title}",
        f"Claim: {plan.claim_text or 'N/A'}",
        f"Section: {section_title}",
        f"Brief: {plan.brief_text or 'N/A'}",
    ]

    if assets:
        context_parts.append("")
        context_parts.append("## Uploaded Images:")
        for binding, asset in assets:
            uploaded_at = binding.created_at.isoformat() if binding.created_at else "unknown"
            context_parts.append(
                f"- {asset.file_name} (uploaded at {uploaded_at})"
            )

    return "\n".join(context_parts)


def _json_event(event_type: str, content: str) -> str:
    import json

    return json.dumps({"type": event_type, "content": content}, ensure_ascii=False)


def _build_chat_message_detail(msg: FigurePlanChatMessage) -> ChatMessageDetail:
    return ChatMessageDetail(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,
        content=msg.content,
        status=msg.status,
        turn_index=msg.turn_index,
        error_text=msg.error_text,
        created_at=msg.created_at,
    )


__all__ = [
    "EVIDENCE_TASK_START_DELAY_SECONDS",
    "approve_claim",
    "batch_approve_claims",
    "bind_claim_evidence",
    "complete_evidence_matrix_generation",
    "complete_figure_plan_generation",
    "confirm_figure_plan",
    "delete_figure_plan",
    "delete_figure_plan_asset_binding",
    "generate_evidence_matrix",
    "generate_figure_plan",
    "get_evidence_task_session_bind",
    "list_chat_messages_for_plan",
    "list_claims",
    "list_figure_plan_assets",
    "list_image_analyses",
    "list_figure_plans",
    "patch_figure_plan",
    "run_evidence_matrix_generation_task",
    "run_figure_plan_generation_task",
    "send_chat_message_stream",
    "trigger_figure_plan_analysis",
    "transition_figure_plan_status",
    "update_figure_plan_brief",
    "upload_figure_plan_asset",
]
