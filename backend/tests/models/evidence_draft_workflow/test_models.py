from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.enums import SystemState, TaskStatus
from app.persistence.base import Base
from app.persistence.models.asset import Asset
from app.persistence.models.draft import (
    Outline,
    OutlineAssetBinding,
    ReviewComment,
    SectionDraft,
)
from app.persistence.models.evidence import (
    AnalysisRun,
    Claim,
    ClaimEvidenceLink,
    FigurePlan,
    FigurePlanAsset,
)
from app.persistence.models.manifest import AssetManifest
from app.persistence.models.project import Project
from app.persistence.models.system import ExperimentalSystem
from app.persistence.models.workflow import ApprovalTask, WorkflowEvent, WorkflowInstance

AUDIT_COLUMNS = {"id", "created_at", "updated_at", "created_by", "updated_by"}
VERSIONED_MODELS = [FigurePlan, AnalysisRun, Claim, Outline, SectionDraft, WorkflowInstance]
TRACKED_MODELS = [
    FigurePlanAsset,
    ClaimEvidenceLink,
    OutlineAssetBinding,
    ReviewComment,
    WorkflowEvent,
    ApprovalTask,
]
REQUIRED_TABLES = {
    "figure_plans",
    "figure_plan_assets",
    "claims",
    "claim_evidence_links",
    "analysis_runs",
    "outlines",
    "outline_asset_bindings",
    "section_drafts",
    "review_comments",
    "workflow_instances",
    "workflow_events",
    "approval_tasks",
}


def _sqlite_memory_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _seed_claim_evidence_link_context(
    session: Session,
) -> tuple[Project, ExperimentalSystem, Asset, Claim, AnalysisRun]:
    project = Project(name="Thesis MVP", owner_id="owner-1")
    session.add(project)
    session.flush()

    system = ExperimentalSystem(project_id=project.id, system_no=1, title="System 1")
    session.add(system)
    session.flush()

    asset = Asset(
        project_id=project.id,
        system_id=system.id,
        asset_type="figure",
        file_name="figure-1.png",
        storage_key="assets/figure-1.png",
        uploaded_by="owner-1",
    )
    claim = Claim(
        system_id=system.id,
        claim_id="claim-1",
        statement="Supported statement",
        section_ref="results",
    )
    run = AnalysisRun(system_id=system.id, asset_id=asset.id, run_type="vision")
    session.add_all([asset, claim, run])
    session.flush()

    return project, system, asset, claim, run


def _column_names(model: type) -> set[str]:
    return set(model.__table__.columns.keys())


def _foreign_key_targets(model: type, column_name: str) -> set[str]:
    return {fk.target_fullname for fk in model.__table__.c[column_name].foreign_keys}


def _unique_constraint_names(model: type) -> set[str]:
    return {constraint.name for constraint in model.__table__.constraints if constraint.name}


def _index_names(model: type) -> set[str]:
    return {index.name for index in model.__table__.indexes if index.name}


def test_versioned_models_keep_audit_and_version_columns() -> None:
    for model in VERSIONED_MODELS:
        columns = _column_names(model)
        assert AUDIT_COLUMNS.issubset(columns)
        assert "version" in columns

    for model in TRACKED_MODELS:
        assert AUDIT_COLUMNS.issubset(_column_names(model))


def test_relationship_targets_match_expected_core_tables() -> None:
    assert _foreign_key_targets(FigurePlan, "system_id") == {"experimental_systems.id"}
    assert _foreign_key_targets(FigurePlanAsset, "figure_plan_id") == {"figure_plans.id"}
    assert _foreign_key_targets(FigurePlanAsset, "asset_id") == {"assets.id"}
    assert _foreign_key_targets(AnalysisRun, "figure_plan_id") == {"figure_plans.id"}
    assert _foreign_key_targets(ClaimEvidenceLink, "claim_record_id") == {"claims.id"}
    assert _foreign_key_targets(OutlineAssetBinding, "outline_id") == {"outlines.id"}
    assert _foreign_key_targets(ReviewComment, "draft_id") == {"section_drafts.id"}
    assert _foreign_key_targets(WorkflowEvent, "instance_id") == {"workflow_instances.id"}
    assert _foreign_key_targets(ApprovalTask, "project_id") == {"projects.id"}


def test_uniqueness_and_defaults_match_workflow_requirements() -> None:
    assert "uq_figure_plans_system_figure_version" in _unique_constraint_names(FigurePlan)
    assert "uq_claims_system_claim_version" in _unique_constraint_names(Claim)
    assert "uq_outlines_system_version" in _unique_constraint_names(Outline)
    assert "uq_section_drafts_system_section_version" in _unique_constraint_names(SectionDraft)
    assert "uq_workflow_instances_scope_key_version" in _unique_constraint_names(WorkflowInstance)
    assert "ix_claim_evidence_links_unique_without_run" in _index_names(ClaimEvidenceLink)
    assert "ix_claim_evidence_links_unique_with_run" in _index_names(ClaimEvidenceLink)
    assert "ix_analysis_runs_figure_plan_id" in _index_names(AnalysisRun)

    assert FigurePlan.__table__.c.version.default.arg == 1
    assert AnalysisRun.__table__.c.status.default.arg == TaskStatus.QUEUED.value
    assert AnalysisRun.__table__.c.analysis_type.default.arg == "comprehensive"
    assert WorkflowInstance.__table__.c.current_state.default.arg == SystemState.DRAFT.value


def test_claim_evidence_links_enforce_uniqueness_for_null_and_non_null_analysis_runs() -> None:
    engine = _sqlite_memory_engine()
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            ExperimentalSystem.__table__,
            Asset.__table__,
            AssetManifest.__table__,
            FigurePlan.__table__,
            Claim.__table__,
            AnalysisRun.__table__,
            ClaimEvidenceLink.__table__,
        ],
    )

    with Session(engine) as session:
        _, _, asset, claim, run = _seed_claim_evidence_link_context(session)

        link_without_run = ClaimEvidenceLink(
            claim_record_id=claim.id,
            asset_id=asset.id,
            analysis_run_id=None,
            statistical_support={"kind": "raw"},
        )
        session.add(link_without_run)
        session.flush()

        duplicate_without_run = ClaimEvidenceLink(
            claim_record_id=claim.id,
            asset_id=asset.id,
            analysis_run_id=None,
            statistical_support={"kind": "duplicate"},
        )
        session.add(duplicate_without_run)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("Expected unique index to reject duplicate NULL analysis_run_id")

    with Session(engine) as session:
        _, _, asset, claim, run = _seed_claim_evidence_link_context(session)

        link_without_run = ClaimEvidenceLink(
            claim_record_id=claim.id,
            asset_id=asset.id,
            analysis_run_id=None,
            statistical_support={"kind": "raw"},
        )
        link_with_run = ClaimEvidenceLink(
            claim_record_id=claim.id,
            asset_id=asset.id,
            analysis_run_id=run.id,
            statistical_support={"kind": "analysis"},
        )
        session.add_all([link_without_run, link_with_run])
        session.flush()

        duplicate_with_run = ClaimEvidenceLink(
            claim_record_id=claim.id,
            asset_id=asset.id,
            analysis_run_id=run.id,
            statistical_support={"kind": "duplicate-analysis"},
        )
        session.add(duplicate_with_run)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError(
                "Expected unique index to reject duplicate non-NULL analysis_run_id"
            )


def test_claim_evidence_links_block_deleting_referenced_analysis_run() -> None:
    engine = _sqlite_memory_engine()
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            ExperimentalSystem.__table__,
            Asset.__table__,
            AssetManifest.__table__,
            FigurePlan.__table__,
            Claim.__table__,
            AnalysisRun.__table__,
            ClaimEvidenceLink.__table__,
        ],
    )

    with Session(engine) as session:
        _, _, asset, claim, run = _seed_claim_evidence_link_context(session)

        session.add(
            ClaimEvidenceLink(
                claim_record_id=claim.id,
                asset_id=asset.id,
                analysis_run_id=run.id,
                statistical_support={"kind": "analysis"},
            )
        )
        session.flush()

        session.delete(run)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("Expected foreign key to reject deleting referenced analysis run")
