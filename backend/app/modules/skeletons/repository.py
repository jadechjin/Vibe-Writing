from __future__ import annotations

from inspect import isawaitable
from typing import TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.persistence.models.skeleton import StructureSkeleton
from app.persistence.models.system import ExperimentalSystem

SessionLike = AsyncSession | Session
T = TypeVar("T")


async def _maybe_await(value: T) -> T:
    if isawaitable(value):
        return await value
    return value


async def get_system(session: SessionLike, system_id: str) -> ExperimentalSystem | None:
    result = await _maybe_await(session.execute(
        select(ExperimentalSystem).where(ExperimentalSystem.id == system_id)
    ))
    return result.scalar_one_or_none()


async def get_skeleton_by_id(session: SessionLike, skeleton_id: str) -> StructureSkeleton | None:
    result = await _maybe_await(session.execute(
        select(StructureSkeleton).where(StructureSkeleton.id == skeleton_id)
    ))
    return result.scalar_one_or_none()


async def list_skeletons(session: SessionLike, system_id: str) -> list[StructureSkeleton]:
    result = await _maybe_await(session.execute(
        select(StructureSkeleton)
        .where(StructureSkeleton.system_id == system_id)
        .order_by(StructureSkeleton.version.desc())
    ))
    return list(result.scalars().all())


async def get_next_version(session: SessionLike, system_id: str) -> int:
    result = await _maybe_await(session.execute(
        select(func.coalesce(func.max(StructureSkeleton.version), 0))
        .where(StructureSkeleton.system_id == system_id)
    ))
    return result.scalar_one() + 1


async def has_confirmed_skeleton(session: SessionLike, system_id: str) -> bool:
    result = await _maybe_await(session.execute(
        select(StructureSkeleton.id)
        .where(StructureSkeleton.system_id == system_id, StructureSkeleton.status == "confirmed")
        .limit(1)
    ))
    return result.scalar_one_or_none() is not None
