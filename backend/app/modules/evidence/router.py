from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.websocket import get_broadcaster
from app.common.schemas import ApiResponse
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
    FigurePlanGenerateRequest,
)
from app.modules.evidence.service import (
    EVIDENCE_TASK_START_DELAY_SECONDS,
    approve_claim as approve_claim_service,
    batch_approve_claims as batch_approve_claims_service,
    bind_claim_evidence as bind_claim_evidence_service,
    complete_evidence_matrix_generation,
    complete_figure_plan_generation,
    confirm_figure_plan as confirm_figure_plan_service,
    generate_evidence_matrix as generate_evidence_matrix_service,
    generate_figure_plan as generate_figure_plan_service,
    get_evidence_task_session_bind,
    list_claims as list_claims_service,
    list_figure_plans as list_figure_plans_service,
    run_evidence_matrix_generation_task,
    run_figure_plan_generation_task,
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
