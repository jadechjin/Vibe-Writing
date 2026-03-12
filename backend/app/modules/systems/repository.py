from __future__ import annotations

from inspect import isawaitable
from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.persistence.models.asset import Asset
from app.persistence.models.manifest import AssetManifest
from app.persistence.models.system import ExperimentalSystem, SystemSection
from app.persistence.models.workflow import WorkflowInstance

SessionLike = AsyncSession | Session
T = TypeVar("T")


async def _maybe_await(value: T) -> T:
    if isawaitable(value):
        return await value
    return value


async def create_system(
    session: SessionLike,
    *,
    project_id: str,
    system_no: int,
    title: str,
    research_goal: str | None = None,
    samples_subjects: str | None = None,
    variables_controls: str | None = None,
    output_metrics: str | None = None,
    methods_summary: str | None = None,
    system_card_json: dict[str, Any] | None = None,
) -> ExperimentalSystem:
    system = ExperimentalSystem(
        project_id=project_id,
        system_no=system_no,
        title=title,
        research_goal=research_goal,
        samples_subjects=samples_subjects,
        variables_controls=variables_controls,
        output_metrics=output_metrics,
        methods_summary=methods_summary,
        system_card_json=system_card_json or {},
    )
    session.add(system)
    await _maybe_await(session.flush())
    return system


async def create_system_sections(
    session: SessionLike,
    *,
    system_id: str,
    sections: list[tuple[str, str]],
) -> list[SystemSection]:
    created_sections: list[SystemSection] = []
    seen_section_keys: set[str] = set()

    for section_key, title in sections:
        normalized_key = section_key.strip()
        normalized_title = title.strip()
        if not normalized_key or not normalized_title or normalized_key in seen_section_keys:
            continue

        seen_section_keys.add(normalized_key)
        section = SystemSection(
            system_id=system_id,
            section_key=normalized_key,
            title=normalized_title,
            order_no=len(created_sections) + 1,
        )
        session.add(section)
        created_sections.append(section)

    if created_sections:
        await _maybe_await(session.flush())
    return created_sections


async def get_system_by_id(session: SessionLike, system_id: str) -> ExperimentalSystem | None:
    statement = (
        select(ExperimentalSystem)
        .options(selectinload(ExperimentalSystem.sections))
        .where(ExperimentalSystem.id == system_id)
    )
    result = await _maybe_await(session.execute(statement))
    return result.scalars().unique().one_or_none()


async def get_next_system_no(session: SessionLike, project_id: str) -> int:
    statement = select(func.coalesce(func.max(ExperimentalSystem.system_no), 0)).where(
        ExperimentalSystem.project_id == project_id
    )
    result = await _maybe_await(session.execute(statement))
    max_no = result.scalar_one()
    return max_no + 1


async def update_system_fields(
    session: SessionLike,
    system: ExperimentalSystem,
    **kwargs: Any,
) -> ExperimentalSystem:
    for field_name, value in kwargs.items():
        if value is not None:
            setattr(system, field_name, value)
    await _maybe_await(session.flush())
    return system


async def has_associated_data(session: SessionLike, system_id: str) -> bool:
    for model in (Asset, AssetManifest, WorkflowInstance):
        stmt = select(func.count()).select_from(model).where(model.system_id == system_id)
        result = await _maybe_await(session.execute(stmt))
        if result.scalar_one() > 0:
            return True
    return False


async def delete_system_by_id(session: SessionLike, system_id: str) -> None:
    stmt = select(ExperimentalSystem).where(ExperimentalSystem.id == system_id)
    result = await _maybe_await(session.execute(stmt))
    system = result.scalar_one_or_none()
    if system is not None:
        await _maybe_await(session.delete(system))
        await _maybe_await(session.flush())


__all__ = [
    "create_system",
    "create_system_sections",
    "delete_system_by_id",
    "get_next_system_no",
    "get_system_by_id",
    "has_associated_data",
    "update_system_fields",
]
