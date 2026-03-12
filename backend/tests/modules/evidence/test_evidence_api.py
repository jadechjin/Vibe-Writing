from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.common.enums import EventType, SystemState, TaskStatus
from app.main import create_app
from app.persistence import get_db_session
from app.persistence.base import Base
from app.persistence.models import (
    AnalysisRun,
    Asset,
    AssetMetadata,
    Claim,
    ClaimEvidenceLink,
    ExperimentalSystem,
    FigurePlan,
    Project,
    ProjectMember,
    ProjectMemberRole,
    SystemSection,
    WorkflowEvent,
    WorkflowInstance,
)

ALL_TABLES = [
    Project.__table__,
    ProjectMember.__table__,
    ExperimentalSystem.__table__,
    SystemSection.__table__,
    Asset.__table__,
    AssetMetadata.__table__,
    AnalysisRun.__table__,
    FigurePlan.__table__,
    Claim.__table__,
    ClaimEvidenceLink.__table__,
    WorkflowInstance.__table__,
    WorkflowEvent.__table__,
]

DROP_TABLES = list(reversed(ALL_TABLES))


@pytest.fixture()
def engine() -> Generator:
    with NamedTemporaryFile(suffix=".db", delete=False) as database_file:
        database_path = Path(database_file.name)

    eng = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng, tables=ALL_TABLES)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng, tables=DROP_TABLES)
        eng.dispose()
        database_path.unlink(missing_ok=True)


@pytest.fixture()
def client(engine) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _create_project(session: Session, *, owner_id: str = "owner-1") -> Project:
    project = Project(name="Evidence Project", owner_id=owner_id)
    session.add(project)
    session.flush()
    session.add(ProjectMember(project_id=project.id, user_id=owner_id, role=ProjectMemberRole.OWNER.value))
    session.flush()
    return project


def _create_system(
    session: Session,
    *,
    project_id: str,
    title: str = "System 1",
    status: str = SystemState.DRAFT.value,
    system_no: int = 1,
) -> ExperimentalSystem:
    system = ExperimentalSystem(
        project_id=project_id,
        system_no=system_no,
        title=title,
        status=status,
    )
    session.add(system)
    session.flush()
    return system


def _wait_for_figure_plan_completion(engine, workflow_id: str, system_id: str, *, expected_plan_count: int) -> None:
    for _ in range(50):
        with Session(engine) as session:
            workflow = session.get(WorkflowInstance, workflow_id)
            plans = session.scalars(
                select(FigurePlan).where(FigurePlan.system_id == system_id).order_by(FigurePlan.version.asc())
            ).all()
            if (
                workflow is not None
                and workflow.status == TaskStatus.SUCCEEDED.value
                and len(plans) == expected_plan_count
            ):
                return
        time.sleep(0.01)

    raise AssertionError("Figure plan generation did not complete in time")


def _wait_for_evidence_matrix_completion(engine, workflow_id: str, system_id: str, *, expected_claim_count: int) -> None:
    for _ in range(50):
        with Session(engine) as session:
            workflow = session.get(WorkflowInstance, workflow_id)
            claims = session.scalars(
                select(Claim).where(Claim.system_id == system_id).order_by(Claim.version.asc(), Claim.claim_id.asc())
            ).all()
            if (
                workflow is not None
                and workflow.status == TaskStatus.SUCCEEDED.value
                and len(claims) == expected_claim_count
            ):
                return
        time.sleep(0.01)

    raise AssertionError("Evidence matrix generation did not complete in time")


def _create_asset_with_analysis(
    session: Session,
    *,
    project_id: str,
    system_id: str,
    file_name: str = "fig-1.png",
    storage_key: str = "uploads/fig-1.png",
    semantic_description: str = "Validated asset",
    qc_status: str = "confirmed",
) -> Asset:
    asset = Asset(
        project_id=project_id,
        system_id=system_id,
        asset_type="figure",
        file_name=file_name,
        storage_key=storage_key,
        uploaded_by="owner-1",
    )
    session.add(asset)
    session.flush()
    session.add(
        AssetMetadata(
            asset_id=asset.id,
            semantic_description=semantic_description,
            qc_status=qc_status,
        )
    )
    session.add(
        AnalysisRun(
            system_id=system_id,
            asset_id=asset.id,
            run_type="vision_qc",
            status=TaskStatus.SUCCEEDED.value,
        )
    )
    session.flush()
    return asset




def test_generate_figure_plan_returns_accepted(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.commit()
        system_id = system.id

    response = client.post(f"/api/systems/{system_id}/figure-plans/generate", json={})

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    handle = body["data"]["handle"]
    workflow_id = handle["workflow_id"]
    assert workflow_id is not None
    assert handle["job_id"].startswith(f"figure_plan_generate:{system_id}:")
    assert handle["status"] == TaskStatus.QUEUED.value

    with Session(engine) as session:
        workflow = session.scalars(
            select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
        ).one()
        events = session.scalars(
            select(WorkflowEvent).where(WorkflowEvent.instance_id == workflow.id).order_by(WorkflowEvent.created_at.asc())
        ).all()

    assert workflow.workflow_key == "figure_plan_generate"
    assert workflow.status == TaskStatus.QUEUED.value
    assert [event.event_type for event in events] == [EventType.TASK_CREATED.value]

    _wait_for_figure_plan_completion(engine, workflow_id, system_id, expected_plan_count=1)

    with Session(engine) as session:
        plans = session.scalars(
            select(FigurePlan).where(FigurePlan.system_id == system_id).order_by(FigurePlan.version.asc())
        ).all()
        workflow = session.scalars(
            select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
        ).one()
        events = session.scalars(
            select(WorkflowEvent).where(WorkflowEvent.instance_id == workflow.id).order_by(WorkflowEvent.created_at.asc())
        ).all()

    assert len(plans) == 1
    assert plans[0].system_id == system_id
    assert plans[0].figure_no == "1"
    assert plans[0].version == 1
    assert plans[0].status == "draft"
    assert workflow.status == TaskStatus.SUCCEEDED.value
    assert [event.event_type for event in events] == [EventType.TASK_CREATED.value, EventType.TASK_SUCCEEDED.value]

    list_response = client.get(f"/api/systems/{system_id}/figure-plans")
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["success"] is True
    assert len(list_body["data"]) == 1
    assert list_body["data"][0]["figureNo"] == "1"
    assert list_body["data"][0]["version"] == 1


def test_list_figure_plans_empty(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.commit()
        system_id = system.id

    response = client.get(f"/api/systems/{system_id}/figure-plans")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == []


def test_confirm_figure_plan(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        plan = FigurePlan(
            system_id=system.id,
            figure_no="1",
            title="Fig 1",
            claim_text="test",
            status="draft",
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id

    response = client.post(f"/api/figure-plans/{plan_id}/confirm")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "confirmed"

    with Session(engine) as session:
        updated = session.get(FigurePlan, plan_id)
    assert updated is not None
    assert updated.status == "confirmed"


def test_confirm_figure_plan_rejects_invalid_status(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        plan = FigurePlan(
            system_id=system.id,
            figure_no="1",
            title="Fig 1",
            claim_text="test",
            status="draft",
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id

    response = client.post(f"/api/figure-plans/{plan_id}/confirm", json={"status": "approved"})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Claims + ClaimEvidenceLink (G4)
# ---------------------------------------------------------------------------


def test_generate_evidence_matrix_returns_accepted(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(
            session,
            project_id=project.id,
            status=SystemState.ASSETS_CONFIRMED.value,
        )
        session.add_all(
            [
                SystemSection(system_id=system.id, section_key="results", title="Results", order_no=1),
                SystemSection(system_id=system.id, section_key="discussion", title="Discussion", order_no=2),
            ]
        )
        _create_asset_with_analysis(session, project_id=project.id, system_id=system.id)
        session.commit()
        system_id = system.id

    response = client.post(f"/api/systems/{system_id}/evidence-matrix/generate", json={})

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    handle = body["data"]["handle"]
    workflow_id = handle["workflow_id"]
    assert workflow_id is not None
    assert handle["job_id"].startswith(f"evidence_matrix_generate:{system_id}:")
    assert handle["status"] == TaskStatus.QUEUED.value

    with Session(engine) as session:
        workflow = session.scalars(
            select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
        ).one()
        events = session.scalars(
            select(WorkflowEvent).where(WorkflowEvent.instance_id == workflow.id).order_by(WorkflowEvent.created_at.asc())
        ).all()

    assert workflow.workflow_key == "evidence_matrix_generate"
    assert workflow.status == TaskStatus.QUEUED.value
    assert [event.event_type for event in events] == [EventType.TASK_CREATED.value]

    _wait_for_evidence_matrix_completion(engine, workflow_id, system_id, expected_claim_count=2)

    with Session(engine) as session:
        claims = session.scalars(
            select(Claim).where(Claim.system_id == system_id).order_by(Claim.claim_id.asc(), Claim.version.asc())
        ).all()
        links = session.scalars(
            select(ClaimEvidenceLink)
            .join(Claim, Claim.id == ClaimEvidenceLink.claim_record_id)
            .where(Claim.system_id == system_id)
            .order_by(ClaimEvidenceLink.created_at.asc())
        ).all()
        workflow = session.scalars(
            select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
        ).one()
        events = session.scalars(
            select(WorkflowEvent).where(WorkflowEvent.instance_id == workflow.id).order_by(WorkflowEvent.created_at.asc())
        ).all()

    assert [claim.claim_id for claim in claims] == ["C1", "C2"]
    assert {claim.section_ref for claim in claims} == {"results", "discussion"}
    assert all(claim.status == "draft" for claim in claims)
    assert len(links) == 2
    assert workflow.status == TaskStatus.SUCCEEDED.value
    assert [event.event_type for event in events] == [EventType.TASK_CREATED.value, EventType.TASK_SUCCEEDED.value]

    list_response = client.get(f"/api/systems/{system_id}/claims")
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["success"] is True
    assert [item["claimId"] for item in list_body["data"]] == ["C1", "C2"]


def test_list_claims_empty(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.commit()
        system_id = system.id

    response = client.get(f"/api/systems/{system_id}/claims")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == []


def test_approve_claim(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.add(
            SystemSection(system_id=system.id, section_key="results", title="Results", order_no=1)
        )
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="test claim",
            section_ref="results",
            status="draft",
        )
        session.add(claim)
        session.commit()
        claim_record_id = claim.id

    response = client.patch(f"/api/claims/{claim_record_id}", json={"status": "approved"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "approved"
    assert body["data"]["approvedAt"] is not None

    with Session(engine) as session:
        updated = session.get(Claim, claim_record_id)
    assert updated is not None
    assert updated.status == "approved"
    assert updated.approved_at is not None


def test_approve_claim_rejects_unknown_section_ref(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.add(
            SystemSection(system_id=system.id, section_key="results", title="Results", order_no=1)
        )
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="test claim",
            section_ref="discussion",
            status="draft",
        )
        session.add(claim)
        session.commit()
        claim_record_id = claim.id
        system_id = system.id

    response = client.patch(f"/api/claims/{claim_record_id}", json={"status": "approved"})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "Claim section_ref is not defined for this system"
    assert body["data"]["code"] == "validation_error"
    assert body["data"]["details"] == {
        "claim_id": claim_record_id,
        "system_id": system_id,
        "section_ref": "discussion",
    }

    with Session(engine) as session:
        updated = session.get(Claim, claim_record_id)
    assert updated is not None
    assert updated.status == "draft"
    assert updated.approved_at is None


def test_approve_claim_rejects_invalid_status(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="test claim",
            section_ref="results",
            status="draft",
        )
        session.add(claim)
        session.commit()
        claim_record_id = claim.id

    response = client.patch(f"/api/claims/{claim_record_id}", json={"status": "confirmed"})

    assert response.status_code == 422


def test_approve_claim_reapprove_keeps_original_approved_at(client: TestClient, engine) -> None:
    original_approved_at = datetime(2026, 1, 1, tzinfo=UTC)
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.add(
            SystemSection(system_id=system.id, section_key="results", title="Results", order_no=1)
        )
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="test claim",
            section_ref="results",
            status="approved",
            approved_at=original_approved_at,
        )
        session.add(claim)
        session.commit()
        claim_record_id = claim.id

    expected_approved_at = original_approved_at.replace(tzinfo=None)

    response = client.patch(f"/api/claims/{claim_record_id}", json={"status": "approved"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["approvedAt"] == expected_approved_at.isoformat()

    with Session(engine) as session:
        updated = session.get(Claim, claim_record_id)
    assert updated is not None
    assert updated.approved_at == expected_approved_at


def test_create_claim_evidence_link(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="test claim",
            section_ref="results",
            status="draft",
        )
        session.add(claim)
        session.flush()
        asset = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="figure",
            file_name="fig-1.png",
            storage_key="uploads/fig-1.png",
            uploaded_by="owner-1",
        )
        session.add(asset)
        session.commit()
        claim_record_id = claim.id
        asset_id = asset.id

    response = client.post(
        f"/api/claims/{claim_record_id}/evidence-links",
        json={"assetId": asset_id},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["claimRecordId"] == claim_record_id
    assert body["data"]["assetId"] == asset_id

    with Session(engine) as session:
        link = session.scalars(
            select(ClaimEvidenceLink).where(ClaimEvidenceLink.claim_record_id == claim_record_id)
        ).one()
    assert link.asset_id == asset_id


# ---------------------------------------------------------------------------
# 404 scenarios
# ---------------------------------------------------------------------------


def test_generate_figure_plan_missing_system_returns_404(client: TestClient) -> None:
    response = client.post("/api/systems/missing-system/figure-plans/generate", json={})

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_generate_evidence_matrix_missing_system_returns_404(client: TestClient) -> None:
    response = client.post("/api/systems/missing-system/evidence-matrix/generate", json={})

    assert response.status_code == 404
    assert response.json()["success"] is False


# ---------------------------------------------------------------------------
# HC-11: Cross-system boundary validation
# ---------------------------------------------------------------------------


def test_create_claim_evidence_link_cross_system_asset_returns_422(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system1 = _create_system(session, project_id=project.id, title="System 1", system_no=1)
        system2 = _create_system(session, project_id=project.id, title="System 2", system_no=2)
        claim = Claim(
            system_id=system1.id,
            claim_id="C1",
            statement="test claim",
            section_ref="results",
            status="draft",
        )
        session.add(claim)
        session.flush()
        asset = Asset(
            project_id=project.id,
            system_id=system2.id,
            asset_type="figure",
            file_name="fig-1.png",
            storage_key="uploads/fig-1.png",
            uploaded_by="owner-1",
        )
        session.add(asset)
        session.commit()
        claim_record_id = claim.id
        asset_id = asset.id

    response = client.post(
        f"/api/claims/{claim_record_id}/evidence-links",
        json={"assetId": asset_id},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "system" in body["error"].lower()


# ---------------------------------------------------------------------------
# HC-12: Duplicate link detection
# ---------------------------------------------------------------------------


def test_create_claim_evidence_link_duplicate_returns_409(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="test claim",
            section_ref="results",
            status="draft",
        )
        session.add(claim)
        session.flush()
        asset = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="figure",
            file_name="fig-1.png",
            storage_key="uploads/fig-1.png",
            uploaded_by="owner-1",
        )
        session.add(asset)
        session.flush()
        link = ClaimEvidenceLink(
            claim_record_id=claim.id,
            asset_id=asset.id,
        )
        session.add(link)
        session.commit()
        claim_record_id = claim.id
        asset_id = asset.id

    response = client.post(
        f"/api/claims/{claim_record_id}/evidence-links",
        json={"assetId": asset_id},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert "already exists" in body["error"].lower() or "duplicate" in body["error"].lower()


def test_create_claim_evidence_link_rejects_analysis_run_asset_mismatch(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="test claim",
            section_ref="results",
            status="draft",
        )
        session.add(claim)
        session.flush()
        asset1 = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="figure",
            file_name="fig-1.png",
            storage_key="uploads/fig-1.png",
            uploaded_by="owner-1",
        )
        asset2 = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="figure",
            file_name="fig-2.png",
            storage_key="uploads/fig-2.png",
            uploaded_by="owner-1",
        )
        session.add_all([asset1, asset2])
        session.flush()
        analysis_run = AnalysisRun(
            system_id=system.id,
            asset_id=asset1.id,
            run_type="vision_qc",
        )
        session.add(analysis_run)
        session.commit()
        claim_record_id = claim.id
        asset_id = asset2.id
        analysis_run_id = analysis_run.id

    response = client.post(
        f"/api/claims/{claim_record_id}/evidence-links",
        json={"assetId": asset_id, "analysisRunId": analysis_run_id},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "asset" in body["error"].lower()


# ---------------------------------------------------------------------------
# Missing resource scenarios
# ---------------------------------------------------------------------------


def test_create_claim_evidence_link_missing_claim_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/claims/missing-claim-id/evidence-links",
        json={"assetId": "some-asset-id"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False


def test_create_claim_evidence_link_missing_asset_returns_404(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="test claim",
            section_ref="results",
            status="draft",
        )
        session.add(claim)
        session.commit()
        claim_record_id = claim.id

    response = client.post(
        f"/api/claims/{claim_record_id}/evidence-links",
        json={"assetId": "missing-asset-id"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False


# ---------------------------------------------------------------------------
# Batch approve claims tests
# ---------------------------------------------------------------------------


def _create_claim_with_section(
    session: Session,
    system_id: str,
    claim_id: str,
    section_key: str,
) -> Claim:
    section = session.scalars(
        select(SystemSection).where(
            SystemSection.system_id == system_id,
            SystemSection.section_key == section_key,
        )
    ).first()
    if section is None:
        section = SystemSection(
            system_id=system_id,
            section_key=section_key,
            title=section_key.capitalize(),
            order_no=1,
        )
        session.add(section)
        session.flush()
    claim = Claim(
        system_id=system_id,
        claim_id=claim_id,
        statement=f"Claim {claim_id}",
        section_ref=section_key,
        status="draft",
    )
    session.add(claim)
    session.flush()
    return claim


def test_batch_approve_claims_all_succeed(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        c1 = _create_claim_with_section(session, system.id, "C1", "results")
        c2 = _create_claim_with_section(session, system.id, "C2", "results")
        session.commit()
        system_id = system.id
        c1_id, c2_id = c1.id, c2.id

    response = client.post(
        f"/api/systems/{system_id}/claims/batch-approve",
        json={"claimIds": [c1_id, c2_id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert set(body["data"]["succeeded"]) == {c1_id, c2_id}
    assert body["data"]["failed"] == []


def test_batch_approve_claims_partial_failure(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        c1 = _create_claim_with_section(session, system.id, "C1", "results")
        session.commit()
        system_id = system.id
        c1_id = c1.id

    response = client.post(
        f"/api/systems/{system_id}/claims/batch-approve",
        json={"claimIds": [c1_id, "nonexistent-id"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["succeeded"] == [c1_id]
    assert len(body["data"]["failed"]) == 1
    assert body["data"]["failed"][0]["claimId"] == "nonexistent-id"


def test_batch_approve_claims_empty_input(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.commit()
        system_id = system.id

    response = client.post(
        f"/api/systems/{system_id}/claims/batch-approve",
        json={"claimIds": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["succeeded"] == []
    assert body["data"]["failed"] == []


def test_batch_approve_claims_wrong_system(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system1 = _create_system(session, project_id=project.id, system_no=1)
        system2 = _create_system(session, project_id=project.id, system_no=2)
        c1 = _create_claim_with_section(session, system1.id, "C1", "results")
        session.commit()
        system2_id = system2.id
        c1_id = c1.id

    response = client.post(
        f"/api/systems/{system2_id}/claims/batch-approve",
        json={"claimIds": [c1_id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["succeeded"] == []
    assert len(body["data"]["failed"]) == 1
