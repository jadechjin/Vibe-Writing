from __future__ import annotations

from typing import Callable, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums import GATE_REQUIREMENTS, GateKey, GateRequirementKey, SystemState, TaskStatus
from app.common.schemas import Blocker, GateReview
from app.persistence.models.asset import Asset, AssetMetadata
from app.persistence.models.draft import Outline, OutlineAssetBinding, SectionDraft
from app.persistence.models.evidence import AnalysisRun, Claim, ClaimEvidenceLink, FigurePlan
from app.persistence.models.manifest import AssetManifest
from app.persistence.models.skeleton import StructureSkeleton
from app.persistence.models.system import ExperimentalSystem, SystemSection

ACTIVE_GATE_BY_STATE: dict[str, GateKey] = {
    SystemState.DRAFT.value: GateKey.G0,
    SystemState.SYSTEM_DEFINED.value: GateKey.G1,
    SystemState.FIGURE_PLAN_READY.value: GateKey.G2,
    SystemState.DATA_PENDING.value: GateKey.G2,
    SystemState.DATA_UPLOADED.value: GateKey.G2,
    SystemState.ANALYSIS_READY.value: GateKey.G3,
    SystemState.ASSETS_CONFIRMED.value: GateKey.G4,
    SystemState.EVIDENCE_MATRIX_READY.value: GateKey.G4,
    SystemState.OUTLINE_READY.value: GateKey.G5,
    SystemState.SECTION_DRAFTING.value: GateKey.G5,
    SystemState.CHAPTER_REVIEW.value: GateKey.G5,
    SystemState.CHAPTER_APPROVED.value: GateKey.G5,
}


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
        blockers = check_figure_plan_ready(session, system)
    elif active_gate == GateKey.G2:
        blockers = check_data_and_analysis_ready(session, system)
    elif active_gate == GateKey.G3:
        blockers = check_assets_confirmed(session, system)
    elif active_gate == GateKey.G4:
        blockers = check_evidence_and_outline_ready(session, system)
    else:
        blockers = check_chapter_approved(session, system)

    return GateReview(
        gate=active_gate,
        satisfied=len(blockers) == 0,
        required_checks=list(GATE_REQUIREMENTS[active_gate]),
        blockers=blockers,
    )


def check_system_defined(_session: Session, system: ExperimentalSystem) -> list[Blocker]:
    blockers: list[Blocker] = []
    missing_fields: list[str] = []

    if not _has_text(system.research_goal):
        missing_fields.append("research_goal")
    if not _has_text(system.samples_subjects):
        missing_fields.append("samples_subjects")
    if not _has_text(system.variables_controls):
        missing_fields.append("variables_controls")
    if not _has_text(system.output_metrics):
        missing_fields.append("output_metrics")
    if not _has_text(system.methods_summary):
        missing_fields.append("methods_summary")
    if not system.system_card_json:
        missing_fields.append("system_card_json")

    if missing_fields:
        blockers.append(
            _build_blocker(
                code="system_definition_incomplete",
                message="System definition is incomplete.",
                gate=GateKey.G0,
                current_state=system.status,
                required_checks=[GateRequirementKey.SYSTEM_DEFINED],
                details={"missing_fields": missing_fields},
            )
        )

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
    plans = session.scalars(
        select(FigurePlan).where(FigurePlan.system_id == system.id)
    ).all()
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
    assets = session.scalars(select(Asset).where(Asset.system_id == system.id)).all()
    succeeded_run_count = len(
        session.scalars(
            select(AnalysisRun).where(
                AnalysisRun.system_id == system.id,
                AnalysisRun.status == TaskStatus.SUCCEEDED.value,
            )
        ).all()
    )

    blockers: list[Blocker] = []
    if not assets:
        blockers.append(
            _build_blocker(
                code="data_assets_missing",
                message="System data assets are missing.",
                gate=GateKey.G2,
                current_state=system.status,
                required_checks=[GateRequirementKey.DATA_UPLOADED],
                details={"asset_count": 0},
            )
        )

    if succeeded_run_count == 0:
        blockers.append(
            _build_blocker(
                code="analysis_not_ready",
                message="System analysis is not ready.",
                gate=GateKey.G2,
                current_state=system.status,
                required_checks=[GateRequirementKey.ANALYSIS_READY],
                details={"succeeded_run_count": 0},
            )
        )

    return blockers


def check_assets_confirmed(session: Session, system: ExperimentalSystem) -> list[Blocker]:
    manifests = session.scalars(
        select(AssetManifest).where(AssetManifest.system_id == system.id)
    ).all()
    latest_manifest = _latest_single_by_version(manifests)
    manifest_status = latest_manifest.status if latest_manifest is not None else None

    assets = session.scalars(select(Asset).where(Asset.system_id == system.id)).all()
    asset_ids = [asset.id for asset in assets]
    metadata_entries = session.scalars(
        select(AssetMetadata).where(AssetMetadata.asset_id.in_(asset_ids))
    ).all() if asset_ids else []
    metadata_by_asset_id = {entry.asset_id: entry for entry in metadata_entries}

    missing_metadata_asset_ids = [
        asset.id
        for asset in assets
        if not _has_text(getattr(metadata_by_asset_id.get(asset.id), "semantic_description", None))
    ]
    pending_qc_asset_ids = [
        asset.id
        for asset in assets
        if not _is_confirmed_status(getattr(metadata_by_asset_id.get(asset.id), "qc_status", None))
    ]

    if _is_confirmed_status(manifest_status) and not missing_metadata_asset_ids and not pending_qc_asset_ids:
        return []

    return [
        _build_blocker(
            code="assets_not_confirmed",
            message="Assets are not confirmed.",
            gate=GateKey.G3,
            current_state=system.status,
            required_checks=[GateRequirementKey.ASSETS_CONFIRMED],
            details={
                "manifest_status": manifest_status,
                "missing_metadata_asset_ids": missing_metadata_asset_ids,
                "pending_qc_asset_ids": pending_qc_asset_ids,
            },
        )
    ]


def check_evidence_and_outline_ready(session: Session, system: ExperimentalSystem) -> list[Blocker]:
    blockers: list[Blocker] = []

    claims = session.scalars(select(Claim).where(Claim.system_id == system.id)).all()
    latest_claims = _latest_by_version(claims, key=lambda item: item.claim_id)
    approved_claims = [claim for claim in latest_claims if _is_approved_status(claim.status)]
    allowed_section_keys = set(
        session.scalars(
            select(SystemSection.section_key).where(SystemSection.system_id == system.id)
        ).all()
    )
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
                gate=GateKey.G4,
                current_state=system.status,
                required_checks=[GateRequirementKey.EVIDENCE_MATRIX_READY],
                details={"invalid_claims": invalid_section_claims},
            )
        )

    approved_claim_ids = [claim.id for claim in approved_claims]
    linked_claim_ids = set(
        session.scalars(
            select(ClaimEvidenceLink.claim_record_id).where(
                ClaimEvidenceLink.claim_record_id.in_(approved_claim_ids)
            )
        ).all()
    ) if approved_claim_ids else set()
    claims_missing_evidence = [
        claim.claim_id
        for claim in approved_claims
        if claim.id not in linked_claim_ids
    ]

    if not approved_claims or claims_missing_evidence:
        blockers.append(
            _build_blocker(
                code="evidence_matrix_not_ready",
                message="Evidence matrix is not ready.",
                gate=GateKey.G4,
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
    binding_count = 0
    if latest_outline is not None:
        binding_count = len(
            session.scalars(
                select(OutlineAssetBinding).where(OutlineAssetBinding.outline_id == latest_outline.id)
            ).all()
        )

    outline_ready = (
        latest_outline is not None
        and _is_confirmed_status(latest_outline.status)
        and binding_count > 0
    )
    if not outline_ready:
        blockers.append(
            _build_blocker(
                code="outline_not_ready",
                message="Outline is not ready.",
                gate=GateKey.G4,
                current_state=system.status,
                required_checks=[GateRequirementKey.OUTLINE_READY],
                details={
                    "outline_status": latest_outline.status if latest_outline is not None else None,
                    "outline_version": latest_outline.version if latest_outline is not None else None,
                    "binding_count": binding_count,
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
    drafts = session.scalars(
        select(SectionDraft).where(SectionDraft.system_id == system.id)
    ).all()
    latest_drafts_by_section = {
        draft.section_key: draft for draft in _latest_by_version(drafts, key=lambda item: item.section_key)
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
            gate=GateKey.G5,
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
