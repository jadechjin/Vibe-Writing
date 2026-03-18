from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import ApiResponse, PaginationMeta
from app.modules.projects.schemas import ProjectCreateRequest, ProjectDetail, ProjectListItem
from app.modules.projects.service import (
    create_project as create_project_service,
    delete_project as delete_project_service,
    get_project_detail as get_project_detail_service,
    list_projects as list_projects_service,
)
from app.persistence import get_db_session

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ApiResponse[ProjectDetail], status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ProjectDetail]:
    project = await create_project_service(session, payload)
    return ApiResponse(data=project)


@router.get("", response_model=ApiResponse[list[ProjectListItem]])
async def list_projects(
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[ProjectListItem]]:
    projects = await list_projects_service(session)
    return ApiResponse(
        data=projects,
        meta=PaginationMeta(total=len(projects), page=1, limit=len(projects)),
    )


@router.get("/{project_id}", response_model=ApiResponse[ProjectDetail])
async def get_project_detail(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ProjectDetail]:
    project = await get_project_detail_service(session, project_id)
    return ApiResponse(data=project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await delete_project_service(session, project_id)
