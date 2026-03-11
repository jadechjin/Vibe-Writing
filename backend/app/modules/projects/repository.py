from __future__ import annotations

from inspect import isawaitable
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.modules.projects.schemas import ProjectCreateRequest
from app.persistence.models import ExperimentalSystem, Project, ProjectMember, ProjectMemberRole

SessionLike = AsyncSession | Session
T = TypeVar("T")


async def _maybe_await(value: T) -> T:
    if isawaitable(value):
        return await value
    return value


async def create_project(session: SessionLike, payload: ProjectCreateRequest) -> Project:
    project = Project(
        name=payload.name,
        owner_id=payload.owner_id,
        template_asset_id=payload.template_asset_id,
        thesis_schema_json=payload.thesis_schema_json,
    )
    owner_member = ProjectMember(
        project=project,
        user_id=payload.owner_id,
        role=ProjectMemberRole.OWNER.value,
    )

    session.add_all([project, owner_member])
    await _maybe_await(session.flush())
    return project


async def list_projects(session: SessionLike) -> list[Project]:
    statement = (
        select(Project)
        .options(selectinload(Project.systems))
        .order_by(Project.created_at.desc(), Project.id.desc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().unique().all())


async def get_project_detail(session: SessionLike, project_id: str) -> Project | None:
    statement = (
        select(Project)
        .options(
            selectinload(Project.systems).selectinload(ExperimentalSystem.sections),
        )
        .where(Project.id == project_id)
    )
    result = await _maybe_await(session.execute(statement))
    return result.scalars().unique().one_or_none()
