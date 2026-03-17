from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from io import BytesIO
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
    AssetManifest,
    AssetMetadata,
    Claim,
    ClaimEvidenceLink,
    ExperimentalSystem,
    FigurePlan,
    FigurePlanAsset,
    G4Snapshot,
    Outline,
    Project,
    ProjectMember,
    ProjectMemberRole,
    SystemSection,
    WorkflowEvent,
    WorkflowInstance,
)
from app.persistence.models.skeleton import StructureSkeleton

ALL_TABLES = [
    Project.__table__,
    ProjectMember.__table__,
    ExperimentalSystem.__table__,
    SystemSection.__table__,
    StructureSkeleton.__table__,
    Asset.__table__,
    AssetMetadata.__table__,
    AssetManifest.__table__,
    AnalysisRun.__table__,
    FigurePlan.__table__,
    FigurePlanAsset.__table__,
    Claim.__table__,
    ClaimEvidenceLink.__table__,
    Outline.__table__,
    G4Snapshot.__table__,
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


def _create_confirmed_skeleton(
    session: Session,
    *,
    system_id: str,
    version: int = 1,
    figure_framework: list | None = None,
) -> StructureSkeleton:
    skeleton = StructureSkeleton(
        system_id=system_id,
        version=version,
        skeleton_json={
            "sections": [{"key": "sec1", "title": "Section 1"}],
            "figure_framework": figure_framework or [
                {"figure_id": "fig1", "title": "Figure 1", "type": "chart", "purpose": "Test", "related_sections": ["sec1"]},
            ],
        },
        source_asset_ids=[],
        status="confirmed",
        confirmed_at=datetime.now(UTC),
    )
    session.add(skeleton)
    session.flush()
    return skeleton


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


def _create_figure_plan(
    session: Session,
    *,
    system_id: str,
    figure_no: str = "fig1",
    title: str = "Figure 1",
    claim_text: str = "test",
    status: str = "pending",
    section_key: str | None = None,
) -> FigurePlan:
    plan = FigurePlan(
        system_id=system_id,
        figure_no=figure_no,
        title=title,
        claim_text=claim_text,
        status=status,
        section_key=section_key,
    )
    session.add(plan)
    session.flush()
    return plan




def test_generate_figure_plan_returns_accepted(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _create_confirmed_skeleton(session, system_id=system.id)
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
    assert plans[0].figure_no == "fig1"
    assert plans[0].version == 1
    assert plans[0].status == "pending"
    assert plans[0].section_key == "sec1"
    assert plans[0].skeleton_version == 1
    assert workflow.status == TaskStatus.SUCCEEDED.value
    assert [event.event_type for event in events] == [EventType.TASK_CREATED.value, EventType.TASK_SUCCEEDED.value]

    list_response = client.get(f"/api/systems/{system_id}/figure-plans")
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["success"] is True
    assert len(list_body["data"]) == 1
    assert list_body["data"][0]["figureNo"] == "fig1"
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


def test_patch_figure_plan_updates_fields(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.add(
            SystemSection(system_id=system.id, section_key="results", title="Results", order_no=1)
        )
        plan = FigurePlan(
            system_id=system.id,
            figure_no="fig1",
            title="Original title",
            claim_text="Original claim",
            status="pending",
            data_needed_json=[{"kind": "raw"}],
            method_json={"mode": "initial"},
            acceptance_criteria_json=[{"type": "status", "value": "confirmed"}],
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id

    response = client.patch(
        f"/api/figure-plans/{plan_id}",
        json={
            "figureNo": "fig1-updated",
            "title": "Updated title",
            "claimText": "Updated claim",
            "sectionKey": "results",
            "briefText": "Updated brief",
            "dataNeededJson": [{"kind": "processed"}],
            "methodJson": {"mode": "manual"},
            "acceptanceCriteriaJson": [{"type": "note", "value": "ok"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["figureNo"] == "fig1-updated"
    assert body["data"]["title"] == "Updated title"
    assert body["data"]["claimText"] == "Updated claim"
    assert body["data"]["sectionKey"] == "results"
    assert body["data"]["briefText"] == "Updated brief"
    assert body["data"]["dataNeededJson"] == [{"kind": "processed"}]
    assert body["data"]["methodJson"] == {"mode": "manual"}
    assert body["data"]["acceptanceCriteriaJson"] == [{"type": "note", "value": "ok"}]

    with Session(engine) as session:
        updated = session.get(FigurePlan, plan_id)

    assert updated is not None
    assert updated.figure_no == "fig1-updated"
    assert updated.title == "Updated title"
    assert updated.claim_text == "Updated claim"
    assert updated.section_key == "results"
    assert updated.brief_text == "Updated brief"
    assert updated.data_needed_json == [{"kind": "processed"}]
    assert updated.method_json == {"mode": "manual"}
    assert updated.acceptance_criteria_json == [{"type": "note", "value": "ok"}]


def test_patch_figure_plan_rejects_invalid_section_key(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.add(
            SystemSection(system_id=system.id, section_key="results", title="Results", order_no=1)
        )
        plan = FigurePlan(
            system_id=system.id,
            figure_no="fig1",
            title="Fig 1",
            claim_text="test",
            status="pending",
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id

    response = client.patch(
        f"/api/figure-plans/{plan_id}",
        json={"sectionKey": "discussion"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "Figure plan section_key is not defined for this system"


def test_delete_figure_plan_returns_204(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        plan = FigurePlan(
            system_id=system.id,
            figure_no="fig1",
            title="Fig 1",
            claim_text="test",
            status="pending",
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id

    response = client.delete(f"/api/figure-plans/{plan_id}")

    assert response.status_code == 204
    assert response.content == b""

    with Session(engine) as session:
        deleted = session.get(FigurePlan, plan_id)

    assert deleted is None


def test_delete_figure_plan_returns_404_for_missing_plan(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        _create_system(session, project_id=project.id)
        session.commit()

    response = client.delete("/api/figure-plans/missing-plan-id")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "Figure plan not found"


# ---------------------------------------------------------------------------
# FigurePlan assets
# ---------------------------------------------------------------------------


def test_upload_figure_plan_asset_creates_binding_and_asset_metadata(
    client: TestClient,
    engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_upload = lambda *_args, **_kwargs: "uploads/plan-asset.png"
    monkeypatch.setattr("app.modules.evidence.service.upload_fileobj", fake_upload, raising=False)
    monkeypatch.setattr("app.modules.assets.service.upload_fileobj", fake_upload, raising=False)
    monkeypatch.setattr(
        "app.modules.evidence.service.generate_presigned_url",
        lambda storage_key, expires=3600: f"https://example.test/{storage_key}?expires={expires}",
    )

    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        plan = _create_figure_plan(session, system_id=system.id)
        session.commit()
        plan_id = plan.id

    response = client.post(
        f"/api/figure-plans/{plan_id}/assets",
        data={"role": "source_image"},
        files={"file": ("microscopy.png", BytesIO(b"binary-image"), "image/png")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["figurePlanId"] == plan_id
    assert body["data"]["role"] == "source_image"
    assert body["data"]["position"] == 0
    assert body["data"]["fileName"] == "microscopy.png"
    assert body["data"]["mimeType"] == "image/png"
    assert body["data"]["previewUrl"] == "https://example.test/uploads/plan-asset.png?expires=3600"

    with Session(engine) as session:
        binding = session.scalars(select(FigurePlanAsset)).one()
        asset = session.scalars(select(Asset)).one()
        metadata = session.scalars(select(AssetMetadata)).one()

    assert binding.figure_plan_id == plan_id
    assert binding.asset_id == asset.id
    assert asset.asset_type == "image"
    assert asset.storage_key == "uploads/plan-asset.png"
    assert metadata.asset_id == asset.id
    assert metadata.qc_status == "pending"


def test_upload_figure_plan_asset_rejects_non_image_file(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        plan = _create_figure_plan(session, system_id=system.id)
        session.commit()
        plan_id = plan.id

    response = client.post(
        f"/api/figure-plans/{plan_id}/assets",
        data={"role": "source_image"},
        files={"file": ("notes.txt", BytesIO(b"not-an-image"), "text/plain")},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "Only image files are allowed"


def test_upload_figure_plan_asset_rejects_file_larger_than_10mb(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        plan = _create_figure_plan(session, system_id=system.id)
        session.commit()
        plan_id = plan.id

    response = client.post(
        f"/api/figure-plans/{plan_id}/assets",
        data={"role": "source_image"},
        files={"file": ("too-large.png", BytesIO(b"x" * (10 * 1024 * 1024 + 1)), "image/png")},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "File size exceeds 10MB limit"


def test_delete_figure_plan_asset_requires_matching_plan(
    client: TestClient,
    engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.modules.evidence.service.generate_presigned_url", lambda *_args, **_kwargs: "https://example.test/preview")

    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        other_system = ExperimentalSystem(
            project_id=project.id,
            system_no=2,
            title="Other system",
            status=SystemState.DRAFT.value,
        )
        session.add(other_system)
        session.flush()
        owner_plan = _create_figure_plan(session, system_id=system.id, figure_no="fig1")
        foreign_plan = _create_figure_plan(session, system_id=other_system.id, figure_no="fig2")
        asset = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="image",
            file_name="asset.png",
            storage_key="uploads/asset.png",
            uploaded_by="owner-1",
        )
        session.add(asset)
        session.flush()
        binding = FigurePlanAsset(
            figure_plan_id=owner_plan.id,
            asset_id=asset.id,
            role="source_image",
            position=0,
        )
        session.add(binding)
        session.commit()
        owner_plan_id = owner_plan.id
        foreign_plan_id = foreign_plan.id
        binding_id = binding.id

    wrong_plan_response = client.delete(f"/api/figure-plans/{foreign_plan_id}/assets/{binding_id}")

    assert wrong_plan_response.status_code == 403
    wrong_plan_body = wrong_plan_response.json()
    assert wrong_plan_body["success"] is False
    assert wrong_plan_body["error"] == "Binding does not belong to this plan"

    with Session(engine) as session:
        still_exists = session.get(FigurePlanAsset, binding_id)

    assert still_exists is not None
    assert still_exists.figure_plan_id == owner_plan_id

    delete_response = client.delete(f"/api/figure-plans/{owner_plan_id}/assets/{binding_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    with Session(engine) as session:
        deleted = session.get(FigurePlanAsset, binding_id)

    assert deleted is None


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
        _create_confirmed_skeleton(session, system_id=system.id)
        plan_one = _create_figure_plan(
            session,
            system_id=system.id,
            figure_no="fig1",
            title="Figure 1",
            status="confirmed",
            section_key="results",
        )
        plan_two = _create_figure_plan(
            session,
            system_id=system.id,
            figure_no="fig2",
            title="Figure 2",
            status="confirmed",
            section_key="discussion",
        )
        asset_one = _create_asset_with_analysis(
            session,
            project_id=project.id,
            system_id=system.id,
            file_name="fig-1.png",
            storage_key="uploads/fig-1.png",
        )
        asset_two = _create_asset_with_analysis(
            session,
            project_id=project.id,
            system_id=system.id,
            file_name="fig-2.png",
            storage_key="uploads/fig-2.png",
        )
        session.add_all(
            [
                FigurePlanAsset(
                    figure_plan_id=plan_one.id,
                    asset_id=asset_one.id,
                    role="source_image",
                    position=0,
                ),
                FigurePlanAsset(
                    figure_plan_id=plan_two.id,
                    asset_id=asset_two.id,
                    role="source_image",
                    position=0,
                ),
            ]
        )
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

    assert [claim.claim_id for claim in claims] == ["Sdiscussion-Ffig2-1", "Sresults-Ffig1-1"]
    assert {claim.section_ref for claim in claims} == {"results", "discussion"}
    assert all(claim.status == "draft" for claim in claims)
    assert len(links) == 2
    assert workflow.status == TaskStatus.SUCCEEDED.value
    assert [event.event_type for event in events] == [EventType.TASK_CREATED.value, EventType.TASK_SUCCEEDED.value]

    list_response = client.get(f"/api/systems/{system_id}/claims")
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["success"] is True
    assert [item["claimId"] for item in list_body["data"]] == ["Sdiscussion-Ffig2-1", "Sresults-Ffig1-1"]


def test_generate_evidence_matrix_deduplicates_repeated_plan_assets_without_rolling_back(
    client: TestClient, engine,
) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(
            session,
            project_id=project.id,
            status=SystemState.ASSETS_CONFIRMED.value,
        )
        session.add(SystemSection(system_id=system.id, section_key="results", title="Results", order_no=1))
        _create_confirmed_skeleton(session, system_id=system.id)
        plan = _create_figure_plan(
            session,
            system_id=system.id,
            figure_no="fig1",
            title="Figure 1",
            status="confirmed",
            section_key="results",
        )
        asset = _create_asset_with_analysis(
            session,
            project_id=project.id,
            system_id=system.id,
            file_name="fig-1.png",
            storage_key="uploads/fig-1.png",
        )
        session.add_all(
            [
                FigurePlanAsset(
                    figure_plan_id=plan.id,
                    asset_id=asset.id,
                    role="source_image",
                    position=0,
                ),
                FigurePlanAsset(
                    figure_plan_id=plan.id,
                    asset_id=asset.id,
                    role="annotated_image",
                    position=1,
                ),
            ]
        )
        session.commit()
        system_id = system.id

    response = client.post(f"/api/systems/{system_id}/evidence-matrix/generate", json={})

    assert response.status_code == 202
    body = response.json()
    workflow_id = body["data"]["handle"]["workflow_id"]
    assert workflow_id is not None

    _wait_for_evidence_matrix_completion(engine, workflow_id, system_id, expected_claim_count=1)

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

    assert [claim.claim_id for claim in claims] == ["Sresults-Ffig1-1"]
    assert len(links) == 1


def test_generate_evidence_matrix_rejects_regeneration_when_latest_claim_or_outline_is_confirmed(
    client: TestClient, engine,
) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(
            session,
            project_id=project.id,
            status=SystemState.ASSETS_CONFIRMED.value,
        )
        session.add(SystemSection(system_id=system.id, section_key="results", title="Results", order_no=1))
        _create_confirmed_skeleton(session, system_id=system.id)
        _create_figure_plan(
            session,
            system_id=system.id,
            figure_no="fig1",
            title="Figure 1",
            status="confirmed",
            section_key="results",
        )
        session.add(
            Claim(
                system_id=system.id,
                claim_id="claim-1",
                statement="already approved latest claim",
                section_ref="results",
                status="approved",
                version=1,
            )
        )
        session.add(
            Outline(
                system_id=system.id,
                version=1,
                outline_json={"sections": []},
                generated_from_claims_json=[],
                status="confirmed",
            )
        )
        session.commit()
        system_id = system.id

    response = client.post(f"/api/systems/{system_id}/evidence-matrix/generate", json={})

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["data"]["code"] == "evidence_matrix_regeneration_conflict"
    assert body["data"]["details"]["approved_latest_claim_count"] == 1
    assert body["data"]["details"]["confirmed_outline_count"] == 1
    assert body["data"]["details"]["sections_affected"] == ["results"]
    assert body["data"]["details"]["force_regenerate"] is False


def test_generate_evidence_matrix_allows_force_regeneration_even_when_latest_claim_or_outline_exists(
    client: TestClient, engine,
) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(
            session,
            project_id=project.id,
            status=SystemState.ASSETS_CONFIRMED.value,
        )
        session.add(SystemSection(system_id=system.id, section_key="results", title="Results", order_no=1))
        _create_confirmed_skeleton(session, system_id=system.id)
        plan = _create_figure_plan(
            session,
            system_id=system.id,
            figure_no="fig1",
            title="Figure 1",
            status="confirmed",
            section_key="results",
        )
        asset = _create_asset_with_analysis(session, project_id=project.id, system_id=system.id)
        session.add(
            FigurePlanAsset(
                figure_plan_id=plan.id,
                asset_id=asset.id,
                role="source_image",
                position=0,
            )
        )
        session.add(
            Claim(
                system_id=system.id,
                claim_id="claim-1",
                statement="already approved latest claim",
                section_ref="results",
                status="approved",
                version=1,
            )
        )
        session.add(
            Outline(
                system_id=system.id,
                version=1,
                outline_json={"sections": []},
                generated_from_claims_json=[],
                status="confirmed",
            )
        )
        session.commit()
        system_id = system.id

    response = client.post(
        f"/api/systems/{system_id}/evidence-matrix/generate",
        json={"forceRegenerate": True},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    handle = body["data"]["handle"]
    workflow_id = handle["workflow_id"]
    assert workflow_id is not None
    assert body["data"]["invalidationSummary"] == {
        "approvedLatestClaimCount": 1,
        "confirmedOutlineCount": 1,
        "sectionsAffected": ["results"],
        "willInvalidateClaimApprovals": True,
        "willInvalidateOutlines": True,
    }

    _wait_for_evidence_matrix_completion(engine, workflow_id, system_id, expected_claim_count=2)


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


def test_list_image_analyses_returns_assets_and_latest_succeeded_run(
    client: TestClient,
    engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.modules.evidence.service.generate_presigned_url",
        lambda storage_key, expires=3600: f"https://example.test/{storage_key}?expires={expires}",
    )

    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        plan_one = _create_figure_plan(
            session,
            system_id=system.id,
            figure_no="fig1",
            title="Figure 1",
        )
        plan_two = _create_figure_plan(
            session,
            system_id=system.id,
            figure_no="fig2",
            title="Figure 2",
        )
        asset_one = _create_asset_with_analysis(
            session,
            project_id=project.id,
            system_id=system.id,
            file_name="fig-1.png",
            storage_key="uploads/fig-1.png",
        )
        asset_two = _create_asset_with_analysis(
            session,
            project_id=project.id,
            system_id=system.id,
            file_name="fig-2.png",
            storage_key="uploads/fig-2.png",
        )
        session.add_all(
            [
                FigurePlanAsset(
                    figure_plan_id=plan_one.id,
                    asset_id=asset_one.id,
                    role="source_image",
                    position=0,
                ),
                FigurePlanAsset(
                    figure_plan_id=plan_two.id,
                    asset_id=asset_two.id,
                    role="source_image",
                    position=0,
                ),
            ]
        )
        session.flush()
        older_run = AnalysisRun(
            system_id=system.id,
            figure_plan_id=plan_one.id,
            asset_id=asset_one.id,
            run_type="image_analysis",
            analysis_type="comprehensive",
            status=TaskStatus.SUCCEEDED.value,
            summary="Older run",
            result_payload_json={"confidence": 0.41},
            started_at=datetime(2026, 3, 14, tzinfo=UTC),
        )
        latest_run = AnalysisRun(
            system_id=system.id,
            figure_plan_id=plan_one.id,
            asset_id=asset_one.id,
            run_type="image_analysis",
            analysis_type="comprehensive",
            status=TaskStatus.SUCCEEDED.value,
            summary="Strong signal detected",
            result_payload_json={"confidence": 0.93},
            started_at=datetime(2026, 3, 15, tzinfo=UTC),
        )
        session.add_all([older_run, latest_run])
        session.flush()
        older_run.created_at = datetime(2026, 3, 14, tzinfo=UTC)
        older_run.updated_at = datetime(2026, 3, 14, tzinfo=UTC)
        latest_run.created_at = datetime(2026, 3, 15, tzinfo=UTC)
        latest_run.updated_at = datetime(2026, 3, 15, tzinfo=UTC)
        session.commit()
        system_id = system.id
        asset_one_id = asset_one.id
        latest_run_id = latest_run.id

    response = client.get(f"/api/systems/{system_id}/image-analyses")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] == 2
    assert body["data"]["analyzed"] == 1
    assert body["data"]["pending"] == 1
    assert [item["figureNo"] for item in body["data"]["items"]] == ["fig1", "fig2"]
    assert body["data"]["items"][0]["assets"][0]["id"] == asset_one_id
    assert body["data"]["items"][0]["assets"][0]["fileName"] == "fig-1.png"
    assert body["data"]["items"][0]["assets"][0]["previewUrl"] == "https://example.test/uploads/fig-1.png?expires=3600"
    assert body["data"]["items"][0]["latestAnalysis"]["id"] == latest_run_id
    assert body["data"]["items"][0]["latestAnalysis"]["summary"] == "Strong signal detected"
    assert body["data"]["items"][0]["latestAnalysis"]["confidence"] == 0.93
    assert body["data"]["items"][1]["latestAnalysis"] is None


def test_trigger_figure_plan_analysis_creates_queued_run(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        plan = _create_figure_plan(session, system_id=system.id)
        asset = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="image",
            file_name="analysis.png",
            storage_key="uploads/analysis.png",
            uploaded_by="owner-1",
        )
        session.add(asset)
        session.flush()
        session.add(
            FigurePlanAsset(
                figure_plan_id=plan.id,
                asset_id=asset.id,
                role="source_image",
                position=0,
            )
        )
        session.commit()
        plan_id = plan.id
        asset_id = asset.id

    response = client.post(
        f"/api/figure-plans/{plan_id}/analyze",
        json={"assetId": asset_id, "analysisType": "comprehensive"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == TaskStatus.QUEUED.value
    assert body["data"]["summary"] is None

    with Session(engine) as session:
        run = session.scalars(select(AnalysisRun).where(AnalysisRun.asset_id == asset_id)).one()

    assert run.figure_plan_id == plan_id
    assert run.analysis_type == "comprehensive"
    assert run.status == TaskStatus.QUEUED.value
    assert run.run_type == "image_analysis"


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
