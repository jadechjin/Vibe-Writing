from __future__ import annotations

from typing import Callable, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.enums import GATE_REQUIREMENTS, GateKey, GateRequirementKey, SystemState, TaskStatus
from app.common.schemas import Blocker, GateReview
from app.persistence.models.asset import Asset, AssetMetadata
from app.persistence.models.draft import Outline, OutlineAssetBinding, SectionDraft
from app.persistence.models.evidence import (
    AnalysisRun,
    Claim,
    ClaimEvidenceLink,
    FigurePlan,
    FigurePlanAsset,
)
from app.persistence.models.g4_snapshot import G4Snapshot
from app.persistence.models.manifest import AssetManifest
from app.persistence.models.skeleton import StructureSkeleton
from app.persistence.models.system import ExperimentalSystem, SystemSection

ACTIVE_GATE_BY_STATE: dict[str, GateKey] = {
    SystemState.DRAFT.value: GateKey.G0,
    SystemState.SYSTEM_DEFINED.value: GateKey.G1,
    SystemState.FIGURE_PLAN_READY.value: GateKey.G1,
    SystemState.DATA_PENDING.value: GateKey.G1,
    SystemState.DATA_UPLOADED.value: GateKey.G1,
    SystemState.ANALYSIS_READY.value: GateKey.G2,
    SystemState.ASSETS_CONFIRMED.value: GateKey.G2,
    SystemState.EVIDENCE_MATRIX_READY.value: GateKey.G2,
    SystemState.OUTLINE_READY.value: GateKey.G3,
    SystemState.SECTION_DRAFTING.value: GateKey.G3,
    SystemState.CHAPTER_REVIEW.value: GateKey.G3,
    SystemState.CHAPTER_APPROVED.value: GateKey.G3,
}
NON_BLOCKING_BLOCKER_CODES = {"snapshot_stale"}


def resolve_active_gate(system: ExperimentalSystem) -> GateKey:
    return ACTIVE_GATE_BY_STATE.get(system.status, GateKey.G0)


def review_gate(
    session: Session,
    system: ExperimentalSystem,
    gate: GateKey | None = None,
) -> GateReview:
    active_gate = gate or resolve_active_gate(system)

    if active_gate == GateKey.G0:
        blockers = check_system_defined(session, system)
    elif active_gate == GateKey.G1:
        blockers = check_figure_plan_ready(session, system) + check_data_and_analysis_ready(session, system)
    elif active_gate == GateKey.G2:
        blockers = check_assets_confirmed(session, system) + check_evidence_and_outline_ready(session, system)
    elif system.status == SystemState.SECTION_DRAFTING.value:
        blockers = check_section_drafting_ready(session, system)
    else:
        blockers = check_chapter_approved(session, system)

    blocking_blockers = [
        blocker for blocker in blockers if blocker.code not in NON_BLOCKING_BLOCKER_CODES
    ]

    return GateReview(
        gate=active_gate,
        satisfied=len(blocking_blockers) == 0,
        required_checks=list(GATE_REQUIREMENTS[active_gate]),
        blockers=blockers,
    )


def check_system_defined(_session: Session, system: ExperimentalSystem) -> list[Blocker]:
    blockers: list[Blocker] = []

    has_confirmed = _session.scalar(
        select(StructureSkeleton.id)
        .where(StructureSkeleton.system_id == system.id, StructureSkeleton.status == "confirmed")
        .limit(1)
    )
    if has_confirmed is None:
        blockers.append(
            _build_blocker(
                code="skeleton_not_confirmed",
                message="No confirmed structure skeleton exists.",
                gate=GateKey.G0,
                current_state=system.status,
                required_checks=[GateRequirementKey.SYSTEM_DEFINED],
                details={},
            )
        )

    return blockers


def check_figure_plan_ready(session: Session, system: ExperimentalSystem) -> list[Blocker]:
    plans = session.scalars(select(FigurePlan).where(FigurePlan.system_id == system.id)).all()
    latest_plans = _latest_by_version(plans, key=lambda item: item.figure_no)
    unready_plans = [
        {
            "figure_no": plan.figure_no,
            "status": plan.status,
            "version": plan.version,
        }
        for plan in latest_plans
        if not _is_confirmed_status(plan.status)
    ]

    if latest_plans and not unready_plans:
        return []

    return [
        _build_blocker(
            code="figure_plan_not_ready",
            message="Figure plan is not confirmed.",
            gate=GateKey.G1,
            current_state=system.status,
            required_checks=[GateRequirementKey.FIGURE_PLAN_READY],
            details={"unready_plans": unready_plans},
        )
    ]


def check_data_and_analysis_ready(session: Session, system: ExperimentalSystem) -> list[Blocker]:
    # New logic: check figure-plan-level analysis coverage
    plans = session.scalars(
        select(FigurePlan).where(FigurePlan.system_id == system.id)
    ).all()
    latest_plans = _latest_by_version(plans, key=lambda p: p.figure_no)
    confirmed_plans = [p for p in latest_plans if _is_confirmed_status(p.status)]

    # Find plans that have uploaded images
    plans_with_images: list[FigurePlan] = []
    for plan in confirmed_plans:
        image_count = session.scalar(
            select(func.count(FigurePlanAsset.id)).where(
                FigurePlanAsset.figure_plan_id == plan.id
            )
        )
        if image_count and image_count > 0:
            plans_with_images.append(plan)

    if not plans_with_images:
        # Fallback: check old-style assets + analysis runs for backward compat
        assets = session.scalars(select(Asset).where(Asset.system_id == system.id)).all()
        old_succeeded = session.scalar(
            select(func.count(AnalysisRun.id)).where(
                AnalysisRun.system_id == system.id,
                AnalysisRun.status == TaskStatus.SUCCEEDED.value,
                AnalysisRun.figure_plan_id.is_(None),
            )
        )
        if assets and old_succeeded and old_succeeded > 0:
            return []  # Old-style data passes

        blockers: list[Blocker] = []
        if not assets:
            blockers.append(
                _build_blocker(
                    code="no_figure_plan_images",
                    message="No figure plans have uploaded images.",
                    gate=GateKey.G1,
                    current_state=system.status,
                    required_checks=[GateRequirementKey.DATA_UPLOADED],
                    details={"confirmed_plan_count": len(confirmed_plans)},
                )
            )
        else:
            blockers.append(
                _build_blocker(
                    code="analysis_not_ready",
                    message="System analysis is not ready.",
                    gate=GateKey.G1,
                    current_state=system.status,
                    required_checks=[GateRequirementKey.ANALYSIS_READY],
                    details={"succeeded_run_count": 0},
                )
            )
        return blockers

    # Check each plan with images has a succeeded analysis
    unanalyzed: list[str] = []
    for plan in plans_with_images:
        has_analysis = session.scalar(
            select(AnalysisRun.id).where(
                AnalysisRun.figure_plan_id == plan.id,
                AnalysisRun.status == TaskStatus.SUCCEEDED.value,
            ).limit(1)
        )
        has_evidence_text = bool(plan.evidence_text and plan.evidence_text.strip())
        if not has_analysis and not has_evidence_text:
            unanalyzed.append(plan.figure_no)

    if unanalyzed:
        return [
            _build_blocker(
                code="analysis_incomplete",
                message=f"Analysis incomplete for {len(unanalyzed)} figure plans.",
                gate=GateKey.G1,
                current_state=system.status,
                required_checks=[GateRequirementKey.ANALYSIS_READY],
                details={
                    "unanalyzed_plans": unanalyzed,
                    "analyzed": len(plans_with_images) - len(unanalyzed),
                    "total": len(plans_with_images),
                },
            )
        ]

    return []


def check_assets_confirmed(session: Session, system: ExperimentalSystem) -> list[Blocker]:
    blockers: list[Blocker] = []

    # --- Manifest status check ---
    manifests = session.scalars(
        select(AssetManifest).where(AssetManifest.system_id == system.id)
    ).all()
    latest_manifest = _latest_single_by_version(manifests)
    manifest_status = latest_manifest.status if latest_manifest is not None else None

    assets = session.scalars(
        select(Asset).where(Asset.system_id == system.id)
    ).all()
    metadata_rows = session.scalars(
        select(AssetMetadata).join(Asset, AssetMetadata.asset_id == Asset.id).where(
            Asset.system_id == system.id
        )
    ).all()
    metadata_by_asset_id = {metadata.asset_id: metadata for metadata in metadata_rows}
    missing_metadata_asset_ids = [
        asset.id
        for asset in assets
        if not (metadata_by_asset_id.get(asset.id) and (metadata_by_asset_id[asset.id].semantic_description or "").strip())
    ]
    pending_qc_asset_ids = [
        asset.id
        for asset in assets
        if not _is_confirmed_status(
            metadata_by_asset_id.get(asset.id).qc_status
            if metadata_by_asset_id.get(asset.id) is not None
            else None
        )
    ]

    if (
        not _is_confirmed_status(manifest_status)
        or missing_metadata_asset_ids
        or pending_qc_asset_ids
    ):
        blockers.append(
            _build_blocker(
                code="assets_not_confirmed",
                message="Assets are not confirmed.",
                gate=GateKey.G2,
                current_state=system.status,
                required_checks=[GateRequirementKey.ASSETS_CONFIRMED],
                details={
                    "manifest_status": manifest_status,
                    "missing_metadata_asset_ids": missing_metadata_asset_ids,
                    "pending_qc_asset_ids": pending_qc_asset_ids,
                },
            )
        )

    # --- FigurePlan completeness checks ---
    plans = session.scalars(
        select(FigurePlan).where(FigurePlan.system_id == system.id)
    ).all()
    latest_plans = _latest_by_version(plans, key=lambda p: p.figure_no)
    confirmed_plans = [p for p in latest_plans if _is_confirmed_status(p.status)]

    plans_missing_assets: list[str] = []
    plans_missing_evidence: list[str] = []

    for plan in confirmed_plans:
        asset_count = session.scalar(
            select(func.count(FigurePlanAsset.id)).where(
                FigurePlanAsset.figure_plan_id == plan.id
            )
        )
        if not asset_count or asset_count == 0:
            plans_missing_assets.append(plan.figure_no)
            continue

        has_evidence = bool(plan.evidence_text and plan.evidence_text.strip())
        has_analysis = session.scalar(
            select(AnalysisRun.id).where(
                AnalysisRun.figure_plan_id == plan.id,
                AnalysisRun.status == TaskStatus.SUCCEEDED.value,
            ).limit(1)
        )
        if not has_evidence and not has_analysis:
            plans_missing_evidence.append(plan.figure_no)

    if plans_missing_assets:
        blockers.append(
            _build_blocker(
                code="figure_plan_missing_assets",
                message=f"{len(plans_missing_assets)} figure plan(s) have no associated images.",
                gate=GateKey.G2,
                current_state=system.status,
                required_checks=[GateRequirementKey.ASSETS_CONFIRMED],
                details={"figure_nos": plans_missing_assets},
            )
        )

    if plans_missing_evidence:
        blockers.append(
            _build_blocker(
                code="figure_plan_missing_evidence",
                message=f"{len(plans_missing_evidence)} figure plan(s) have no analysis conclusion.",
                gate=GateKey.G2,
                current_state=system.status,
                required_checks=[GateRequirementKey.ASSETS_CONFIRMED],
                details={"figure_nos": plans_missing_evidence},
            )
        )

    return blockers


def check_evidence_and_outline_ready(session: Session, system: ExperimentalSystem) -> list[Blocker]:
    blockers: list[Blocker] = []

    sections = session.scalars(
        select(SystemSection).where(SystemSection.system_id == system.id)
    ).all()
    allowed_section_keys = {s.section_key for s in sections}

    claims = session.scalars(select(Claim).where(Claim.system_id == system.id)).all()
    latest_claims = _latest_by_version(claims, key=lambda item: item.claim_id)
    approved_claims = [claim for claim in latest_claims if _is_approved_status(claim.status)]

    # Existing: invalid section_ref check
    invalid_section_claims = [
        {"claim_id": claim.claim_id, "section_ref": claim.section_ref}
        for claim in approved_claims
        if claim.section_ref not in allowed_section_keys
    ]
    if invalid_section_claims:
        blockers.append(
            _build_blocker(
                code="approved_claim_sections_invalid",
                message="Approved claims reference undefined sections.",
                gate=GateKey.G2,
                current_state=system.status,
                required_checks=[GateRequirementKey.EVIDENCE_MATRIX_READY],
                details={"invalid_claims": invalid_section_claims},
            )
        )

    # NEW (4.1): per-section check — every section needs ≥1 approved claim
    claims_by_section: dict[str, list[Claim]] = {}
    for claim in approved_claims:
        claims_by_section.setdefault(claim.section_ref, []).append(claim)
    sections_missing_claims = [
        s.section_key for s in sections if s.section_key not in claims_by_section
    ]
    if sections_missing_claims:
        blockers.append(
            _build_blocker(
                code="section_missing_claims",
                message="Some sections have no approved claims.",
                gate=GateKey.G2,
                current_state=system.status,
                required_checks=[GateRequirementKey.EVIDENCE_MATRIX_READY],
                details={"sections": sections_missing_claims},
            )
        )

    # Existing: evidence link check
    approved_claim_ids = [claim.id for claim in approved_claims]
    linked_claim_ids = (
        set(
            session.scalars(
                select(ClaimEvidenceLink.claim_record_id).where(
                    ClaimEvidenceLink.claim_record_id.in_(approved_claim_ids)
                )
            ).all()
        )
        if approved_claim_ids
        else set()
    )
    claims_missing_evidence = [
        claim.claim_id for claim in approved_claims if claim.id not in linked_claim_ids
    ]

    if not approved_claims or claims_missing_evidence:
        blockers.append(
            _build_blocker(
                code="evidence_matrix_not_ready",
                message="Evidence matrix is not ready.",
                gate=GateKey.G2,
                current_state=system.status,
                required_checks=[GateRequirementKey.EVIDENCE_MATRIX_READY],
                details={
                    "approved_claim_count": len(approved_claims),
                    "claims_missing_evidence": claims_missing_evidence,
                },
            )
        )

    outlines = session.scalars(select(Outline).where(Outline.system_id == system.id)).all()
    latest_outline = _latest_single_by_version(outlines)

    # NEW (4.2): per-section binding check
    bindings: list[OutlineAssetBinding] = []
    if latest_outline is not None:
        bindings = list(
            session.scalars(
                select(OutlineAssetBinding).where(
                    OutlineAssetBinding.outline_id == latest_outline.id
                )
            ).all()
        )
    bound_sections = {b.section_key for b in bindings}
    sections_missing_binding = [
        s.section_key for s in sections if s.section_key not in bound_sections
    ]

    outline_ready = (
        latest_outline is not None
        and _is_confirmed_status(latest_outline.status)
        and len(bindings) > 0
    )
    if not outline_ready:
        blockers.append(
            _build_blocker(
                code="outline_not_ready",
                message="Outline is not ready.",
                gate=GateKey.G2,
                current_state=system.status,
                required_checks=[GateRequirementKey.OUTLINE_READY],
                details={
                    "outline_status": latest_outline.status if latest_outline is not None else None,
                    "outline_version": latest_outline.version
                    if latest_outline is not None
                    else None,
                    "binding_count": len(bindings),
                },
            )
        )
    elif sections_missing_binding:
        blockers.append(
            _build_blocker(
                code="section_missing_binding",
                message="Some sections have no outline binding.",
                gate=GateKey.G2,
                current_state=system.status,
                required_checks=[GateRequirementKey.OUTLINE_READY],
                details={"sections": sections_missing_binding},
            )
        )

    # NEW (4.3): staleness detection (warning level)
    if latest_outline is not None and _is_confirmed_status(latest_outline.status):
        outline_json = latest_outline.outline_json or {}
        outline_fp = (outline_json.get("meta") or {}).get("fingerprint") if isinstance(outline_json, dict) else None
        if outline_fp:
            latest_snapshot = session.scalars(
                select(G4Snapshot)
                .where(G4Snapshot.system_id == system.id)
                .order_by(G4Snapshot.created_at.desc())
                .limit(1)
            ).first()
            if latest_snapshot and latest_snapshot.fingerprint != outline_fp:
                blockers.append(
                    _build_blocker(
                        code="snapshot_stale",
                        message=(
                            "Outline is based on outdated data."
                            " Regeneration recommended but not required."
                        ),
                        gate=GateKey.G2,
                        current_state=system.status,
                        required_checks=[GateRequirementKey.OUTLINE_READY],
                        details={
                            "outline_fingerprint": outline_fp,
                            "current_fingerprint": latest_snapshot.fingerprint,
                        },
                    )
                )

    return blockers


def check_section_drafting_ready(session: Session, system: ExperimentalSystem) -> list[Blocker]:
    sections = session.scalars(
        select(SystemSection)
        .where(SystemSection.system_id == system.id)
        .order_by(SystemSection.order_no, SystemSection.section_key)
    ).all()
    drafts = session.scalars(select(SectionDraft).where(SectionDraft.system_id == system.id)).all()
    latest_drafts_by_section = {
        draft.section_key: draft
        for draft in _latest_by_version(drafts, key=lambda item: item.section_key)
    }

    missing_sections: list[str] = []
    invalid_sections: list[str] = []
    ready_sections: list[str] = []
    for section in sections:
        latest_draft = latest_drafts_by_section.get(section.section_key)
        if latest_draft is None or latest_draft.status == "draft":
            missing_sections.append(section.section_key)
            continue
        if not latest_draft.traceability_json:
            invalid_sections.append(section.section_key)
            continue
        ready_sections.append(section.section_key)

    blockers: list[Blocker] = []
    if missing_sections:
        blockers.append(
            _build_blocker(
                code="sections_missing_drafts",
                message=f"{len(missing_sections)} sections have no validated draft.",
                gate=GateKey.G3,
                current_state=system.status,
                required_checks=[GateRequirementKey.CHAPTER_APPROVED],
                details={
                    "total_sections": len(sections),
                    "ready_sections": ready_sections,
                    "missing_sections": missing_sections,
                },
            )
        )
    if invalid_sections:
        blockers.append(
            _build_blocker(
                code="sections_missing_traceability",
                message=f"{len(invalid_sections)} drafts lack traceability mapping.",
                gate=GateKey.G3,
                current_state=system.status,
                required_checks=[GateRequirementKey.CHAPTER_APPROVED],
                details={
                    "total_sections": len(sections),
                    "ready_sections": ready_sections,
                    "invalid_sections": invalid_sections,
                },
            )
        )
    return blockers


def check_chapter_approved(session: Session, system: ExperimentalSystem) -> list[Blocker]:
    sections = session.scalars(
        select(SystemSection)
        .where(SystemSection.system_id == system.id)
        .order_by(SystemSection.order_no, SystemSection.section_key)
    ).all()
    drafts = session.scalars(select(SectionDraft).where(SectionDraft.system_id == system.id)).all()
    latest_drafts_by_section = {
        draft.section_key: draft
        for draft in _latest_by_version(drafts, key=lambda item: item.section_key)
    }

    approved_sections: list[str] = []
    missing_sections: list[str] = []
    for section in sections:
        latest_draft = latest_drafts_by_section.get(section.section_key)
        if latest_draft is not None and _is_approved_status(latest_draft.status):
            approved_sections.append(section.section_key)
            continue
        missing_sections.append(section.section_key)

    if sections and not missing_sections:
        return []

    return [
        _build_blocker(
            code="chapter_not_approved",
            message="Chapter is not approved.",
            gate=GateKey.G3,
            current_state=system.status,
            required_checks=[GateRequirementKey.CHAPTER_APPROVED],
            details={
                "total_sections": len(sections),
                "approved_sections": approved_sections,
                "missing_sections": missing_sections,
            },
        )
    ]


def _build_blocker(
    *,
    code: str,
    message: str,
    gate: GateKey,
    current_state: str | None,
    required_checks: list[GateRequirementKey],
    details: dict[str, object],
) -> Blocker:
    return Blocker(
        code=code,
        message=message,
        gate=gate,
        current_state=_coerce_system_state(current_state),
        required_checks=required_checks,
        details=details,
    )


def _coerce_system_state(value: str | None) -> SystemState | None:
    if value is None:
        return None

    try:
        return SystemState(value)
    except ValueError:
        return None


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


def _is_confirmed_status(status: str | None) -> bool:
    return (status or "").strip().lower() in {"confirmed", "approved"}


def _is_approved_status(status: str | None) -> bool:
    return (status or "").strip().lower() == "approved"


_T = TypeVar("_T")


def _latest_by_version(items: list[_T], *, key: Callable[[_T], object]) -> list[_T]:
    latest: dict[object, _T] = {}
    for item in items:
        item_key = key(item)
        current = latest.get(item_key)
        if current is None or item.version > current.version:
            latest[item_key] = item
    return list(latest.values())


def _latest_single_by_version(items: list[_T]) -> _T | None:
    if not items:
        return None
    return max(items, key=lambda item: item.version)
