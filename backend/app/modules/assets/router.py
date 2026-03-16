from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.websocket import get_broadcaster
from app.common.schemas import ApiResponse
from app.common.storage import upload_fileobj
from app.modules.assets.schemas import (
    AnalysisRunCompleteRequest,
    AnalysisRunCreateAcceptedResponse,
    AnalysisRunCreateRequest,
    AnalysisRunDetail,
    AssetBindRequest,
    AssetDetail,
    AssetQCConfirmResponse,
    AssetUploadRequest,
    BatchConfirmAssetQCRequest,
    BatchConfirmAssetQCResponse,
    ManifestConfirmResponse,
    ManifestCreateAcceptedResponse,
    ManifestCreateRequest,
    ManifestDetail,
    ManifestPreviewResponse,
)
from app.modules.assets.service import (
    MANIFEST_TASK_START_DELAY_SECONDS,
    batch_confirm_asset_qc as batch_confirm_asset_qc_service,
    bind_asset as bind_asset_service,
    complete_analysis_run as complete_analysis_run_service,
    confirm_asset_qc as confirm_asset_qc_service,
    confirm_manifest as confirm_manifest_service,
    confirm_manifest_from_preview as confirm_manifest_from_preview_service,
    create_analysis_run as create_analysis_run_service,
    create_manifest as create_manifest_service,
    delete_asset as delete_asset_service,
    get_asset_detail as get_asset_detail_service,
    get_latest_manifest as get_latest_manifest_service,
    get_manifest_preview as get_manifest_preview_service,
    get_manifest_task_session_bind,
    list_analysis_runs as list_analysis_runs_service,
    list_assets_for_system as list_assets_for_system_service,
    run_manifest_generation_task,
    upload_asset as upload_asset_service,
)
from app.persistence import get_db_session

router = APIRouter(tags=["assets"])


@router.post(
    "/assets/upload-file",
    response_model=ApiResponse[AssetDetail],
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    file: UploadFile = File(...),
    system_id: str = Form(...),
    asset_type: str = Form(...),
    uploaded_by: str = Form(default="user"),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AssetDetail]:
    content_type = file.content_type or "application/octet-stream"
    storage_key = upload_fileobj(file.file, file.filename or "unknown", content_type)
    payload = AssetUploadRequest(
        system_id=system_id,
        asset_type=asset_type,
        file_name=file.filename or "unknown",
        storage_key=storage_key,
        mime_type=content_type,
        uploaded_by=uploaded_by,
    )
    asset = await upload_asset_service(session, payload)
    return ApiResponse(data=asset)


@router.post(
    "/assets/upload",
    response_model=ApiResponse[AssetDetail],
    status_code=status.HTTP_201_CREATED,
)
async def upload_asset(
    payload: AssetUploadRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AssetDetail]:
    asset = await upload_asset_service(session, payload)
    return ApiResponse(data=asset)


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await delete_asset_service(session, asset_id)


@router.get("/assets/{asset_id}", response_model=ApiResponse[AssetDetail])
async def get_asset_detail(
    asset_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AssetDetail]:
    asset = await get_asset_detail_service(session, asset_id)
    return ApiResponse(data=asset)


@router.get("/systems/{system_id}/assets", response_model=ApiResponse[list[AssetDetail]])
async def list_assets_for_system(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[AssetDetail]]:
    assets = await list_assets_for_system_service(session, system_id)
    return ApiResponse(data=assets)


@router.post("/assets/{asset_id}/bind", response_model=ApiResponse[AssetDetail])
async def bind_asset(
    asset_id: str,
    payload: AssetBindRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AssetDetail]:
    asset = await bind_asset_service(session, asset_id, payload)
    return ApiResponse(data=asset)


@router.get("/systems/{system_id}/manifest", response_model=ApiResponse[ManifestDetail | None])
async def get_latest_manifest(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ManifestDetail | None]:
    manifest = await get_latest_manifest_service(session, system_id)
    return ApiResponse(data=manifest)


@router.get(
    "/systems/{system_id}/manifest-preview",
    response_model=ApiResponse[ManifestPreviewResponse],
)
async def get_manifest_preview(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ManifestPreviewResponse]:
    preview = await get_manifest_preview_service(session, system_id)
    return ApiResponse(data=preview)


@router.post(
    "/systems/{system_id}/manifest",
    response_model=ApiResponse[ManifestCreateAcceptedResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_manifest(
    system_id: str,
    payload: ManifestCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ManifestCreateAcceptedResponse]:
    broadcaster = get_broadcaster(request)
    result = await create_manifest_service(session, system_id, payload, broadcaster)
    bind, use_async_session = get_manifest_task_session_bind(session)
    asyncio.create_task(
        run_manifest_generation_task(
            bind=bind,
            use_async_session=use_async_session,
            workflow_id=result.handle.workflow_id or "",
            system_id=system_id,
            manifest_status=payload.status,
            broadcaster=broadcaster,
            delay_seconds=MANIFEST_TASK_START_DELAY_SECONDS,
        )
    )
    return ApiResponse(data=result)


@router.post(
    "/systems/{system_id}/analysis-runs",
    response_model=ApiResponse[AnalysisRunCreateAcceptedResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_analysis_run(
    system_id: str,
    payload: AnalysisRunCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AnalysisRunCreateAcceptedResponse]:
    broadcaster = get_broadcaster(request)
    result = await create_analysis_run_service(
        session,
        system_id,
        config=payload.config,
        run_type=payload.run_type,
        broadcaster=broadcaster,
    )
    return ApiResponse(data=result)


@router.get(
    "/systems/{system_id}/analysis-runs",
    response_model=ApiResponse[list[AnalysisRunDetail]],
)
async def list_analysis_runs(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[AnalysisRunDetail]]:
    runs = await list_analysis_runs_service(session, system_id)
    return ApiResponse(data=runs)


@router.patch(
    "/analysis-runs/{run_id}/complete",
    response_model=ApiResponse[AnalysisRunDetail],
)
async def complete_analysis_run(
    run_id: str,
    payload: AnalysisRunCompleteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AnalysisRunDetail]:
    result = await complete_analysis_run_service(
        session,
        run_id,
        status=payload.status,
        result_summary=payload.result_summary,
    )
    return ApiResponse(data=result)


@router.post(
    "/manifests/{manifest_id}/confirm",
    response_model=ApiResponse[ManifestConfirmResponse],
)
async def confirm_manifest(
    manifest_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ManifestConfirmResponse]:
    result = await confirm_manifest_service(session, manifest_id)
    return ApiResponse(data=result)


@router.post(
    "/systems/{system_id}/manifest-confirm",
    response_model=ApiResponse[ManifestConfirmResponse],
)
async def confirm_manifest_from_preview(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ManifestConfirmResponse]:
    result = await confirm_manifest_from_preview_service(session, system_id)
    return ApiResponse(data=result)


@router.post(
    "/assets/{asset_id}/confirm-qc",
    response_model=ApiResponse[AssetQCConfirmResponse],
)
async def confirm_asset_qc(
    asset_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AssetQCConfirmResponse]:
    result = await confirm_asset_qc_service(session, asset_id)
    return ApiResponse(data=result)


@router.post(
    "/systems/{system_id}/assets/batch-confirm-qc",
    response_model=ApiResponse[BatchConfirmAssetQCResponse],
)
async def batch_confirm_asset_qc(
    system_id: str,
    payload: BatchConfirmAssetQCRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BatchConfirmAssetQCResponse]:
    result = await batch_confirm_asset_qc_service(session, system_id, payload.asset_ids)
    return ApiResponse(data=result)
