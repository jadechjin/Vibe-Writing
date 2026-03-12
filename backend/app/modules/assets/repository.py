from __future__ import annotations

from inspect import isawaitable
from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.persistence.models import AnalysisRun, Asset, AssetManifest, AssetMetadata, ExperimentalSystem

SessionLike = AsyncSession | Session
T = TypeVar("T")


async def _maybe_await(value: T) -> T:
    if isawaitable(value):
        return await value
    return value


async def get_system_with_project(session: SessionLike, system_id: str) -> ExperimentalSystem | None:
    statement = select(ExperimentalSystem).where(ExperimentalSystem.id == system_id)
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def create_asset(
    session: SessionLike,
    *,
    project_id: str,
    system_id: str,
    asset_type: str,
    file_name: str,
    storage_key: str,
    mime_type: str | None,
    uploaded_by: str,
) -> Asset:
    asset = Asset(
        project_id=project_id,
        system_id=system_id,
        asset_type=asset_type,
        file_name=file_name,
        storage_key=storage_key,
        mime_type=mime_type,
        uploaded_by=uploaded_by,
    )
    session.add(asset)
    await _maybe_await(session.flush())
    return asset


async def create_asset_metadata(
    session: SessionLike,
    *,
    asset_id: str,
    semantic_description: str | None = None,
    source_description: str | None = None,
    instrument_info: str | None = None,
    sample_ids: list[str] | None = None,
    conditions_json: dict[str, Any] | None = None,
    qc_status: str = "pending",
) -> AssetMetadata:
    metadata = AssetMetadata(
        asset_id=asset_id,
        semantic_description=semantic_description,
        source_description=source_description,
        instrument_info=instrument_info,
        sample_ids=sample_ids,
        conditions_json=conditions_json,
        qc_status=qc_status,
    )
    session.add(metadata)
    await _maybe_await(session.flush())
    return metadata


async def get_asset_by_id(session: SessionLike, asset_id: str) -> Asset | None:
    statement = (
        select(Asset)
        .options(selectinload(Asset.metadata_entry))
        .where(Asset.id == asset_id)
    )
    result = await _maybe_await(session.execute(statement))
    return result.scalars().unique().one_or_none()


async def list_assets_for_system(session: SessionLike, system_id: str) -> list[Asset]:
    statement = (
        select(Asset)
        .options(selectinload(Asset.metadata_entry))
        .where(Asset.system_id == system_id)
        .order_by(Asset.created_at.asc(), Asset.file_name.asc(), Asset.id.asc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().unique().all())


async def update_asset_metadata(
    session: SessionLike,
    metadata: AssetMetadata,
    **kwargs: Any,
) -> AssetMetadata:
    for field_name, value in kwargs.items():
        if value is not None:
            setattr(metadata, field_name, value)
    await _maybe_await(session.flush())
    return metadata


async def get_analysis_run_by_id(session: SessionLike, analysis_run_id: str) -> AnalysisRun | None:
    statement = select(AnalysisRun).where(AnalysisRun.id == analysis_run_id)
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def get_latest_manifest(session: SessionLike, system_id: str) -> AssetManifest | None:
    statement = (
        select(AssetManifest)
        .where(AssetManifest.system_id == system_id)
        .order_by(AssetManifest.version.desc(), AssetManifest.created_at.desc(), AssetManifest.id.desc())
        .limit(1)
    )
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def get_next_manifest_version(session: SessionLike, system_id: str) -> int:
    statement = select(func.coalesce(func.max(AssetManifest.version), 0)).where(
        AssetManifest.system_id == system_id
    )
    result = await _maybe_await(session.execute(statement))
    max_version = result.scalar_one()
    return max_version + 1


async def create_manifest(
    session: SessionLike,
    *,
    project_id: str,
    system_id: str,
    version: int,
    status: str,
    manifest_json: dict[str, Any],
) -> AssetManifest:
    manifest = AssetManifest(
        project_id=project_id,
        system_id=system_id,
        version=version,
        status=status,
        manifest_json=manifest_json,
    )
    session.add(manifest)
    await _maybe_await(session.flush())
    return manifest


async def create_analysis_run(
    session: SessionLike,
    *,
    system_id: str,
    run_type: str = "default",
    input_payload_json: dict[str, Any] | None = None,
) -> AnalysisRun:
    analysis_run = AnalysisRun(
        system_id=system_id,
        run_type=run_type,
        status="running",
        input_payload_json=input_payload_json or {},
    )
    session.add(analysis_run)
    await _maybe_await(session.flush())
    return analysis_run


async def list_analysis_runs_for_system(session: SessionLike, system_id: str) -> list[AnalysisRun]:
    statement = (
        select(AnalysisRun)
        .where(AnalysisRun.system_id == system_id)
        .order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def update_analysis_run_status(
    session: SessionLike,
    analysis_run: AnalysisRun,
    *,
    status: str,
    result_summary: str | None = None,
) -> AnalysisRun:
    analysis_run.status = status
    if result_summary is not None:
        analysis_run.summary = result_summary
    if status in {"succeeded", "failed"}:
        from datetime import UTC, datetime

        analysis_run.completed_at = datetime.now(UTC)
    await _maybe_await(session.flush())
    return analysis_run


async def delete_asset(session: SessionLike, asset: Asset) -> None:
    if asset.metadata_entry is not None:
        await _maybe_await(session.delete(asset.metadata_entry))
    await _maybe_await(session.delete(asset))
    await _maybe_await(session.flush())


__all__ = [
    "delete_asset",
    "create_analysis_run",
    "create_asset",
    "create_asset_metadata",
    "create_manifest",
    "get_analysis_run_by_id",
    "get_asset_by_id",
    "get_latest_manifest",
    "get_next_manifest_version",
    "get_system_with_project",
    "list_analysis_runs_for_system",
    "list_assets_for_system",
    "update_asset_metadata",
]
