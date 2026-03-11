from __future__ import annotations

from inspect import isawaitable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.common.errors import ErrorCode
from app.core.exceptions import AppException
from app.modules.projects import repository
from app.modules.projects.schemas import (
    ProjectCreateRequest,
    ProjectDetail,
    ProjectListItem,
    ProjectSystemSummary,
)
from app.persistence.models import ExperimentalSystem, Project

SessionLike = AsyncSession | Session
T = TypeVar("T")


async def _maybe_await(value: T) -> T:
    if isawaitable(value):
        return await value
    return value


async def create_project(session: SessionLike, payload: ProjectCreateRequest) -> ProjectDetail:
    project = await repository.create_project(session, payload)
    await _maybe_await(session.commit())

    stored_project = await repository.get_project_detail(session, project.id)
    if stored_project is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Project not found",
            status_code=404,
            details={"project_id": project.id},
        )

    return _build_project_detail(stored_project)


async def list_projects(session: SessionLike) -> list[ProjectListItem]:
    projects = await repository.list_projects(session)
    return [_build_project_list_item(project) for project in projects]


async def get_project_detail(session: SessionLike, project_id: str) -> ProjectDetail:
    project = await repository.get_project_detail(session, project_id)
    if project is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="Project not found",
            status_code=404,
            details={"project_id": project_id},
        )

    return _build_project_detail(project)


def _build_project_list_item(project: Project) -> ProjectListItem:
    return ProjectListItem(
        id=project.id,
        name=project.name,
        owner_id=project.owner_id,
        status=project.status,
        template_asset_id=project.template_asset_id,
        system_count=len(project.systems),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _build_project_detail(project: Project) -> ProjectDetail:
    systems = sorted(
        project.systems,
        key=lambda item: (item.system_no, item.created_at, item.id),
    )
    return ProjectDetail(
        **_build_project_list_item(project).model_dump(),
        thesis_schema_json=project.thesis_schema_json,
        systems=[_build_project_system_summary(system) for system in systems],
    )


def _build_project_system_summary(system: ExperimentalSystem) -> ProjectSystemSummary:
    return ProjectSystemSummary(
        id=system.id,
        system_no=system.system_no,
        title=system.title,
        status=system.status,
        section_count=len(system.sections),
        created_at=system.created_at,
        updated_at=system.updated_at,
    )
