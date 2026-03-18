from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.websocket import get_broadcaster
from app.common.schemas import ApiResponse
from app.modules.drafts.schemas import (
    DraftChatMessageDetail,
    DraftChatMessageRequest,
    DraftContextPack,
    DraftValidateRequest,
    DraftValidateResponse,
    OutlineBindingCreateRequest,
    OutlineBindingDetail,
    OutlineConfirmRequest,
    OutlineDetail,
    OutlineGenerateAcceptedResponse,
    OutlineGenerateRequest,
    ReviewCommentCreateRequest,
    ReviewCommentDetail,
    SectionDraftApproveRequest,
    SectionDraftDetail,
    SectionDraftGenerateAcceptedResponse,
    SectionDraftGenerateRequest,
)
from app.modules.drafts.service import (
    DRAFT_TASK_START_DELAY_SECONDS,
    add_review_comment as add_review_comment_service,
    approve_section_draft as approve_draft_service,
    assemble_draft_context as assemble_draft_context_service,
    bind_outline_assets as bind_outline_assets_service,
    confirm_outline as confirm_outline_service,
    generate_outline as generate_outline_service,
    generate_section_draft as generate_draft_service,
    get_draft_task_session_bind,
    list_draft_chat_messages as list_draft_chat_messages_service,
    list_outlines as list_outlines_service,
    list_section_drafts as list_drafts_service,
    run_outline_generation_task,
    run_section_draft_generation_task,
    send_draft_chat_message_stream as send_draft_chat_message_stream_service,
    validate_and_save_draft as validate_and_save_draft_service,
)
from app.persistence import get_db_session

router = APIRouter(tags=["drafts"])


@router.post(
    "/systems/{system_id}/outline/generate",
    response_model=ApiResponse[OutlineGenerateAcceptedResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_outline(
    system_id: str,
    _payload: OutlineGenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OutlineGenerateAcceptedResponse]:
    broadcaster = get_broadcaster(request)
    result = await generate_outline_service(session, system_id, broadcaster)
    bind, use_async_session = get_draft_task_session_bind(session)
    asyncio.create_task(
        run_outline_generation_task(
            bind=bind,
            use_async_session=use_async_session,
            workflow_id=result.handle.workflow_id or "",
            system_id=system_id,
            broadcaster=broadcaster,
            delay_seconds=DRAFT_TASK_START_DELAY_SECONDS,
        )
    )
    return ApiResponse(data=result)


@router.get(
    "/systems/{system_id}/outlines",
    response_model=ApiResponse[list[OutlineDetail]],
)
async def list_outlines(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[OutlineDetail]]:
    outlines = await list_outlines_service(session, system_id)
    return ApiResponse(data=outlines)


@router.post(
    "/outlines/{outline_id}/confirm",
    response_model=ApiResponse[OutlineDetail],
)
async def confirm_outline(
    outline_id: str,
    payload: OutlineConfirmRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OutlineDetail]:
    result = await confirm_outline_service(session, outline_id, payload)
    return ApiResponse(data=result)


@router.post(
    "/outlines/{outline_id}/bindings",
    response_model=ApiResponse[OutlineBindingDetail],
    status_code=status.HTTP_201_CREATED,
)
async def create_outline_binding(
    outline_id: str,
    payload: OutlineBindingCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OutlineBindingDetail]:
    result = await bind_outline_assets_service(session, outline_id, payload)
    return ApiResponse(data=result)


@router.post(
    "/systems/{system_id}/sections/{section_key}/draft",
    response_model=ApiResponse[SectionDraftGenerateAcceptedResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_section_draft(
    system_id: str,
    section_key: str,
    payload: SectionDraftGenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SectionDraftGenerateAcceptedResponse]:
    broadcaster = get_broadcaster(request)
    result = await generate_draft_service(
        session,
        system_id,
        section_key,
        outline_id=payload.outline_id,
        claim_ids=payload.claim_ids,
        broadcaster=broadcaster,
    )
    bind, use_async_session = get_draft_task_session_bind(session)
    asyncio.create_task(
        run_section_draft_generation_task(
            bind=bind,
            use_async_session=use_async_session,
            workflow_id=result.handle.workflow_id or "",
            system_id=system_id,
            section_key=section_key,
            outline_id=payload.outline_id,
            claim_ids=payload.claim_ids,
            broadcaster=broadcaster,
            delay_seconds=DRAFT_TASK_START_DELAY_SECONDS,
        )
    )
    return ApiResponse(data=result)


@router.get(
    "/systems/{system_id}/sections/{section_key}/draft/context",
    response_model=ApiResponse[DraftContextPack],
)
async def get_draft_context(
    system_id: str,
    section_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[DraftContextPack]:
    result = await assemble_draft_context_service(session, system_id, section_key)
    return ApiResponse(data=result)


@router.post("/systems/{system_id}/sections/{section_key}/draft/chat")
async def send_draft_chat_message(
    system_id: str,
    section_key: str,
    payload: DraftChatMessageRequest,
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    stream = await send_draft_chat_message_stream_service(
        session,
        system_id,
        section_key,
        payload.provider,
        payload.content,
    )
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/systems/{system_id}/sections/{section_key}/draft/chat/messages",
    response_model=ApiResponse[list[DraftChatMessageDetail]],
)
async def list_draft_chat_messages(
    system_id: str,
    section_key: str,
    provider: str = Query(default="claude", min_length=1, max_length=50),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[DraftChatMessageDetail]]:
    messages = await list_draft_chat_messages_service(
        session,
        system_id,
        section_key,
        provider,
    )
    return ApiResponse(data=messages)


@router.post(
    "/systems/{system_id}/sections/{section_key}/draft/validate-and-save",
    response_model=ApiResponse[DraftValidateResponse],
)
async def validate_and_save_draft(
    system_id: str,
    section_key: str,
    payload: DraftValidateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[DraftValidateResponse]:
    result = await validate_and_save_draft_service(
        session,
        system_id,
        section_key,
        payload.content_md,
        payload.outline_id,
    )
    return ApiResponse(data=result)


@router.get(
    "/systems/{system_id}/drafts",
    response_model=ApiResponse[list[SectionDraftDetail]],
)
async def list_section_drafts(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[SectionDraftDetail]]:
    drafts = await list_drafts_service(session, system_id)
    return ApiResponse(data=drafts)


@router.post(
    "/drafts/{draft_id}/approve",
    response_model=ApiResponse[SectionDraftDetail],
)
async def approve_section_draft(
    draft_id: str,
    payload: SectionDraftApproveRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SectionDraftDetail]:
    result = await approve_draft_service(session, draft_id, payload)
    return ApiResponse(data=result)


@router.post(
    "/drafts/{draft_id}/review",
    response_model=ApiResponse[ReviewCommentDetail],
    status_code=status.HTTP_201_CREATED,
)
async def add_review_comment(
    draft_id: str,
    payload: ReviewCommentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ReviewCommentDetail]:
    result = await add_review_comment_service(session, draft_id, payload)
    return ApiResponse(data=result)
