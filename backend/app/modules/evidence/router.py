# ruff: noqa: B008

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.websocket import get_broadcaster
from app.common.schemas import ApiResponse
from app.modules.assets.schemas import (
    AnalysisRunSummary,
    FigurePlanAnalyzeRequest,
    ImageAnalysisListResponse,
)
from app.modules.evidence.schemas import (
    BatchApproveClaimsRequest,
    BatchApproveClaimsResponse,
    ChatImageUploadResponse,
    ChatMessageCreateRequest,
    ChatMessageDetail,
    ChatProvider,
    ClaimApproveRequest,
    ClaimDetail,
    ClaimEvidenceLinkCreateRequest,
    ClaimEvidenceLinkDetail,
    EvidenceMatrixGenerateAcceptedResponse,
    FigurePlanAssetDetail,
    FigurePlanConfirmRequest,
    FigurePlanDetail,
    FigurePlanGenerateAcceptedResponse,
    FigurePlanGenerateRequest,
    FigurePlanPatchRequest,
    FigurePlanStatusTransitionRequest,
    FigurePlanUpdateBriefRequest,
)
from app.modules.evidence.service import (
    EVIDENCE_TASK_START_DELAY_SECONDS,
    get_evidence_task_session_bind,
    run_evidence_matrix_generation_task,
    run_figure_plan_generation_task,
)
from app.modules.evidence.service import (
    approve_claim as approve_claim_service,
)
from app.modules.evidence.service import (
    batch_approve_claims as batch_approve_claims_service,
)
from app.modules.evidence.service import (
    bind_claim_evidence as bind_claim_evidence_service,
)
from app.modules.evidence.service import (
    confirm_figure_plan as confirm_figure_plan_service,
)
from app.modules.evidence.service import (
    delete_figure_plan as delete_figure_plan_service,
)
from app.modules.evidence.service import (
    delete_figure_plan_asset_binding as delete_figure_plan_asset_binding_service,
)
from app.modules.evidence.service import (
    generate_evidence_matrix as generate_evidence_matrix_service,
)
from app.modules.evidence.service import (
    generate_figure_plan as generate_figure_plan_service,
)
from app.modules.evidence.service import (
    list_chat_messages_for_plan as list_chat_messages_for_plan_service,
)
from app.modules.evidence.service import (
    list_claims as list_claims_service,
)
from app.modules.evidence.service import (
    list_figure_plan_assets as list_figure_plan_assets_service,
)
from app.modules.evidence.service import (
    list_figure_plans as list_figure_plans_service,
)
from app.modules.evidence.service import (
    list_image_analyses as list_image_analyses_service,
)
from app.modules.evidence.service import (
    patch_figure_plan as patch_figure_plan_service,
)
from app.modules.evidence.service import (
    send_chat_message_stream as send_chat_message_stream_service,
)
from app.modules.evidence.service import (
    transition_figure_plan_status as transition_figure_plan_status_service,
)
from app.modules.evidence.service import (
    trigger_figure_plan_analysis as trigger_figure_plan_analysis_service,
)
from app.modules.evidence.service import (
    update_figure_plan_brief as update_figure_plan_brief_service,
)
from app.modules.evidence.service import (
    upload_chat_image as upload_chat_image_service,
)
from app.modules.evidence.service import (
    upload_figure_plan_asset as upload_figure_plan_asset_service,
)
from app.persistence import get_db_session

router = APIRouter(tags=["evidence"])


@router.post(
    "/systems/{system_id}/figure-plans/generate",
    response_model=ApiResponse[FigurePlanGenerateAcceptedResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_figure_plan(
    system_id: str,
    _payload: FigurePlanGenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[FigurePlanGenerateAcceptedResponse]:
    broadcaster = get_broadcaster(request)
    result = await generate_figure_plan_service(session, system_id, broadcaster)
    bind, use_async_session = get_evidence_task_session_bind(session)
    asyncio.create_task(
        run_figure_plan_generation_task(
            bind=bind,
            use_async_session=use_async_session,
            workflow_id=result.handle.workflow_id or "",
            system_id=system_id,
            broadcaster=broadcaster,
            delay_seconds=EVIDENCE_TASK_START_DELAY_SECONDS,
        )
    )
    return ApiResponse(data=result)


@router.get(
    "/systems/{system_id}/figure-plans",
    response_model=ApiResponse[list[FigurePlanDetail]],
)
async def list_figure_plans(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[FigurePlanDetail]]:
    plans = await list_figure_plans_service(session, system_id)
    return ApiResponse(data=plans)


@router.get(
    "/systems/{system_id}/image-analyses",
    response_model=ApiResponse[ImageAnalysisListResponse],
)
async def list_image_analyses(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ImageAnalysisListResponse]:
    results = await list_image_analyses_service(session, system_id)
    return ApiResponse(data=results)


@router.post(
    "/figure-plans/{plan_id}/confirm",
    response_model=ApiResponse[FigurePlanDetail],
)
async def confirm_figure_plan(
    plan_id: str,
    payload: FigurePlanConfirmRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[FigurePlanDetail]:
    result = await confirm_figure_plan_service(session, plan_id, payload)
    return ApiResponse(data=result)


@router.patch(
    "/figure-plans/{plan_id}",
    response_model=ApiResponse[FigurePlanDetail],
)
async def patch_figure_plan(
    plan_id: str,
    payload: FigurePlanPatchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[FigurePlanDetail]:
    result = await patch_figure_plan_service(session, plan_id, payload)
    return ApiResponse(data=result)


@router.delete(
    "/figure-plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_figure_plan(
    plan_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await delete_figure_plan_service(session, plan_id)


@router.put(
    "/figure-plans/{plan_id}/brief",
    response_model=ApiResponse[FigurePlanDetail],
)
async def update_figure_plan_brief(
    plan_id: str,
    payload: FigurePlanUpdateBriefRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[FigurePlanDetail]:
    result = await update_figure_plan_brief_service(session, plan_id, payload)
    return ApiResponse(data=result)


@router.put(
    "/figure-plans/{plan_id}/status",
    response_model=ApiResponse[FigurePlanDetail],
)
async def transition_figure_plan_status(
    plan_id: str,
    payload: FigurePlanStatusTransitionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[FigurePlanDetail]:
    result = await transition_figure_plan_status_service(session, plan_id, payload)
    return ApiResponse(data=result)


# ---------------------------------------------------------------------------
# Claims & Evidence Matrix routes (Task 9 – G4)
# ---------------------------------------------------------------------------


@router.post(
    "/systems/{system_id}/evidence-matrix/generate",
    response_model=ApiResponse[EvidenceMatrixGenerateAcceptedResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_evidence_matrix(
    system_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[EvidenceMatrixGenerateAcceptedResponse]:
    broadcaster = get_broadcaster(request)
    result = await generate_evidence_matrix_service(session, system_id, broadcaster)
    bind, use_async_session = get_evidence_task_session_bind(session)
    asyncio.create_task(
        run_evidence_matrix_generation_task(
            bind=bind,
            use_async_session=use_async_session,
            workflow_id=result.handle.workflow_id or "",
            system_id=system_id,
            broadcaster=broadcaster,
            delay_seconds=EVIDENCE_TASK_START_DELAY_SECONDS,
        )
    )
    return ApiResponse(data=result)


@router.get(
    "/systems/{system_id}/claims",
    response_model=ApiResponse[list[ClaimDetail]],
)
async def list_claims(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[ClaimDetail]]:
    claims = await list_claims_service(session, system_id)
    return ApiResponse(data=claims)


@router.patch(
    "/claims/{claim_id}",
    response_model=ApiResponse[ClaimDetail],
)
async def approve_claim(
    claim_id: str,
    payload: ClaimApproveRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ClaimDetail]:
    result = await approve_claim_service(session, claim_id, payload)
    return ApiResponse(data=result)


@router.post(
    "/claims/{claim_id}/evidence-links",
    response_model=ApiResponse[ClaimEvidenceLinkDetail],
    status_code=status.HTTP_201_CREATED,
)
async def bind_claim_evidence(
    claim_id: str,
    payload: ClaimEvidenceLinkCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ClaimEvidenceLinkDetail]:
    result = await bind_claim_evidence_service(session, claim_id, payload)
    return ApiResponse(data=result)


@router.post(
    "/systems/{system_id}/claims/batch-approve",
    response_model=ApiResponse[BatchApproveClaimsResponse],
)
async def batch_approve_claims(
    system_id: str,
    payload: BatchApproveClaimsRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BatchApproveClaimsResponse]:
    result = await batch_approve_claims_service(session, system_id, payload.claim_ids)
    return ApiResponse(data=result)


# ---------------------------------------------------------------------------
# FigurePlanAsset routes (G1 – image upload)
# ---------------------------------------------------------------------------


@router.post(
    "/figure-plans/{plan_id}/assets",
    response_model=ApiResponse[FigurePlanAssetDetail],
    status_code=status.HTTP_201_CREATED,
)
async def upload_figure_plan_asset(
    plan_id: str,
    file: UploadFile = File(...),
    role: str = Form(default="source_image"),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[FigurePlanAssetDetail]:
    result = await upload_figure_plan_asset_service(
        session,
        plan_id,
        file_obj=file.file,
        file_name=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        role=role,
    )
    return ApiResponse(data=result)


@router.get(
    "/figure-plans/{plan_id}/assets",
    response_model=ApiResponse[list[FigurePlanAssetDetail]],
)
async def list_figure_plan_assets(
    plan_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[FigurePlanAssetDetail]]:
    results = await list_figure_plan_assets_service(session, plan_id)
    return ApiResponse(data=results)


@router.delete(
    "/figure-plans/{plan_id}/assets/{binding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_figure_plan_asset(
    plan_id: str,
    binding_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await delete_figure_plan_asset_binding_service(session, plan_id, binding_id)


@router.post(
    "/figure-plans/{plan_id}/analyze",
    response_model=ApiResponse[AnalysisRunSummary],
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_figure_plan_analysis(
    plan_id: str,
    payload: FigurePlanAnalyzeRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AnalysisRunSummary]:
    result = await trigger_figure_plan_analysis_service(session, plan_id, payload)
    return ApiResponse(data=result)


# ---------------------------------------------------------------------------
# FigurePlanChat routes (G1/G2 – agent chat)
# ---------------------------------------------------------------------------


@router.post(
    "/figure-plans/{plan_id}/chat/upload-image",
    response_model=ApiResponse[ChatImageUploadResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_chat_image(
    plan_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ChatImageUploadResponse]:
    result = await upload_chat_image_service(
        session,
        plan_id,
        file_obj=file.file,
        file_name=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
    )
    return ApiResponse(data=result)


@router.post("/figure-plans/{plan_id}/chat/messages")
async def send_chat_message(
    plan_id: str,
    payload: ChatMessageCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    stream = await send_chat_message_stream_service(
        session,
        plan_id,
        payload.provider.value,
        payload.content,
        payload.scope,
    )
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/figure-plans/{plan_id}/chat/messages",
    response_model=ApiResponse[list[ChatMessageDetail]],
)
async def list_chat_messages(
    plan_id: str,
    provider: ChatProvider = Query(...),
    scope: str = Query(default="planning", min_length=1, max_length=50),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[ChatMessageDetail]]:
    messages = await list_chat_messages_for_plan_service(
        session,
        plan_id,
        provider.value,
        scope,
    )
    return ApiResponse(data=messages)
