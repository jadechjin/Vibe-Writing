from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import ApiResponse, JobHandle
from app.modules.skeletons.schemas import (
    SkeletonConfirmResponse,
    SkeletonDetail,
    SkeletonGenerateRequest,
    SkeletonPatchRequest,
    SkeletonReviseRequest,
    SkeletonSummary,
)
from app.modules.skeletons.service import (
    confirm_skeleton as confirm_skeleton_service,
    generate_skeleton as generate_skeleton_service,
    get_skeleton as get_skeleton_service,
    list_skeletons as list_skeletons_service,
    patch_skeleton as patch_skeleton_service,
    revise_skeleton as revise_skeleton_service,
)
from app.persistence import get_db_session

router = APIRouter(tags=["skeletons"])


@router.post(
    "/systems/{system_id}/skeletons/generate",
    response_model=ApiResponse[JobHandle],
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_skeleton(
    system_id: str,
    payload: SkeletonGenerateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[JobHandle]:
    handle = await generate_skeleton_service(session, system_id, payload)
    return ApiResponse(data=handle)


@router.get(
    "/systems/{system_id}/skeletons",
    response_model=ApiResponse[list[SkeletonSummary]],
)
async def list_skeletons(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[SkeletonSummary]]:
    summaries = await list_skeletons_service(session, system_id)
    return ApiResponse(data=summaries)


@router.get(
    "/skeletons/{skeleton_id}",
    response_model=ApiResponse[SkeletonDetail],
)
async def get_skeleton(
    skeleton_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SkeletonDetail]:
    detail = await get_skeleton_service(session, skeleton_id)
    return ApiResponse(data=detail)


@router.patch(
    "/skeletons/{skeleton_id}",
    response_model=ApiResponse[SkeletonDetail],
)
async def patch_skeleton(
    skeleton_id: str,
    payload: SkeletonPatchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SkeletonDetail]:
    detail = await patch_skeleton_service(session, skeleton_id, payload)
    return ApiResponse(data=detail)


@router.post(
    "/skeletons/{skeleton_id}/confirm",
    response_model=ApiResponse[SkeletonConfirmResponse],
)
async def confirm_skeleton(
    skeleton_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SkeletonConfirmResponse]:
    result = await confirm_skeleton_service(session, skeleton_id)
    return ApiResponse(data=result)


@router.post(
    "/systems/{system_id}/skeletons/revise",
    response_model=ApiResponse[JobHandle],
    status_code=status.HTTP_202_ACCEPTED,
)
async def revise_skeleton(
    system_id: str,
    payload: SkeletonReviseRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[JobHandle]:
    handle = await revise_skeleton_service(session, system_id, payload)
    return ApiResponse(data=handle)
