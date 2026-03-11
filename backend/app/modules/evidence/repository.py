from __future__ import annotations

from inspect import isawaitable
from typing import TypeVar

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
    SystemSection,
)

SessionLike = AsyncSession | Session
T = TypeVar("T")


async def _maybe_await(value: T) -> T:
    if isawaitable(value):
        return await value
    return value


async def get_system_with_project(session: SessionLike, system_id: str) -> ExperimentalSystem | None:
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


async def list_system_sections(session: SessionLike, system_id: str) -> list[SystemSection]:
    statement = (
        select(SystemSection)
        .where(SystemSection.system_id == system_id)
        .order_by(SystemSection.order_no.asc(), SystemSection.created_at.asc(), SystemSection.id.asc())
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


async def list_links_for_claim(session: SessionLike, claim_record_id: str) -> list[ClaimEvidenceLink]:
    statement = (
        select(ClaimEvidenceLink)
        .where(ClaimEvidenceLink.claim_record_id == claim_record_id)
        .order_by(ClaimEvidenceLink.created_at.asc(), ClaimEvidenceLink.id.asc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


async def list_claim_evidence_links_for_system(session: SessionLike, system_id: str) -> list[ClaimEvidenceLink]:
    statement = (
        select(ClaimEvidenceLink)
        .join(Claim, Claim.id == ClaimEvidenceLink.claim_record_id)
        .where(Claim.system_id == system_id)
        .order_by(Claim.claim_id.asc(), ClaimEvidenceLink.created_at.asc(), ClaimEvidenceLink.id.asc())
    )
    result = await _maybe_await(session.execute(statement))
    return list(result.scalars().all())


__all__ = [
    "create_claim",
    "create_claim_evidence_link",
    "create_figure_plan",
    "get_analysis_run",
    "get_asset",
    "get_claim",
    "get_figure_plan",
    "get_next_claim_version",
    "get_next_figure_plan_version",
    "get_system_with_project",
    "list_analysis_runs_for_system",
    "list_assets_for_system",
    "list_claim_evidence_links_for_system",
    "list_claims",
    "list_figure_plans",
    "list_links_for_claim",
    "list_system_sections",
    "update_claim_status",
    "update_figure_plan_status",
]
