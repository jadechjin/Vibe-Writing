from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from inspect import isawaitable
from typing import Any, BinaryIO, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.common.enums import EventType, GateKey, SystemState, TaskStatus
from app.common.errors import ErrorCode
from app.common.events import TaskEvent
from app.common.storage import upload_fileobj
from app.core.exceptions import AppException
from app.modules.assets import repository

from app.modules.assets.schemas import (
    AnalysisRunCreateAcceptedResponse,
    AnalysisRunDetail,
    AssetBindRequest,
    AssetDetail,
    AssetListItem,
    AssetMetadataDetail,
    AssetQCConfirmResponse,
    AssetUploadRequest,
    BatchConfirmAssetQCRequest,
    BatchConfirmAssetQCResponse,
    ManifestConfirmResponse,
    ManifestCreateAcceptedResponse,
    ManifestCreateRequest,
    ManifestDetail,
)
from app.modules.gates.service import check_data_and_analysis_ready
from app.modules.tasks.service import TaskWorkflowService
from app.persistence.models import AnalysisRun, Asset, AssetManifest, AssetMetadata, ExperimentalSystem
from app.realtime.broadcaster import TaskBroadcaster
from app.workflows.system_workflow import (
    WorkflowCommand,
    WorkflowEventCommand,
    append_system_workflow_event,
    start_system_workflow,
)

SessionLike = AsyncSession | Session
T = TypeVar("T")

DOWNSTREAM_ASSET_CONFIRMATION_STATES = {
    SystemState.ASSETS_CONFIRMED.value,
    SystemState.EVIDENCE_MATRIX_READY.value,
    SystemState.OUTLINE_READY.value,
    SystemState.SECTION_DRAFTING.value,
    SystemState.CHAPTER_REVIEW.value,
    SystemState.CHAPTER_APPROVED.value,
}

MANIFEST_TASK_START_DELAY_SECONDS = 0.05


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


async def create_asset_from_upload(
    session: SessionLike,
    *,
    system_id: str,
    file_obj: BinaryIO,
    file_name: str,
    content_type: str,
    asset_type: str = "image",
    uploaded_by: str = "user",
) -> Asset:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    storage_key = upload_fileobj(file_obj, file_name, content_type)
    asset = await repository.create_asset(
        session,
        project_id=system.project_id,
        system_id=system.id,
        asset_type=asset_type,
        file_name=file_name,
        storage_key=storage_key,
        mime_type=content_type,
        uploaded_by=uploaded_by,
    )
    await repository.create_asset_metadata(session, asset_id=asset.id)
    return asset


async def upload_asset(session: SessionLike, payload: AssetUploadRequest) -> AssetDetail:
    system = await repository.get_system_with_project(session, payload.system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": payload.system_id},
        )

    asset = await repository.create_asset(
        session,
        project_id=system.project_id,
        system_id=system.id,
        asset_type=payload.asset_type,
        file_name=payload.file_name,
        storage_key=payload.storage_key,
        mime_type=payload.mime_type,
        uploaded_by=payload.uploaded_by,
    )
    await repository.create_asset_metadata(session, asset_id=asset.id)
    await _reset_system_state_after_upload(session, system)
    await _maybe_await(session.commit())

    stored = await repository.get_asset_by_id(session, asset.id)
    if stored is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Asset not found after creation",
            status_code=500,
            details={"asset_id": asset.id},
        )
    return _build_asset_detail(stored)


async def delete_asset(session: SessionLike, asset_id: str) -> None:
    asset = await repository.get_asset_by_id(session, asset_id)
    if asset is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Asset not found",
            status_code=404,
            details={"asset_id": asset_id},
        )
    await repository.delete_asset(session, asset)
    await _maybe_await(session.commit())


async def get_asset_detail(session: SessionLike, asset_id: str) -> AssetDetail:
    asset = await repository.get_asset_by_id(session, asset_id)
    if asset is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Asset not found",
            status_code=404,
            details={"asset_id": asset_id},
        )
    return _build_asset_detail(asset)


async def list_assets_for_system(session: SessionLike, system_id: str) -> list[AssetDetail]:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    assets = await repository.list_assets_for_system(session, system_id)
    return [_build_asset_detail(asset) for asset in assets]


async def bind_asset(session: SessionLike, asset_id: str, payload: AssetBindRequest) -> AssetDetail:
    asset = await repository.get_asset_by_id(session, asset_id)
    if asset is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Asset not found",
            status_code=404,
            details={"asset_id": asset_id},
        )

    if payload.analysis_run_id is not None:
        analysis_run = await repository.get_analysis_run_by_id(session, payload.analysis_run_id)
        if analysis_run is None:
            raise AppException(
                code=ErrorCode.NOT_FOUND.value,
                message="Analysis run not found",
                status_code=404,
                details={"analysis_run_id": payload.analysis_run_id},
            )
        if analysis_run.system_id != asset.system_id:
            raise AppException(
                code=ErrorCode.CONFLICT.value,
                message="Analysis run must belong to the same system as the asset",
                status_code=409,
                details={
                    "analysis_run_id": payload.analysis_run_id,
                    "analysis_run_system_id": analysis_run.system_id,
                    "asset_id": asset.id,
                    "asset_system_id": asset.system_id,
                },
            )
        if analysis_run.status != TaskStatus.SUCCEEDED.value:
            raise AppException(
                code=ErrorCode.CONFLICT.value,
                message="Analysis run must be succeeded before binding to an asset",
                status_code=409,
                details={
                    "analysis_run_id": payload.analysis_run_id,
                    "analysis_run_status": analysis_run.status,
                    "required_status": TaskStatus.SUCCEEDED.value,
                },
            )

    metadata = asset.metadata_entry
    if metadata is None:
        metadata = await repository.create_asset_metadata(session, asset_id=asset.id)

    update_fields = payload.model_dump(exclude_none=True, exclude={"analysis_run_id"})
    if update_fields:
        await repository.update_asset_metadata(session, metadata, **update_fields)

    system = await repository.get_system_with_project(session, asset.system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": asset.system_id},
        )
    await _reset_system_state_after_bind(session, system, mutated=bool(update_fields))
    await _maybe_await(session.commit())

    stored = await repository.get_asset_by_id(session, asset.id)
    if stored is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Asset not found after bind",
            status_code=500,
            details={"asset_id": asset.id},
        )
    return _build_asset_detail(stored)


async def get_latest_manifest(session: SessionLike, system_id: str) -> ManifestDetail | None:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    manifest = await repository.get_latest_manifest(session, system_id)
    if manifest is None:
        return None
    return _build_manifest_detail(manifest)


async def create_manifest(
    session: SessionLike,
    system_id: str,
    payload: ManifestCreateRequest,
    broadcaster: TaskBroadcaster | None = None,
) -> ManifestCreateAcceptedResponse:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    assets = await repository.list_assets_for_system(session, system.id)
    if not assets:
        raise AppException(
            code=ErrorCode.CONFLICT.value,
            message="Cannot create manifest without assets",
            status_code=409,
            details={"system_id": system.id, "asset_count": 0},
        )

    gate_blockers = check_data_and_analysis_ready(_get_sync_session(session), system)
    if gate_blockers:
        raise AppException(
            code=ErrorCode.CONFLICT.value,
            message="System is not ready for manifest generation",
            status_code=409,
            details={
                "system_id": system.id,
                "gate": GateKey.G2.value,
                "blockers": [blocker.model_dump(mode="json") for blocker in gate_blockers],
            },
        )

    task_service = TaskWorkflowService(_get_task_session(session))  # type: ignore[arg-type]
    started = await start_system_workflow(
        task_service,
        WorkflowCommand(
            project_id=system.project_id,
            system_id=system.id,
            workflow_key="manifest_generate",
            current_state=system.status,
            target_state=system.status,
            current_gate=GateKey.G3.value,
            status=TaskStatus.QUEUED,
            context={"requested_manifest_status": payload.status},
            message="Manifest generation started",
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
            message="Manifest generation started",
        )

    return ManifestCreateAcceptedResponse(handle=started.handle)


async def run_manifest_generation_task(
    *,
    bind: object,
    use_async_session: bool,
    workflow_id: str,
    system_id: str,
    manifest_status: str,
    broadcaster: TaskBroadcaster | None = None,
    delay_seconds: float = 0.0,
) -> None:
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)

    if use_async_session:
        session_factory = AsyncSession(bind=bind, expire_on_commit=False)
        async with session_factory as task_session:
            await complete_manifest_generation(
                task_session,
                workflow_id=workflow_id,
                system_id=system_id,
                manifest_status=manifest_status,
                broadcaster=broadcaster,
            )
        return

    with Session(bind=bind, expire_on_commit=False) as task_session:
        await complete_manifest_generation(
            task_session,
            workflow_id=workflow_id,
            system_id=system_id,
            manifest_status=manifest_status,
            broadcaster=broadcaster,
        )


def get_manifest_task_session_bind(session: SessionLike) -> tuple[object, bool]:
    if isinstance(session, AsyncSession):
        bind = session.bind
        if bind is None:
            raise RuntimeError("Async session is not bound")
        return bind, True

    if isinstance(session, Session):
        return session.get_bind(), False

    return session.sync_session.get_bind(), False  # type: ignore[attr-defined]


async def complete_manifest_generation(
    session: SessionLike,
    *,
    workflow_id: str,
    system_id: str,
    manifest_status: str,
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

        assets = await repository.list_assets_for_system(session, system.id)
        if not assets:
            raise AppException(
                code=ErrorCode.CONFLICT.value,
                message="Cannot create manifest without assets",
                status_code=409,
                details={"system_id": system.id, "asset_count": 0},
            )

        version = await repository.get_next_manifest_version(session, system.id)
        manifest = await repository.create_manifest(
            session,
            project_id=system.project_id,
            system_id=system.id,
            version=version,
            status=manifest_status,
            manifest_json=_build_manifest_json(system, assets, version),
        )

        await append_system_workflow_event(
            task_service,
            WorkflowEventCommand(
                workflow_id=workflow_id,
                event_type=EventType.TASK_SUCCEEDED,
                message="Manifest generation completed",
                status=TaskStatus.SUCCEEDED,
                from_state=system.status,
                to_state=system.status,
                current_state=system.status,
                current_gate=GateKey.G3.value,
                payload={
                    "manifest_id": manifest.id,
                    "manifest_version": manifest.version,
                    "manifest_status": manifest.status,
                },
                context_update={
                    "manifest_id": manifest.id,
                    "manifest_version": manifest.version,
                    "manifest_status": manifest.status,
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
                message="Manifest generation completed",
                payload={
                    "manifestId": manifest.id,
                    "manifestVersion": manifest.version,
                    "manifestStatus": manifest.status,
                },
            )
    except AppException as exc:
        await _record_manifest_generation_failure(
            session=session,
            task_service=task_service,
            workflow_id=workflow_id,
            workflow_snapshot=workflow_snapshot,
            message=exc.message,
            payload={"code": exc.code, "details": exc.details},
            broadcaster=broadcaster,
        )
    except Exception as exc:
        await _record_manifest_generation_failure(
            session=session,
            task_service=task_service,
            workflow_id=workflow_id,
            workflow_snapshot=workflow_snapshot,
            message="Manifest generation failed unexpectedly",
            payload={"code": ErrorCode.WORKFLOW_ERROR.value, "details": {}},
            broadcaster=broadcaster,
        )


async def _record_manifest_generation_failure(
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


async def _reset_system_state_after_upload(session: SessionLike, system: ExperimentalSystem) -> None:
    next_status: str | None = None
    if system.status in {
        SystemState.FIGURE_PLAN_READY.value,
        SystemState.DATA_PENDING.value,
        SystemState.DATA_UPLOADED.value,
        SystemState.ANALYSIS_READY.value,
    }:
        next_status = SystemState.DATA_UPLOADED.value
    elif system.status in DOWNSTREAM_ASSET_CONFIRMATION_STATES:
        next_status = SystemState.ANALYSIS_READY.value

    if next_status is not None and system.status != next_status:
        system.status = next_status
        await _maybe_await(session.flush())


async def _reset_system_state_after_bind(
    session: SessionLike,
    system: ExperimentalSystem,
    *,
    mutated: bool,
) -> None:
    if not mutated:
        return

    if system.status in DOWNSTREAM_ASSET_CONFIRMATION_STATES:
        system.status = SystemState.ANALYSIS_READY.value
        await _maybe_await(session.flush())


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


def _build_asset_metadata_detail(metadata: AssetMetadata) -> AssetMetadataDetail:
    return AssetMetadataDetail(
        id=metadata.id,
        asset_id=metadata.asset_id,
        semantic_description=metadata.semantic_description,
        source_description=metadata.source_description,
        instrument_info=metadata.instrument_info,
        sample_ids=metadata.sample_ids,
        conditions_json=metadata.conditions_json,
        qc_status=metadata.qc_status,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
    )



def _build_asset_list_item(asset: Asset) -> AssetListItem:
    return AssetListItem(
        id=asset.id,
        project_id=asset.project_id,
        system_id=asset.system_id,
        asset_type=asset.asset_type,
        file_name=asset.file_name,
        storage_key=asset.storage_key,
        mime_type=asset.mime_type,
        version=asset.version,
        uploaded_by=asset.uploaded_by,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )



def _build_asset_detail(asset: Asset) -> AssetDetail:
    metadata = asset.metadata_entry
    return AssetDetail(
        **_build_asset_list_item(asset).model_dump(),
        metadata_entry=None if metadata is None else _build_asset_metadata_detail(metadata),
    )



def _build_manifest_detail(manifest: AssetManifest) -> ManifestDetail:
    return ManifestDetail(
        id=manifest.id,
        project_id=manifest.project_id,
        system_id=manifest.system_id,
        version=manifest.version,
        status=manifest.status,
        manifest_json=manifest.manifest_json,
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
    )



def _build_manifest_json(
    system: ExperimentalSystem,
    assets: list[Asset],
    version: int,
) -> dict[str, object]:
    return {
        "projectId": system.project_id,
        "systemId": system.id,
        "version": version,
        "generatedAt": datetime.now(UTC).isoformat(),
        "assetCount": len(assets),
        "assets": [
            _build_asset_detail(asset).model_dump(by_alias=True, mode="json")
            for asset in assets
        ],
    }



def _get_sync_session(session: SessionLike) -> Session:
    if isinstance(session, AsyncSession):
        return session.sync_session
    if isinstance(session, Session):
        return session
    return getattr(session, "sync_session", session)  # type: ignore[return-value]


def _get_task_session(session: SessionLike) -> AsyncSession | _SyncTaskSessionAdapter:
    if isinstance(session, AsyncSession):
        return session
    if isinstance(session, Session):
        return _SyncTaskSessionAdapter(session)
    return _SyncTaskSessionAdapter(session.sync_session)  # type: ignore[arg-type]


async def create_analysis_run(
    session: SessionLike,
    system_id: str,
    config: dict[str, Any] | None = None,
    run_type: str = "default",
    broadcaster: TaskBroadcaster | None = None,
) -> AnalysisRunCreateAcceptedResponse:
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
            workflow_key="analysis_run",
            current_state=system.status,
            target_state=system.status,
            current_gate=GateKey.G2.value,
            status=TaskStatus.QUEUED,
            context={"config": config or {}, "run_type": run_type},
            message="Analysis run started",
            event_type=EventType.TASK_CREATED,
        ),
    )

    await repository.create_analysis_run(
        session,
        system_id=system.id,
        run_type=run_type,
        input_payload_json=config,
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
            message="Analysis run started",
        )

    return AnalysisRunCreateAcceptedResponse(handle=started.handle)


async def list_analysis_runs(
    session: SessionLike,
    system_id: str,
) -> list[AnalysisRunDetail]:
    system = await repository.get_system_with_project(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    runs = await repository.list_analysis_runs_for_system(session, system_id)
    return [_build_analysis_run_detail(run) for run in runs]


async def complete_analysis_run(
    session: SessionLike,
    run_id: str,
    status: str,
    result_summary: str | None = None,
) -> AnalysisRunDetail:
    analysis_run = await repository.get_analysis_run_by_id(session, run_id)
    if analysis_run is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Analysis run not found",
            status_code=404,
            details={"run_id": run_id},
        )

    if analysis_run.status not in {TaskStatus.QUEUED.value, TaskStatus.RUNNING.value}:
        raise AppException(
            code=ErrorCode.CONFLICT.value,
            message="Analysis run is already completed",
            status_code=409,
            details={"run_id": run_id, "current_status": analysis_run.status},
        )

    updated = await repository.update_analysis_run_status(
        session,
        analysis_run,
        status=status,
        result_summary=result_summary,
    )
    await _maybe_await(session.commit())
    return _build_analysis_run_detail(updated)


def _build_analysis_run_detail(run: AnalysisRun) -> AnalysisRunDetail:
    return AnalysisRunDetail(
        id=run.id,
        system_id=run.system_id,
        asset_id=run.asset_id,
        run_type=run.run_type,
        status=run.status,
        input_payload_json=run.input_payload_json,
        result_payload_json=run.result_payload_json,
        summary=run.summary,
        version=run.version,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


async def confirm_manifest(session: SessionLike, manifest_id: str) -> ManifestConfirmResponse:
    statement = select(AssetManifest).where(AssetManifest.id == manifest_id)
    result = await _maybe_await(session.execute(statement))
    manifest = result.scalar_one_or_none()
    if manifest is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Manifest not found",
            status_code=404,
            details={"manifest_id": manifest_id},
        )

    manifest.status = "confirmed"
    await _maybe_await(session.flush())
    await _maybe_await(session.commit())

    return ManifestConfirmResponse(
        id=manifest.id,
        system_id=manifest.system_id,
        status=manifest.status,
        confirmed_at=manifest.updated_at,
    )


async def confirm_asset_qc(session: SessionLike, asset_id: str) -> AssetQCConfirmResponse:
    statement = select(AssetMetadata).where(AssetMetadata.asset_id == asset_id)
    result = await _maybe_await(session.execute(statement))
    metadata = result.scalar_one_or_none()
    if metadata is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Asset metadata not found",
            status_code=404,
            details={"asset_id": asset_id},
        )

    metadata.qc_status = "confirmed"
    await _maybe_await(session.flush())
    await _maybe_await(session.commit())

    return AssetQCConfirmResponse(
        id=metadata.id,
        asset_id=metadata.asset_id,
        qc_status=metadata.qc_status,
        confirmed_at=metadata.updated_at,
    )


async def batch_confirm_asset_qc(
    session: SessionLike,
    system_id: str,
    asset_ids: list[str],
) -> BatchConfirmAssetQCResponse:
    succeeded: list[str] = []
    failed: list[dict[str, str]] = []

    for asset_id in asset_ids:
        statement = select(AssetMetadata).where(AssetMetadata.asset_id == asset_id)
        result = await _maybe_await(session.execute(statement))
        metadata = result.scalar_one_or_none()
        if metadata is None:
            failed.append({"assetId": asset_id, "error": "Asset metadata not found"})
            continue
        # Verify asset belongs to the given system
        asset_stmt = select(Asset).where(Asset.id == asset_id)
        asset_result = await _maybe_await(session.execute(asset_stmt))
        asset = asset_result.scalar_one_or_none()
        if asset is None or asset.system_id != system_id:
            failed.append({"assetId": asset_id, "error": "Asset does not belong to this system"})
            continue
        metadata.qc_status = "confirmed"
        await _maybe_await(session.flush())
        succeeded.append(asset_id)

    await _maybe_await(session.commit())
    return BatchConfirmAssetQCResponse(succeeded=succeeded, failed=failed)


__all__ = [
    "MANIFEST_TASK_START_DELAY_SECONDS",
    "batch_confirm_asset_qc",
    "bind_asset",
    "complete_analysis_run",
    "complete_manifest_generation",
    "confirm_asset_qc",
    "confirm_manifest",
    "create_asset_from_upload",
    "create_analysis_run",
    "create_manifest",
    "delete_asset",
    "get_asset_detail",
    "get_latest_manifest",
    "list_analysis_runs",
    "list_assets_for_system",
    "upload_asset",
]
