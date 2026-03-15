from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.common.enums import GateKey, GateRequirementKey, SystemState, TaskStatus
from app.modules.gates.service import resolve_active_gate, review_gate
from app.persistence.base import Base
from app.persistence.models.asset import Asset, AssetMetadata
from app.persistence.models.draft import Outline, OutlineAssetBinding, SectionDraft
from app.persistence.models.evidence import (
    AnalysisRun,
    Claim,
    ClaimEvidenceLink,
    FigurePlan,
    FigurePlanAsset,
)
from app.persistence.models.manifest import AssetManifest
from app.persistence.models.project import Project
from app.persistence.models.skeleton import StructureSkeleton
from app.persistence.models.system import ExperimentalSystem, SystemSection

ALL_GATE_TABLES = [
    Project.__table__,
    ExperimentalSystem.__table__,
    SystemSection.__table__,
    StructureSkeleton.__table__,
    Asset.__table__,
    AssetMetadata.__table__,
    AssetManifest.__table__,
    FigurePlan.__table__,
    FigurePlanAsset.__table__,
    AnalysisRun.__table__,
    Claim.__table__,
    ClaimEvidenceLink.__table__,
    Outline.__table__,
    OutlineAssetBinding.__table__,
    SectionDraft.__table__,
]


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine, tables=ALL_GATE_TABLES)

    with Session(engine) as db_session:
        yield db_session


def _create_system(
    session: Session, *, status: SystemState = SystemState.DRAFT
) -> ExperimentalSystem:
    project = Project(name="Thesis MVP", owner_id="owner-1")
    session.add(project)
    session.flush()

    system = ExperimentalSystem(
        project_id=project.id,
        system_no=1,
        title="System 1",
        status=status.value,
    )
    session.add(system)
    session.flush()
    return system


@pytest.mark.parametrize(
    ("status", "expected_gate"),
    [
        (SystemState.DRAFT, GateKey.G0),
        (SystemState.SYSTEM_DEFINED, GateKey.G1),
        (SystemState.FIGURE_PLAN_READY, GateKey.G2),
        (SystemState.DATA_PENDING, GateKey.G2),
        (SystemState.DATA_UPLOADED, GateKey.G2),
        (SystemState.ANALYSIS_READY, GateKey.G3),
        (SystemState.ASSETS_CONFIRMED, GateKey.G4),
        (SystemState.EVIDENCE_MATRIX_READY, GateKey.G4),
        (SystemState.OUTLINE_READY, GateKey.G5),
        (SystemState.SECTION_DRAFTING, GateKey.G5),
        (SystemState.CHAPTER_REVIEW, GateKey.G5),
        (SystemState.CHAPTER_APPROVED, GateKey.G5),
    ],
)
def test_resolve_active_gate_maps_fixed_gate_sequence(
    status: SystemState,
    expected_gate: GateKey,
) -> None:
    system = ExperimentalSystem(
        project_id="project-1", system_no=1, title="System 1", status=status.value
    )

    assert resolve_active_gate(system) == expected_gate


def test_review_gate_returns_structured_blocker_for_missing_confirmed_skeleton(
    session: Session,
) -> None:
    system = _create_system(session, status=SystemState.DRAFT)

    review = review_gate(session, system)

    assert review.gate == GateKey.G0
    assert review.required_checks == [GateRequirementKey.SYSTEM_DEFINED]
    assert review.satisfied is False
    assert len(review.blockers) == 1

    blocker = review.blockers[0]
    assert blocker.code == "skeleton_not_confirmed"
    assert blocker.gate == GateKey.G0
    assert blocker.current_state == SystemState.DRAFT
    assert blocker.required_checks == [GateRequirementKey.SYSTEM_DEFINED]
    assert blocker.details == {}


def test_review_gate_passes_when_confirmed_skeleton_exists(session: Session) -> None:
    system = _create_system(session, status=SystemState.DRAFT)
    session.add(
        StructureSkeleton(
            system_id=system.id,
            version=1,
            skeleton_json={"nodes": []},
            source_asset_ids=[],
            status="confirmed",
        )
    )
    session.flush()

    review = review_gate(session, system)

    assert review.gate == GateKey.G0
    assert review.satisfied is True
    assert review.blockers == []


def test_review_gate_uses_latest_figure_plan_versions(session: Session) -> None:
    system = _create_system(session, status=SystemState.SYSTEM_DEFINED)
    session.add_all(
        [
            FigurePlan(
                system_id=system.id,
                figure_no="F1",
                title="Figure 1",
                claim_text="Supports claim",
                data_needed_json=[],
                method_json={},
                acceptance_criteria_json=[],
                version=1,
                status="confirmed",
            ),
            FigurePlan(
                system_id=system.id,
                figure_no="F1",
                title="Figure 1 revised",
                claim_text="Supports claim",
                data_needed_json=[],
                method_json={},
                acceptance_criteria_json=[],
                version=2,
                status="draft",
            ),
        ]
    )
    session.flush()

    review = review_gate(session, system)

    assert review.gate == GateKey.G1
    assert review.satisfied is False
    assert [blocker.code for blocker in review.blockers] == ["figure_plan_not_ready"]
    assert review.blockers[0].details["unready_plans"] == [
        {"figure_no": "F1", "status": "draft", "version": 2}
    ]


def test_review_gate_g2_returns_blockers_for_missing_assets_and_analysis(session: Session) -> None:
    system = _create_system(session, status=SystemState.FIGURE_PLAN_READY)

    review = review_gate(session, system)

    assert review.gate == GateKey.G2
    assert review.satisfied is False
    assert {blocker.code for blocker in review.blockers} == {
        "no_figure_plan_images",
    }

    blockers_by_code = {blocker.code: blocker for blocker in review.blockers}
    assert blockers_by_code["no_figure_plan_images"].required_checks == [
        GateRequirementKey.DATA_UPLOADED
    ]


def test_review_gate_g2_passes_with_assets_and_succeeded_analysis(session: Session) -> None:
    system = _create_system(session, status=SystemState.FIGURE_PLAN_READY)
    plan = FigurePlan(
        system_id=system.id,
        figure_no="fig1",
        title="Figure 1",
        claim_text="test",
        status="confirmed",
    )
    session.add(plan)
    session.flush()
    asset = Asset(
        project_id=system.project_id,
        system_id=system.id,
        asset_type="figure",
        file_name="figure-1.png",
        storage_key="assets/figure-1.png",
        uploaded_by="owner-1",
    )
    session.add(asset)
    session.flush()
    session.add(FigurePlanAsset(
        figure_plan_id=plan.id,
        asset_id=asset.id,
        role="source_image",
        position=0,
    ))
    run = AnalysisRun(
        system_id=system.id,
        figure_plan_id=plan.id,
        asset_id=asset.id,
        run_type="image_analysis",
        status=TaskStatus.SUCCEEDED.value,
    )
    session.add(run)
    session.flush()

    review = review_gate(session, system)

    assert review.gate == GateKey.G2
    assert review.satisfied is True
    assert review.blockers == []


def test_review_gate_g3_passes_with_confirmed_manifest_and_metadata(session: Session) -> None:
    system = _create_system(session, status=SystemState.ANALYSIS_READY)
    asset = Asset(
        project_id=system.project_id,
        system_id=system.id,
        asset_type="figure",
        file_name="figure-1.png",
        storage_key="assets/figure-1.png",
        uploaded_by="owner-1",
    )
    session.add(asset)
    session.flush()
    session.add_all(
        [
            AssetMetadata(
                asset_id=asset.id,
                semantic_description="Confirmed microscopy figure",
                qc_status="confirmed",
            ),
            AssetManifest(
                project_id=system.project_id,
                system_id=system.id,
                version=1,
                status="confirmed",
                manifest_json={"assetCount": 1},
            ),
        ]
    )
    session.flush()

    review = review_gate(session, system)

    assert review.gate == GateKey.G3
    assert review.satisfied is True
    assert review.blockers == []


def test_review_gate_g3_uses_latest_manifest_version(session: Session) -> None:
    system = _create_system(session, status=SystemState.ANALYSIS_READY)
    asset = Asset(
        project_id=system.project_id,
        system_id=system.id,
        asset_type="figure",
        file_name="figure-1.png",
        storage_key="assets/figure-1.png",
        uploaded_by="owner-1",
    )
    session.add(asset)
    session.flush()
    session.add(
        AssetMetadata(
            asset_id=asset.id,
            semantic_description="Confirmed microscopy figure",
            qc_status="approved",
        )
    )
    session.add_all(
        [
            AssetManifest(
                project_id=system.project_id,
                system_id=system.id,
                version=1,
                status="confirmed",
                manifest_json={"assetCount": 1},
            ),
            AssetManifest(
                project_id=system.project_id,
                system_id=system.id,
                version=2,
                status="draft",
                manifest_json={"assetCount": 1},
            ),
        ]
    )
    session.flush()

    review = review_gate(session, system)

    assert review.gate == GateKey.G3
    assert review.satisfied is False
    assert [blocker.code for blocker in review.blockers] == ["assets_not_confirmed"]
    assert review.blockers[0].details["manifest_status"] == "draft"


def test_review_gate_g3_requires_manifest_and_confirmed_asset_metadata(session: Session) -> None:
    system = _create_system(session, status=SystemState.ANALYSIS_READY)
    asset = Asset(
        project_id=system.project_id,
        system_id=system.id,
        asset_type="figure",
        file_name="figure-1.png",
        storage_key="assets/figure-1.png",
        uploaded_by="owner-1",
    )
    session.add(asset)
    session.flush()
    session.add(
        AssetMetadata(
            asset_id=asset.id,
            semantic_description=None,
            qc_status="pending",
        )
    )
    session.flush()

    review = review_gate(session, system)

    assert review.gate == GateKey.G3
    assert review.satisfied is False
    assert [blocker.code for blocker in review.blockers] == ["assets_not_confirmed"]
    assert review.blockers[0].required_checks == [GateRequirementKey.ASSETS_CONFIRMED]
    assert review.blockers[0].details == {
        "manifest_status": None,
        "missing_metadata_asset_ids": [asset.id],
        "pending_qc_asset_ids": [asset.id],
    }


def test_review_gate_g4_requires_approved_claim_links_and_outline_bindings(
    session: Session,
) -> None:
    system = _create_system(session, status=SystemState.ASSETS_CONFIRMED)
    asset = Asset(
        project_id=system.project_id,
        system_id=system.id,
        asset_type="figure",
        file_name="figure-1.png",
        storage_key="assets/figure-1.png",
        uploaded_by="owner-1",
    )
    session.add(asset)
    session.flush()
    session.add(
        Claim(
            system_id=system.id,
            claim_id="claim-1",
            statement="Supported statement",
            section_ref="results",
            status="draft",
        )
    )
    session.add(
        Outline(
            system_id=system.id,
            version=1,
            outline_json={"sections": ["results"]},
            generated_from_claims_json=[],
            status="draft",
        )
    )
    session.flush()

    review = review_gate(session, system)

    assert review.gate == GateKey.G4
    assert review.satisfied is False
    assert {blocker.code for blocker in review.blockers} == {
        "evidence_matrix_not_ready",
        "outline_not_ready",
    }

    blockers_by_code = {blocker.code: blocker for blocker in review.blockers}
    assert blockers_by_code["evidence_matrix_not_ready"].required_checks == [
        GateRequirementKey.EVIDENCE_MATRIX_READY
    ]
    assert blockers_by_code["evidence_matrix_not_ready"].details == {
        "approved_claim_count": 0,
        "claims_missing_evidence": [],
    }
    assert blockers_by_code["outline_not_ready"].required_checks == [
        GateRequirementKey.OUTLINE_READY
    ]
    assert blockers_by_code["outline_not_ready"].details == {
        "outline_status": "draft",
        "outline_version": 1,
        "binding_count": 0,
    }


def test_review_gate_g4_blocks_approved_claims_with_invalid_sections(session: Session) -> None:
    system = _create_system(session, status=SystemState.ASSETS_CONFIRMED)
    asset = Asset(
        project_id=system.project_id,
        system_id=system.id,
        asset_type="figure",
        file_name="figure-1.png",
        storage_key="assets/figure-1.png",
        uploaded_by="owner-1",
    )
    session.add(asset)
    session.flush()
    session.add(
        SystemSection(system_id=system.id, section_key="results", title="Results", order_no=1)
    )
    claim = Claim(
        system_id=system.id,
        claim_id="claim-1",
        statement="Supported statement",
        section_ref="discussion",
        status="approved",
    )
    session.add(claim)
    session.flush()
    session.add(ClaimEvidenceLink(claim_record_id=claim.id, asset_id=asset.id))
    outline = Outline(
        system_id=system.id,
        version=1,
        outline_json={"sections": ["results"]},
        generated_from_claims_json=["claim-1"],
        status="confirmed",
    )
    session.add(outline)
    session.flush()
    session.add(
        OutlineAssetBinding(outline_id=outline.id, asset_id=asset.id, section_key="results")
    )
    session.flush()

    review = review_gate(session, system)

    assert review.gate == GateKey.G4
    assert review.satisfied is False
    assert [blocker.code for blocker in review.blockers] == ["approved_claim_sections_invalid"]
    assert review.blockers[0].required_checks == [GateRequirementKey.EVIDENCE_MATRIX_READY]
    assert review.blockers[0].details == {
        "invalid_claims": [
            {"claim_id": "claim-1", "section_ref": "discussion"},
        ]
    }


def test_review_gate_g5_requires_latest_draft_for_every_section_to_be_approved(
    session: Session,
) -> None:
    system = _create_system(session, status=SystemState.OUTLINE_READY)
    session.add_all(
        [
            SystemSection(
                system_id=system.id, section_key="intro", title="Introduction", order_no=1
            ),
            SystemSection(system_id=system.id, section_key="results", title="Results", order_no=2),
        ]
    )
    session.flush()
    session.add_all(
        [
            SectionDraft(
                system_id=system.id,
                section_key="intro",
                version=1,
                content_md="Approved intro",
                generated_from_claims_json=["claim-1"],
                status="approved",
                approved_at=datetime.now(UTC),
            ),
            SectionDraft(
                system_id=system.id,
                section_key="results",
                version=1,
                content_md="Old approved results",
                generated_from_claims_json=["claim-2"],
                status="approved",
                approved_at=datetime.now(UTC),
            ),
            SectionDraft(
                system_id=system.id,
                section_key="results",
                version=2,
                content_md="Pending results revision",
                generated_from_claims_json=["claim-2"],
                status="draft",
            ),
        ]
    )
    session.flush()

    review = review_gate(session, system)

    assert review.gate == GateKey.G5
    assert review.satisfied is False
    assert [blocker.code for blocker in review.blockers] == ["chapter_not_approved"]
    assert review.blockers[0].required_checks == [GateRequirementKey.CHAPTER_APPROVED]
    assert review.blockers[0].details == {
        "total_sections": 2,
        "approved_sections": ["intro"],
        "missing_sections": ["results"],
    }


def test_review_gate_passes_when_gate_facts_are_satisfied(session: Session) -> None:
    system = _create_system(session, status=SystemState.OUTLINE_READY)
    section = SystemSection(system_id=system.id, section_key="results", title="Results", order_no=1)
    session.add(section)
    session.flush()
    session.add(
        SectionDraft(
            system_id=system.id,
            section_key="results",
            version=1,
            content_md="Approved results",
            generated_from_claims_json=["claim-1"],
            status="approved",
            approved_at=datetime.now(UTC),
        )
    )
    session.flush()

    review = review_gate(session, system)

    assert review.gate == GateKey.G5
    assert review.satisfied is True
    assert review.blockers == []


def test_review_gate_g4_uses_latest_claim_version_for_approval(session: Session) -> None:
    """G4 should NOT pass when the latest claim version is unapproved,
    even if an older version was approved."""
    system = _create_system(session, status=SystemState.ASSETS_CONFIRMED)
    asset = Asset(
        project_id=system.project_id,
        system_id=system.id,
        asset_type="figure",
        file_name="figure-1.png",
        storage_key="assets/figure-1.png",
        uploaded_by="owner-1",
    )
    session.add(asset)
    session.flush()

    # claim-1 v1 approved, v2 draft => latest is draft, should NOT count
    claim_v1 = Claim(
        system_id=system.id,
        claim_id="claim-1",
        statement="Original statement",
        section_ref="results",
        status="approved",
        version=1,
    )
    claim_v2 = Claim(
        system_id=system.id,
        claim_id="claim-1",
        statement="Revised statement",
        section_ref="results",
        status="draft",
        version=2,
    )
    session.add_all([claim_v1, claim_v2])
    session.flush()

    # Add evidence link on the old approved version
    session.add(
        ClaimEvidenceLink(
            claim_record_id=claim_v1.id,
            asset_id=asset.id,
        )
    )
    # Confirmed outline with binding
    outline = Outline(
        system_id=system.id,
        version=1,
        outline_json={"sections": ["results"]},
        generated_from_claims_json=["claim-1"],
        status="confirmed",
    )
    session.add(outline)
    session.flush()
    session.add(
        OutlineAssetBinding(outline_id=outline.id, asset_id=asset.id, section_key="results")
    )
    session.flush()

    review = review_gate(session, system)

    assert review.gate == GateKey.G4
    assert review.satisfied is False

    evidence_blocker = next(
        (b for b in review.blockers if b.code == "evidence_matrix_not_ready"),
        None,
    )
    assert evidence_blocker is not None
    assert evidence_blocker.details["approved_claim_count"] == 0
