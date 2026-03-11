from __future__ import annotations

from datetime import datetime, timezone
from inspect import isawaitable
from typing import TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.persistence.models import (
    Asset,
    Claim,
    ExperimentalSystem,
    Outline,
    OutlineAssetBinding,
    ReviewComment,
    SectionDraft,
    SystemSection,
)

SessionLike = AsyncSession | Session
T = TypeVar("T")


async def _maybe_await(value: T) -> T:
    if isawaitable(value):
        return await value
    return value


async def get_system_with_project(
    session: SessionLike,
    system_id: str,
) -> ExperimentalSystem | None:
    statement = select(ExperimentalSystem).where(ExperimentalSystem.id == system_id)
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def list_claims_by_ids(session: SessionLike, claim_ids: list[str]) -> list[Claim]:
    if not claim_ids:
        return []
    statement = select(Claim).where(Claim.id.in_(claim_ids))
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def get_asset(session: SessionLike, asset_id: str) -> Asset | None:
    statement = select(Asset).where(Asset.id == asset_id)
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def list_system_sections(session: SessionLike, system_id: str) -> list[SystemSection]:
    statement = (
        select(SystemSection)
        .where(SystemSection.system_id == system_id)
        .order_by(SystemSection.order_no.asc(), SystemSection.section_key.asc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def get_next_outline_version(session: SessionLike, system_id: str) -> int:
    statement = select(func.coalesce(func.max(Outline.version), 0)).where(
        Outline.system_id == system_id,
    )
    result = await _maybe_await(session.execute(statement))
    max_version = result.scalar_one()
    return max_version + 1


async def get_next_section_draft_version(
    session: SessionLike,
    system_id: str,
    section_key: str,
) -> int:
    statement = select(func.coalesce(func.max(SectionDraft.version), 0)).where(
        SectionDraft.system_id == system_id,
        SectionDraft.section_key == section_key,
    )
    result = await _maybe_await(session.execute(statement))
    max_version = result.scalar_one()
    return max_version + 1


async def create_outline(
    session: SessionLike,
    *,
    system_id: str,
    status: str = "draft",
    **kwargs,
) -> Outline:
    outline = Outline(
        system_id=system_id,
        status=status,
        **kwargs,
    )
    session.add(outline)
    await _maybe_await(session.flush())
    return outline


async def get_outline(session: SessionLike, outline_id: str) -> Outline | None:
    statement = select(Outline).where(Outline.id == outline_id)
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def list_outlines(session: SessionLike, system_id: str) -> list[Outline]:
    statement = (
        select(Outline)
        .where(Outline.system_id == system_id)
        .order_by(Outline.created_at.asc(), Outline.version.asc(), Outline.id.asc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def update_outline_status(session: SessionLike, outline: Outline, status: str) -> Outline:
    outline.status = status
    if status == "confirmed" and outline.approved_at is None:
        outline.approved_at = datetime.now(timezone.utc)
    await _maybe_await(session.flush())
    return outline


async def create_outline_binding(
    session: SessionLike,
    *,
    outline_id: str,
    asset_id: str,
    section_key: str = "",
    binding_note: str | None = None,
    **kwargs,
) -> OutlineAssetBinding:
    binding = OutlineAssetBinding(
        outline_id=outline_id,
        asset_id=asset_id,
        section_key=section_key,
        binding_note=binding_note,
        **kwargs,
    )
    session.add(binding)
    await _maybe_await(session.flush())
    return binding


async def list_outline_bindings(session: SessionLike, outline_id: str) -> list[OutlineAssetBinding]:
    statement = (
        select(OutlineAssetBinding)
        .where(OutlineAssetBinding.outline_id == outline_id)
        .order_by(OutlineAssetBinding.created_at.asc(), OutlineAssetBinding.id.asc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def list_outline_bindings_for_outlines(
    session: SessionLike,
    outline_ids: list[str],
) -> list[OutlineAssetBinding]:
    if not outline_ids:
        return []

    statement = (
        select(OutlineAssetBinding)
        .where(OutlineAssetBinding.outline_id.in_(outline_ids))
        .order_by(
            OutlineAssetBinding.outline_id.asc(),
            OutlineAssetBinding.created_at.asc(),
            OutlineAssetBinding.id.asc(),
        )
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def create_section_draft(
    session: SessionLike,
    *,
    system_id: str,
    section_key: str,
    content_md: str = "",
    outline_id: str | None = None,
    generated_from_claims_json: list[str] | None = None,
    status: str = "draft",
    created_by_agent: str | None = None,
    **kwargs,
) -> SectionDraft:
    draft = SectionDraft(
        system_id=system_id,
        section_key=section_key,
        content_md=content_md,
        outline_id=outline_id,
        generated_from_claims_json=generated_from_claims_json or [],
        status=status,
        created_by_agent=created_by_agent,
        **kwargs,
    )
    session.add(draft)
    await _maybe_await(session.flush())
    return draft


async def list_section_drafts(session: SessionLike, system_id: str) -> list[SectionDraft]:
    statement = (
        select(SectionDraft)
        .where(SectionDraft.system_id == system_id)
        .order_by(SectionDraft.section_key.asc(), SectionDraft.version.desc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def get_section_draft(session: SessionLike, draft_id: str) -> SectionDraft | None:
    statement = select(SectionDraft).where(SectionDraft.id == draft_id)
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def update_draft_status(
    session: SessionLike,
    draft: SectionDraft,
    status: str,
) -> SectionDraft:
    draft.status = status
    if status == "approved" and draft.approved_at is None:
        draft.approved_at = datetime.now(timezone.utc)
    await _maybe_await(session.flush())
    return draft


async def create_review_comment(
    session: SessionLike,
    *,
    draft_id: str,
    commenter_id: str,
    comment_text: str,
    decision: str | None = None,
    context_json: dict | None = None,
    **kwargs,
) -> ReviewComment:
    comment = ReviewComment(
        draft_id=draft_id,
        commenter_id=commenter_id,
        comment_text=comment_text,
        decision=decision,
        context_json=context_json or {},
        **kwargs,
    )
    session.add(comment)
    await _maybe_await(session.flush())
    return comment


async def list_review_comments(session: SessionLike, draft_id: str) -> list[ReviewComment]:
    statement = (
        select(ReviewComment)
        .where(ReviewComment.draft_id == draft_id)
        .order_by(ReviewComment.created_at.asc(), ReviewComment.id.asc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def list_review_comments_for_drafts(
    session: SessionLike,
    draft_ids: list[str],
) -> list[ReviewComment]:
    if not draft_ids:
        return []

    statement = (
        select(ReviewComment)
        .where(ReviewComment.draft_id.in_(draft_ids))
        .order_by(
            ReviewComment.draft_id.asc(),
            ReviewComment.created_at.asc(),
            ReviewComment.id.asc(),
        )
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


__all__ = [
    "create_outline",
    "create_outline_binding",
    "create_review_comment",
    "create_section_draft",
    "get_asset",
    "get_next_outline_version",
    "get_next_section_draft_version",
    "get_outline",
    "get_section_draft",
    "get_system_with_project",
    "list_claims_by_ids",
    "list_outline_bindings",
    "list_outline_bindings_for_outlines",
    "list_outlines",
    "list_review_comments",
    "list_review_comments_for_drafts",
    "list_section_drafts",
    "list_system_sections",
    "update_draft_status",
    "update_outline_status",
]
