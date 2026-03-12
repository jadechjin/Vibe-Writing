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
from app.modules.evidence import repository
from app.modules.evidence.schemas import (
    BatchApproveClaimsRequest,
    BatchApproveClaimsResponse,
    ClaimApproveRequest,
    ClaimDetail,
    ClaimEvidenceLinkCreateRequest,
    ClaimEvidenceLinkDetail,
    EvidenceMatrixGenerateAcceptedResponse,
    FigurePlanConfirmRequest,
    FigurePlanDetail,
    FigurePlanGenerateAcceptedResponse,
)
from app.modules.tasks.service import TaskWorkflowService
from app.persistence.models import AnalysisRun, Asset, Claim, ClaimEvidenceLink, FigurePlan, SystemSection
from app.realtime.broadcaster import TaskBroadcaster
from app.workflows.system_workflow import (
    WorkflowCommand,
    WorkflowEventCommand,
    append_system_workflow_event,
    start_system_workflow,
)

SessionLike = AsyncSession | Session
T = TypeVar("T")

EVIDENCE_TASK_START_DELAY_SECONDS = 0.05


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

        figure_no = "1"
        version = await repository.get_next_figure_plan_version(session, system.id, figure_no)
        plan = await repository.create_figure_plan(
            session,
            system_id=system.id,
            figure_no=figure_no,
            title=f"Figure {figure_no}",
            claim_text=f"Generated figure plan for {system.title}",
            status="draft",
            version=version,
            data_needed_json=[{"assetType": "figure"}],
            method_json={"mode": "thin_workflow"},
            acceptance_criteria_json=[{"type": "status", "value": "confirmed"}],
        )

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
                    "figure_plan_id": plan.id,
                    "figure_no": plan.figure_no,
                    "figure_plan_version": plan.version,
                    "figure_plan_status": plan.status,
                },
                context_update={
                    "figure_plan_id": plan.id,
                    "figure_plan_version": plan.version,
                    "figure_plan_status": plan.status,
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
                    "figurePlanId": plan.id,
                    "figureNo": plan.figure_no,
                    "figurePlanVersion": plan.version,
                    "figurePlanStatus": plan.status,
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
    except Exception as exc:
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
        created_at=plan.created_at,
        updated_at=plan.updated_at,
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
    except Exception as exc:
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
                        select(SystemSection.section_key).where(SystemSection.system_id == claim.system_id)
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
        indexed.setdefault(run.asset_id, run)
    return indexed


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
            failed.append({"claimId": claim_id, "error": "Claim section_ref is not defined for this system"})
            continue
        await repository.update_claim_status(session, claim, "approved")
        succeeded.append(claim_id)

    await _maybe_await(session.commit())
    return BatchApproveClaimsResponse(succeeded=succeeded, failed=failed)


__all__ = [
    "EVIDENCE_TASK_START_DELAY_SECONDS",
    "approve_claim",
    "batch_approve_claims",
    "bind_claim_evidence",
    "complete_evidence_matrix_generation",
    "complete_figure_plan_generation",
    "confirm_figure_plan",
    "generate_evidence_matrix",
    "generate_figure_plan",
    "get_evidence_task_session_bind",
    "list_claims",
    "list_figure_plans",
    "run_evidence_matrix_generation_task",
    "run_figure_plan_generation_task",
]
