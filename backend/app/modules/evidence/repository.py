from __future__ import annotations

from inspect import isawaitable
from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.persistence.models import (
    AnalysisRun,
    Asset,
    Claim,
    ClaimEvidenceLink,
    ExperimentalSystem,
    FigurePlan,
    FigurePlanAsset,
    FigurePlanChatMessage,
    FigurePlanChatSession,
    SystemSection,
)

SessionLike = AsyncSession | Session
T = TypeVar("T")


async def _maybe_await(value: T) -> T:
    if isawaitable(value):
        return await value
    return value


async def get_system_with_project(
    session: SessionLike, system_id: str
) -> ExperimentalSystem | None:
    statement = select(ExperimentalSystem).where(ExperimentalSystem.id == system_id)
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def get_next_figure_plan_version(session: SessionLike, system_id: str, figure_no: str) -> int:
    statement = select(func.coalesce(func.max(FigurePlan.version), 0)).where(
        FigurePlan.system_id == system_id,
        FigurePlan.figure_no == figure_no,
    )
    result = await _maybe_await(session.execute(statement))
    max_version = result.scalar_one()
    return max_version + 1


async def create_figure_plan(
    session: SessionLike,
    *,
    system_id: str,
    figure_no: str = "",
    title: str = "",
    claim_text: str = "",
    status: str = "draft",
    **kwargs,
) -> FigurePlan:
    plan = FigurePlan(
        system_id=system_id,
        figure_no=figure_no,
        title=title,
        claim_text=claim_text,
        status=status,
        **kwargs,
    )
    session.add(plan)
    await _maybe_await(session.flush())
    return plan


async def get_figure_plan(session: SessionLike, plan_id: str) -> FigurePlan | None:
    statement = select(FigurePlan).where(FigurePlan.id == plan_id)
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def list_figure_plans(session: SessionLike, system_id: str) -> list[FigurePlan]:
    statement = (
        select(FigurePlan)
        .where(FigurePlan.system_id == system_id)
        .order_by(
            FigurePlan.figure_no.asc(),
            FigurePlan.version.asc(),
            FigurePlan.created_at.asc(),
            FigurePlan.id.asc(),
        )
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def update_figure_plan_status(session: SessionLike, plan_id: str, status: str) -> FigurePlan:
    plan = await get_figure_plan(session, plan_id)
    if plan is None:
        raise ValueError(f"FigurePlan {plan_id} not found")
    plan.status = status
    await _maybe_await(session.flush())
    return plan


async def update_figure_plan_brief(
    session: SessionLike, plan_id: str, brief_text: str
) -> FigurePlan:
    from datetime import datetime, timezone

    plan = await get_figure_plan(session, plan_id)
    if plan is None:
        raise ValueError(f"FigurePlan {plan_id} not found")
    plan.brief_text = brief_text
    plan.brief_confirmed_at = datetime.now(timezone.utc)
    await _maybe_await(session.flush())
    return plan


async def update_figure_plan_fields(
    session: SessionLike,
    plan: FigurePlan,
    payload: dict[str, object],
) -> FigurePlan:
    for field_name, value in payload.items():
        setattr(plan, field_name, value)
    await _maybe_await(session.flush())
    return plan


async def delete_figure_plan(session: SessionLike, plan: FigurePlan) -> None:
    await _maybe_await(session.delete(plan))
    await _maybe_await(session.flush())


async def list_system_sections(session: SessionLike, system_id: str) -> list[SystemSection]:
    statement = (
        select(SystemSection)
        .where(SystemSection.system_id == system_id)
        .order_by(
            SystemSection.order_no.asc(), SystemSection.created_at.asc(), SystemSection.id.asc()
        )
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def list_assets_for_system(session: SessionLike, system_id: str) -> list[Asset]:
    statement = (
        select(Asset)
        .options(selectinload(Asset.metadata_entry))
        .where(Asset.system_id == system_id)
        .order_by(Asset.created_at.asc(), Asset.file_name.asc(), Asset.id.asc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().unique().all())


async def list_analysis_runs_for_system(session: SessionLike, system_id: str) -> list[AnalysisRun]:
    statement = (
        select(AnalysisRun)
        .where(AnalysisRun.system_id == system_id)
        .order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def list_analysis_runs_for_figure_plans(
    session: SessionLike,
    figure_plan_ids: list[str],
) -> list[AnalysisRun]:
    if not figure_plan_ids:
        return []

    statement = (
        select(AnalysisRun)
        .where(AnalysisRun.figure_plan_id.in_(figure_plan_ids))
        .order_by(
            AnalysisRun.updated_at.desc(),
            AnalysisRun.created_at.desc(),
            AnalysisRun.id.desc(),
        )
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def create_analysis_run(
    session: SessionLike,
    *,
    system_id: str,
    figure_plan_id: str | None = None,
    asset_id: str | None = None,
    run_type: str = "image_analysis",
    analysis_type: str = "comprehensive",
    status: str = "queued",
    input_payload_json: dict[str, Any] | None = None,
) -> AnalysisRun:
    run = AnalysisRun(
        system_id=system_id,
        figure_plan_id=figure_plan_id,
        asset_id=asset_id,
        run_type=run_type,
        analysis_type=analysis_type,
        status=status,
        input_payload_json=input_payload_json or {},
    )
    session.add(run)
    await _maybe_await(session.flush())
    return run


# ---------------------------------------------------------------------------
# Claim CRUD (Task 9 – G4)
# ---------------------------------------------------------------------------


async def get_next_claim_version(session: SessionLike, system_id: str, claim_id: str) -> int:
    statement = select(func.coalesce(func.max(Claim.version), 0)).where(
        Claim.system_id == system_id,
        Claim.claim_id == claim_id,
    )
    result = await _maybe_await(session.execute(statement))
    max_version = result.scalar_one()
    return max_version + 1


async def create_claim(
    session: SessionLike,
    *,
    system_id: str,
    claim_id: str = "",
    statement: str = "",
    section_ref: str = "",
    confidence_level: str = "unreviewed",
    status: str = "draft",
    **kwargs,
) -> Claim:
    claim = Claim(
        system_id=system_id,
        claim_id=claim_id,
        statement=statement,
        section_ref=section_ref,
        confidence_level=confidence_level,
        status=status,
        **kwargs,
    )
    session.add(claim)
    await _maybe_await(session.flush())
    return claim


async def list_claims(session: SessionLike, system_id: str) -> list[Claim]:
    statement = (
        select(Claim)
        .where(Claim.system_id == system_id)
        .order_by(Claim.claim_id.asc(), Claim.version.asc(), Claim.created_at.asc(), Claim.id.asc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def get_claim(session: SessionLike, claim_id: str) -> Claim | None:
    statement = select(Claim).where(Claim.id == claim_id)
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def update_claim_status(session: SessionLike, claim: Claim, status: str) -> Claim:
    claim.status = status
    if status == "approved" and claim.approved_at is None:
        from datetime import datetime, timezone

        claim.approved_at = datetime.now(timezone.utc)
    await _maybe_await(session.flush())
    return claim


async def get_asset(session: SessionLike, asset_id: str) -> Asset | None:
    statement = select(Asset).where(Asset.id == asset_id)
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def get_analysis_run(session: SessionLike, analysis_run_id: str) -> AnalysisRun | None:
    statement = select(AnalysisRun).where(AnalysisRun.id == analysis_run_id)
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# ClaimEvidenceLink CRUD (Task 9 – G4)
# ---------------------------------------------------------------------------


async def create_claim_evidence_link(
    session: SessionLike,
    *,
    claim_record_id: str,
    asset_id: str,
    analysis_run_id: str | None = None,
    statistical_support: dict | None = None,
) -> ClaimEvidenceLink:
    link = ClaimEvidenceLink(
        claim_record_id=claim_record_id,
        asset_id=asset_id,
        analysis_run_id=analysis_run_id,
        statistical_support=statistical_support or {},
    )
    session.add(link)
    await _maybe_await(session.flush())
    return link


async def list_links_for_claim(
    session: SessionLike, claim_record_id: str
) -> list[ClaimEvidenceLink]:
    statement = (
        select(ClaimEvidenceLink)
        .where(ClaimEvidenceLink.claim_record_id == claim_record_id)
        .order_by(ClaimEvidenceLink.created_at.asc(), ClaimEvidenceLink.id.asc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def list_claim_evidence_links_for_system(
    session: SessionLike, system_id: str
) -> list[ClaimEvidenceLink]:
    statement = (
        select(ClaimEvidenceLink)
        .join(Claim, Claim.id == ClaimEvidenceLink.claim_record_id)
        .where(Claim.system_id == system_id)
        .order_by(
            Claim.claim_id.asc(), ClaimEvidenceLink.created_at.asc(), ClaimEvidenceLink.id.asc()
        )
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# FigurePlanAsset CRUD (G1 – image upload)
# ---------------------------------------------------------------------------


async def create_figure_plan_asset(
    session: SessionLike,
    *,
    figure_plan_id: str,
    asset_id: str,
    role: str = "source_image",
    position: int = 0,
) -> FigurePlanAsset:
    binding = FigurePlanAsset(
        figure_plan_id=figure_plan_id,
        asset_id=asset_id,
        role=role,
        position=position,
    )
    session.add(binding)
    await _maybe_await(session.flush())
    return binding


async def list_figure_plan_assets(
    session: SessionLike, figure_plan_id: str
) -> list[FigurePlanAsset]:
    statement = (
        select(FigurePlanAsset)
        .where(FigurePlanAsset.figure_plan_id == figure_plan_id)
        .order_by(
            FigurePlanAsset.position.asc(),
            FigurePlanAsset.created_at.asc(),
            FigurePlanAsset.id.asc(),
        )
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def list_figure_plan_assets_with_details(
    session: SessionLike,
    figure_plan_id: str,
) -> list[tuple[FigurePlanAsset, Asset]]:
    statement = (
        select(FigurePlanAsset, Asset)
        .join(Asset, FigurePlanAsset.asset_id == Asset.id)
        .where(FigurePlanAsset.figure_plan_id == figure_plan_id)
        .order_by(
            FigurePlanAsset.position.asc(),
            FigurePlanAsset.created_at.asc(),
            FigurePlanAsset.id.asc(),
        )
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.all())


async def list_figure_plan_assets_for_system(
    session: SessionLike,
    system_id: str,
) -> list[tuple[FigurePlanAsset, Asset]]:
    statement = (
        select(FigurePlanAsset, Asset)
        .join(FigurePlan, FigurePlanAsset.figure_plan_id == FigurePlan.id)
        .join(Asset, FigurePlanAsset.asset_id == Asset.id)
        .where(FigurePlan.system_id == system_id)
        .order_by(
            FigurePlan.figure_no.asc(),
            FigurePlan.version.asc(),
            FigurePlanAsset.position.asc(),
            FigurePlanAsset.created_at.asc(),
            FigurePlanAsset.id.asc(),
        )
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.all())


async def get_figure_plan_asset_by_asset_id(
    session: SessionLike,
    *,
    figure_plan_id: str,
    asset_id: str,
) -> FigurePlanAsset | None:
    statement = select(FigurePlanAsset).where(
        FigurePlanAsset.figure_plan_id == figure_plan_id,
        FigurePlanAsset.asset_id == asset_id,
    )
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def get_figure_plan_asset(session: SessionLike, binding_id: str) -> FigurePlanAsset | None:
    statement = select(FigurePlanAsset).where(FigurePlanAsset.id == binding_id)
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def delete_figure_plan_asset(session: SessionLike, binding: FigurePlanAsset) -> None:
    await _maybe_await(session.delete(binding))
    await _maybe_await(session.flush())


# ---------------------------------------------------------------------------
# FigurePlanChat CRUD (G1 – agent chat)
# ---------------------------------------------------------------------------


async def create_chat_session(
    session: SessionLike,
    *,
    figure_plan_id: str,
    provider: str,
    scope: str = "planning",
) -> FigurePlanChatSession:
    chat_session = FigurePlanChatSession(
        figure_plan_id=figure_plan_id,
        provider=provider,
        scope=scope,
    )
    session.add(chat_session)
    await _maybe_await(session.flush())
    return chat_session


async def get_active_chat_session(
    session: SessionLike,
    figure_plan_id: str,
    provider: str,
    scope: str = "planning",
) -> FigurePlanChatSession | None:
    statement = (
        select(FigurePlanChatSession)
        .where(
            FigurePlanChatSession.figure_plan_id == figure_plan_id,
            FigurePlanChatSession.provider == provider,
            FigurePlanChatSession.scope == scope,
            FigurePlanChatSession.status == "active",
        )
        .order_by(FigurePlanChatSession.created_at.desc())
        .limit(1)
    )
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none()


async def is_chat_session_busy(session: SessionLike, chat_session_id: str) -> bool:
    statement = select(FigurePlanChatMessage.id).where(
        FigurePlanChatMessage.session_id == chat_session_id,
        FigurePlanChatMessage.status == "streaming",
    )
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one_or_none() is not None


async def update_chat_session_fields(
    session: SessionLike,
    chat_session: FigurePlanChatSession,
    **kwargs: object,
) -> FigurePlanChatSession:
    for key, value in kwargs.items():
        setattr(chat_session, key, value)
    await _maybe_await(session.flush())
    return chat_session


async def create_chat_message(
    session: SessionLike,
    *,
    session_id: str,
    role: str,
    content: str,
    status: str = "completed",
    turn_index: int = 0,
) -> FigurePlanChatMessage:
    message = FigurePlanChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        status=status,
        turn_index=turn_index,
    )
    session.add(message)
    await _maybe_await(session.flush())
    return message


async def list_chat_messages(
    session: SessionLike, chat_session_id: str
) -> list[FigurePlanChatMessage]:
    statement = (
        select(FigurePlanChatMessage)
        .where(FigurePlanChatMessage.session_id == chat_session_id)
        .order_by(FigurePlanChatMessage.turn_index.asc(), FigurePlanChatMessage.created_at.asc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def get_next_turn_index(session: SessionLike, chat_session_id: str) -> int:
    statement = select(func.coalesce(func.max(FigurePlanChatMessage.turn_index), -1)).where(
        FigurePlanChatMessage.session_id == chat_session_id,
    )
    result = await _maybe_await(session.execute(statement))
    return result.scalar_one() + 1


async def update_chat_message_fields(
    session: SessionLike,
    message: FigurePlanChatMessage,
    **kwargs: object,
) -> FigurePlanChatMessage:
    for key, value in kwargs.items():
        setattr(message, key, value)
    await _maybe_await(session.flush())
    return message


__all__ = [
    "create_chat_message",
    "create_chat_session",
    "create_analysis_run",
    "create_claim",
    "create_claim_evidence_link",
    "create_figure_plan",
    "create_figure_plan_asset",
    "delete_figure_plan",
    "delete_figure_plan_asset",
    "get_active_chat_session",
    "get_analysis_run",
    "get_asset",
    "get_claim",
    "get_figure_plan",
    "get_figure_plan_asset",
    "get_figure_plan_asset_by_asset_id",
    "get_next_claim_version",
    "get_next_figure_plan_version",
    "get_next_turn_index",
    "get_system_with_project",
    "is_chat_session_busy",
    "list_analysis_runs_for_figure_plans",
    "list_analysis_runs_for_system",
    "list_assets_for_system",
    "list_chat_messages",
    "list_claim_evidence_links_for_system",
    "list_claims",
    "list_figure_plan_assets",
    "list_figure_plan_assets_for_system",
    "list_figure_plan_assets_with_details",
    "list_figure_plans",
    "list_links_for_claim",
    "list_system_sections",
    "update_chat_message_fields",
    "update_chat_session_fields",
    "update_claim_status",
    "update_figure_plan_fields",
    "update_figure_plan_brief",
    "update_figure_plan_status",
]
