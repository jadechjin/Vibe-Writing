from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.websocket import get_broadcaster
from app.common.schemas import ApiResponse
from app.modules.systems.schemas import (
    AdvanceResponse,
    SystemCreateRequest,
    SystemDetail,
    SystemUpdateRequest,
)
from app.modules.systems.service import (
    advance_system as advance_system_service,
    create_system as create_system_service,
    get_system_detail as get_system_detail_service,
    get_workflow_snapshot as get_workflow_snapshot_service,
    update_system_definition as update_system_definition_service,
)
from app.modules.tasks.schemas import WorkflowSnapshot
from app.persistence import get_db_session

router = APIRouter(tags=["systems"])


@router.post(
    "/projects/{project_id}/systems",
    response_model=ApiResponse[SystemDetail],
    status_code=status.HTTP_201_CREATED,
)
async def create_system(
    project_id: str,
    payload: SystemCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SystemDetail]:
    system = await create_system_service(session, project_id, payload)
    return ApiResponse(data=system)


@router.get(
    "/systems/{system_id}",
    response_model=ApiResponse[SystemDetail],
)
async def get_system(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SystemDetail]:
    system = await get_system_detail_service(session, system_id)
    return ApiResponse(data=system)


@router.patch(
    "/systems/{system_id}",
    response_model=ApiResponse[SystemDetail],
)
async def update_system(
    system_id: str,
    payload: SystemUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SystemDetail]:
    system = await update_system_definition_service(session, system_id, payload)
    return ApiResponse(data=system)


@router.post(
    "/systems/{system_id}/advance",
    response_model=ApiResponse[AdvanceResponse],
)
async def advance_system(
    system_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AdvanceResponse]:
    broadcaster = get_broadcaster(request)
    result = await advance_system_service(session, system_id, broadcaster)
    return ApiResponse(data=result)


@router.get(
    "/systems/{system_id}/workflow",
    response_model=ApiResponse[WorkflowSnapshot | None],
)
async def get_system_workflow(
    system_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[WorkflowSnapshot | None]:
    snapshot = await get_workflow_snapshot_service(session, system_id)
    return ApiResponse(data=snapshot)
