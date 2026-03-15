from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.websocket import get_broadcaster
from app.common.schemas import ApiResponse, JobHandle
from app.modules.skeletons.schemas import (
    BuildPromptRequest,
    BuildPromptResponse,
    SkeletonConfirmResponse,
    SkeletonDetail,
    SkeletonGenerateRequest,
    SkeletonPatchRequest,
    SkeletonReviseRequest,
    SkeletonSummary,
)
from app.modules.skeletons.service import (
    SKELETON_TASK_START_DELAY_SECONDS,
    build_skeleton_prompt as build_skeleton_prompt_service,
    confirm_skeleton as confirm_skeleton_service,
    delete_skeleton as delete_skeleton_service,
    generate_skeleton as generate_skeleton_service,
    get_skeleton as get_skeleton_service,
    get_skeleton_task_session_bind,
    list_skeletons as list_skeletons_service,
    patch_skeleton as patch_skeleton_service,
    revise_skeleton as revise_skeleton_service,
    run_skeleton_generation_task,
    run_skeleton_revision_task,
)
from app.persistence import get_db_session

router = APIRouter(tags=["skeletons"])


@router.post(
    "/systems/{system_id}/skeletons/build-prompt",
    response_model=ApiResponse[BuildPromptResponse],
)
async def build_prompt(
    system_id: str,
    payload: BuildPromptRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BuildPromptResponse]:
    result = await build_skeleton_prompt_service(session, system_id, payload)
    return ApiResponse(data=result)


@router.post(
    "/systems/{system_id}/skeletons/generate",
    response_model=ApiResponse[JobHandle],
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_skeleton(
    system_id: str,
    payload: SkeletonGenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[JobHandle]:
    broadcaster = get_broadcaster(request)
    handle = await generate_skeleton_service(
        session, system_id, payload, broadcaster
    )
    bind, use_async_session = get_skeleton_task_session_bind(session)
    asyncio.create_task(
        run_skeleton_generation_task(
            bind=bind,
            use_async_session=use_async_session,
            workflow_id=handle.workflow_id or "",
            system_id=system_id,
            source_asset_ids=payload.source_asset_ids,
            user_intent=payload.user_intent,
            provider=payload.provider,
            custom_prompt=payload.custom_prompt,
            broadcaster=broadcaster,
            delay_seconds=SKELETON_TASK_START_DELAY_SECONDS,
        )
    )
    return ApiResponse(data=handle)


@router.get(
    "/systems/{system_id}/skeletons",
    response_model=ApiResponse[list[SkeletonSummary]],
)
async def list_skeletons(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[SkeletonSummary]]:
    items = await list_skeletons_service(session, system_id)
    return ApiResponse(data=items)


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


@router.delete(
    "/skeletons/{skeleton_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_skeleton(
    skeleton_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await delete_skeleton_service(session, skeleton_id)


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
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[JobHandle]:
    broadcaster = get_broadcaster(request)
    handle = await revise_skeleton_service(
        session, system_id, payload, broadcaster
    )
    bind, use_async_session = get_skeleton_task_session_bind(session)
    asyncio.create_task(
        run_skeleton_revision_task(
            bind=bind,
            use_async_session=use_async_session,
            workflow_id=handle.workflow_id or "",
            system_id=system_id,
            skeleton_id=payload.skeleton_id,
            feedback=payload.feedback,
            provider=payload.provider,
            broadcaster=broadcaster,
            delay_seconds=SKELETON_TASK_START_DELAY_SECONDS,
        )
    )
    return ApiResponse(data=handle)
