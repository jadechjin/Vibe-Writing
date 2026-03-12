from __future__ import annotations

import time
from collections.abc import Generator
from pathlib import Path
from tempfile import NamedTemporaryFile

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
    ExperimentalSystem,
    Project,
    ProjectMember,
    ProjectMemberRole,
    WorkflowEvent,
    WorkflowInstance,
)

ALL_TABLES = [
    Project.__table__,
    ProjectMember.__table__,
    ExperimentalSystem.__table__,
    Asset.__table__,
    AssetMetadata.__table__,
    AssetManifest.__table__,
    AnalysisRun.__table__,
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
    project = Project(name="Assets Project", owner_id=owner_id)
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
    status: str = SystemState.FIGURE_PLAN_READY.value,
) -> ExperimentalSystem:
    system = ExperimentalSystem(
        project_id=project_id,
        system_no=1,
        title=title,
        status=status,
    )
    session.add(system)
    session.flush()
    return system


def _wait_for_manifest_completion(engine, workflow_id: str, system_id: str, *, expected_manifest_count: int) -> None:
    for _ in range(50):
        with Session(engine) as session:
            workflow = session.get(WorkflowInstance, workflow_id)
            manifests = session.scalars(
                select(AssetManifest).where(AssetManifest.system_id == system_id).order_by(AssetManifest.version.asc())
            ).all()
            if (
                workflow is not None
                and workflow.status == TaskStatus.SUCCEEDED.value
                and len(manifests) == expected_manifest_count
            ):
                return
        time.sleep(0.01)

    raise AssertionError("Manifest generation did not complete in time")


def test_upload_asset_creates_asset_and_initial_metadata(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.commit()
        system_id = system.id

    response = client.post(
        "/api/assets/upload",
        json={
            "systemId": system_id,
            "assetType": "figure",
            "fileName": " figure-1.png ",
            "storageKey": " uploads/figure-1.png ",
            "mimeType": " image/png ",
            "uploadedBy": " owner-1 ",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["fileName"] == "figure-1.png"
    assert body["data"]["storageKey"] == "uploads/figure-1.png"
    assert body["data"]["metadataEntry"]["qcStatus"] == "pending"

    with Session(engine) as session:
        asset = session.scalars(select(Asset)).one()
        metadata = session.scalars(select(AssetMetadata)).one()
        system = session.get(ExperimentalSystem, system_id)

    assert asset.system_id == system_id
    assert metadata.asset_id == asset.id
    assert metadata.qc_status == "pending"
    assert system is not None
    assert system.status == SystemState.DATA_UPLOADED.value


def test_upload_asset_returns_404_for_missing_system(client: TestClient) -> None:
    response = client.post(
        "/api/assets/upload",
        json={
            "systemId": "missing-system",
            "assetType": "figure",
            "fileName": "figure-1.png",
            "storageKey": "uploads/figure-1.png",
            "uploadedBy": "owner-1",
        },
    )

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_get_asset_detail_returns_metadata(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        asset = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="table",
            file_name="table-1.csv",
            storage_key="uploads/table-1.csv",
            uploaded_by="owner-1",
        )
        session.add(asset)
        session.flush()
        session.add(
            AssetMetadata(
                asset_id=asset.id,
                semantic_description="Original semantic description",
                qc_status="confirmed",
            )
        )
        session.commit()
        asset_id = asset.id

    response = client.get(f"/api/assets/{asset_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"] == asset_id
    assert body["data"]["metadataEntry"]["semanticDescription"] == "Original semantic description"
    assert body["data"]["metadataEntry"]["qcStatus"] == "confirmed"


def test_list_system_assets_returns_all_assets_with_metadata(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        asset_one = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="figure",
            file_name="figure-1.png",
            storage_key="uploads/figure-1.png",
            uploaded_by="owner-1",
        )
        asset_two = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="raw_data",
            file_name="raw-1.csv",
            storage_key="uploads/raw-1.csv",
            uploaded_by="owner-1",
        )
        session.add_all([asset_one, asset_two])
        session.flush()
        session.add_all(
            [
                AssetMetadata(asset_id=asset_one.id, qc_status="pending"),
                AssetMetadata(asset_id=asset_two.id, semantic_description="Raw source", qc_status="confirmed"),
            ]
        )
        session.commit()

        system_id = system.id

    response = client.get(f"/api/systems/{system_id}/assets")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 2
    names = [item["fileName"] for item in body["data"]]
    assert names == ["figure-1.png", "raw-1.csv"]


def test_bind_asset_updates_metadata_and_validates_analysis_run_scope(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        other_system = ExperimentalSystem(project_id=project.id, system_no=2, title="System 2")
        session.add(other_system)
        session.flush()

        asset = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="figure",
            file_name="figure-1.png",
            storage_key="uploads/figure-1.png",
            uploaded_by="owner-1",
        )
        session.add(asset)
        session.flush()
        session.add(AssetMetadata(asset_id=asset.id, qc_status="pending"))
        valid_run = AnalysisRun(
            system_id=system.id,
            asset_id=asset.id,
            run_type="vision",
            status=TaskStatus.SUCCEEDED.value,
        )
        foreign_run = AnalysisRun(
            system_id=other_system.id,
            asset_id=None,
            run_type="vision",
            status=TaskStatus.SUCCEEDED.value,
        )
        running_run = AnalysisRun(
            system_id=system.id,
            asset_id=asset.id,
            run_type="vision",
            status=TaskStatus.RUNNING.value,
        )
        session.add_all([valid_run, foreign_run, running_run])
        session.commit()
        asset_id = asset.id
        foreign_run_id = foreign_run.id
        valid_run_id = valid_run.id
        running_run_id = running_run.id

    response = client.post(
        f"/api/assets/{asset_id}/bind",
        json={
            "semanticDescription": " Quantified microscopy signal ",
            "sourceDescription": " Experiment A ",
            "instrumentInfo": " Leica SP8 ",
            "sampleIds": [" sample-1 ", "sample-2"],
            "conditionsJson": {"temperature": "37C"},
            "qcStatus": " confirmed ",
            "analysisRunId": valid_run_id,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["metadataEntry"]["semanticDescription"] == "Quantified microscopy signal"
    assert body["data"]["metadataEntry"]["sourceDescription"] == "Experiment A"
    assert body["data"]["metadataEntry"]["instrumentInfo"] == "Leica SP8"
    assert body["data"]["metadataEntry"]["sampleIds"] == ["sample-1", "sample-2"]
    assert body["data"]["metadataEntry"]["qcStatus"] == "confirmed"

    with Session(engine) as session:
        metadata = session.scalars(select(AssetMetadata).where(AssetMetadata.asset_id == asset_id)).one()
    assert metadata.semantic_description == "Quantified microscopy signal"
    assert metadata.qc_status == "confirmed"

    invalid_response = client.post(
        f"/api/assets/{asset_id}/bind",
        json={
            "semanticDescription": "Still valid",
            "qcStatus": "approved",
            "analysisRunId": foreign_run_id,
        },
    )

    assert invalid_response.status_code == 409
    invalid_body = invalid_response.json()
    assert invalid_body["success"] is False
    assert invalid_body["data"]["code"] == "conflict"

    running_response = client.post(
        f"/api/assets/{asset_id}/bind",
        json={
            "semanticDescription": "Still valid",
            "qcStatus": "approved",
            "analysisRunId": running_run_id,
        },
    )

    assert running_response.status_code == 409
    running_body = running_response.json()
    assert running_body["success"] is False
    assert running_body["data"]["code"] == "conflict"


def test_manifest_create_returns_queued_handle_then_persists_manifest(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id, status=SystemState.ANALYSIS_READY.value)
        asset = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="figure",
            file_name="figure-1.png",
            storage_key="uploads/figure-1.png",
            uploaded_by="owner-1",
        )
        session.add(asset)
        session.flush()
        session.add(
            AssetMetadata(
                asset_id=asset.id,
                semantic_description="Microscopy asset",
                qc_status="confirmed",
            )
        )
        session.add(
            AnalysisRun(
                system_id=system.id,
                asset_id=asset.id,
                run_type="vision",
                status=TaskStatus.SUCCEEDED.value,
            )
        )
        session.commit()
        system_id = system.id

    response = client.post(
        f"/api/systems/{system_id}/manifest",
        json={"status": "confirmed"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    handle = body["data"]["handle"]
    workflow_id = handle["workflow_id"]
    assert workflow_id is not None
    assert handle["job_id"].startswith(f"manifest_generate:{system_id}:")
    assert handle["status"] == TaskStatus.QUEUED.value

    with Session(engine) as session:
        workflow = session.scalars(
            select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
        ).one()
        events = session.scalars(
            select(WorkflowEvent).where(WorkflowEvent.instance_id == workflow.id).order_by(WorkflowEvent.created_at.asc())
        ).all()

    assert workflow.workflow_key == "manifest_generate"
    assert workflow.status == TaskStatus.QUEUED.value
    assert [event.event_type for event in events] == [EventType.TASK_CREATED.value]

    _wait_for_manifest_completion(engine, workflow_id, system_id, expected_manifest_count=1)

    with Session(engine) as session:
        manifests = session.scalars(
            select(AssetManifest).where(AssetManifest.system_id == system_id).order_by(AssetManifest.version.asc())
        ).all()
        workflow = session.scalars(
            select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
        ).one()
        events = session.scalars(
            select(WorkflowEvent).where(WorkflowEvent.instance_id == workflow.id).order_by(WorkflowEvent.created_at.asc())
        ).all()

    assert len(manifests) == 1
    assert manifests[0].status == "confirmed"
    assert manifests[0].version == 1
    assert manifests[0].manifest_json["assetCount"] == 1
    assert workflow.status == TaskStatus.SUCCEEDED.value
    assert [event.event_type for event in events] == [EventType.TASK_CREATED.value, EventType.TASK_SUCCEEDED.value]

    latest_response = client.get(f"/api/systems/{system_id}/manifest")
    assert latest_response.status_code == 200
    latest_body = latest_response.json()
    assert latest_body["data"]["status"] == "confirmed"
    assert latest_body["data"]["version"] == 1


def test_manifest_create_requires_g2_readiness(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id, status=SystemState.DATA_UPLOADED.value)
        asset = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="figure",
            file_name="figure-1.png",
            storage_key="uploads/figure-1.png",
            uploaded_by="owner-1",
        )
        session.add(asset)
        session.flush()
        session.add(AssetMetadata(asset_id=asset.id, semantic_description="Ready", qc_status="approved"))
        session.commit()
        system_id = system.id

    response = client.post(f"/api/systems/{system_id}/manifest", json={"status": "approved"})

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "System is not ready for manifest generation"
    assert body["data"]["code"] == "conflict"
    assert body["data"]["details"]["gate"] == "G2"
    assert len(body["data"]["details"]["blockers"]) == 1
    assert body["data"]["details"]["blockers"][0]["code"] == "analysis_not_ready"

    with Session(engine) as session:
        manifests = session.scalars(
            select(AssetManifest).where(AssetManifest.system_id == system_id).order_by(AssetManifest.version.asc())
        ).all()
        workflows = session.scalars(select(WorkflowInstance).where(WorkflowInstance.system_id == system_id)).all()

    assert manifests == []
    assert workflows == []


def test_manifest_create_increments_version_and_requires_assets(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        empty_system = _create_system(session, project_id=project.id, title="Empty System")
        system = ExperimentalSystem(
            project_id=project.id,
            system_no=2,
            title="Manifest System",
            status=SystemState.ANALYSIS_READY.value,
        )
        session.add(system)
        session.flush()
        asset = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="figure",
            file_name="figure-1.png",
            storage_key="uploads/figure-1.png",
            uploaded_by="owner-1",
        )
        session.add(asset)
        session.flush()
        session.add(AssetMetadata(asset_id=asset.id, semantic_description="Ready", qc_status="approved"))
        session.add(
            AnalysisRun(
                system_id=system.id,
                asset_id=asset.id,
                run_type="vision",
                status=TaskStatus.SUCCEEDED.value,
            )
        )
        session.add(
            AssetManifest(
                project_id=project.id,
                system_id=system.id,
                version=1,
                status="draft",
                manifest_json={"assetCount": 1},
            )
        )
        session.commit()
        empty_system_id = empty_system.id
        system_id = system.id

    missing_assets = client.post(f"/api/systems/{empty_system_id}/manifest", json={"status": "draft"})
    assert missing_assets.status_code == 409
    assert missing_assets.json()["data"]["code"] == "conflict"

    create_second = client.post(f"/api/systems/{system_id}/manifest", json={"status": "approved"})
    assert create_second.status_code == 202

    with Session(engine) as session:
        workflow = session.scalars(
            select(WorkflowInstance)
            .where(WorkflowInstance.system_id == system_id)
            .order_by(WorkflowInstance.version.desc())
        ).first()

    assert workflow is not None

    _wait_for_manifest_completion(engine, workflow.id, system_id, expected_manifest_count=2)

    with Session(engine) as session:
        manifests = session.scalars(
            select(AssetManifest).where(AssetManifest.system_id == system_id).order_by(AssetManifest.version.asc())
        ).all()

    assert [manifest.version for manifest in manifests] == [1, 2]
    assert manifests[-1].status == "approved"


def test_upload_asset_reverts_downstream_state_to_analysis_ready(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(
            session,
            project_id=project.id,
            status=SystemState.ASSETS_CONFIRMED.value,
        )
        session.commit()
        system_id = system.id

    response = client.post(
        "/api/assets/upload",
        json={
            "systemId": system_id,
            "assetType": "figure",
            "fileName": "figure-2.png",
            "storageKey": "uploads/figure-2.png",
            "uploadedBy": "owner-1",
        },
    )

    assert response.status_code == 201

    with Session(engine) as session:
        system = session.get(ExperimentalSystem, system_id)

    assert system is not None
    assert system.status == SystemState.ANALYSIS_READY.value


def test_bind_asset_reverts_downstream_state_to_analysis_ready(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(
            session,
            project_id=project.id,
            status=SystemState.ASSETS_CONFIRMED.value,
        )
        asset = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="figure",
            file_name="figure-1.png",
            storage_key="uploads/figure-1.png",
            uploaded_by="owner-1",
        )
        session.add(asset)
        session.flush()
        session.add(
            AssetMetadata(
                asset_id=asset.id,
                semantic_description="Confirmed asset",
                qc_status="confirmed",
            )
        )
        session.commit()
        asset_id = asset.id
        system_id = system.id

    response = client.post(
        f"/api/assets/{asset_id}/bind",
        json={
            "semanticDescription": "Updated description",
            "qcStatus": "approved",
        },
    )

    assert response.status_code == 200

    with Session(engine) as session:
        system = session.get(ExperimentalSystem, system_id)

    assert system is not None
    assert system.status == SystemState.ANALYSIS_READY.value


# ---------------------------------------------------------------------------
# Batch confirm asset QC tests
# ---------------------------------------------------------------------------


def _create_asset_with_metadata(
    session: Session,
    project_id: str,
    system_id: str,
    file_name: str = "fig.png",
    qc_status: str = "pending",
) -> tuple[Asset, AssetMetadata]:
    asset = Asset(
        project_id=project_id,
        system_id=system_id,
        asset_type="figure",
        file_name=file_name,
        storage_key=f"uploads/{file_name}",
        uploaded_by="owner-1",
    )
    session.add(asset)
    session.flush()
    metadata = AssetMetadata(asset_id=asset.id, qc_status=qc_status)
    session.add(metadata)
    session.flush()
    return asset, metadata


def test_batch_confirm_asset_qc_all_succeed(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        a1, _ = _create_asset_with_metadata(session, project.id, system.id, "fig1.png")
        a2, _ = _create_asset_with_metadata(session, project.id, system.id, "fig2.png")
        session.commit()
        system_id = system.id
        a1_id, a2_id = a1.id, a2.id

    response = client.post(
        f"/api/systems/{system_id}/assets/batch-confirm-qc",
        json={"assetIds": [a1_id, a2_id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert set(body["data"]["succeeded"]) == {a1_id, a2_id}
    assert body["data"]["failed"] == []


def test_batch_confirm_asset_qc_missing_metadata(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        asset = Asset(
            project_id=project.id,
            system_id=system.id,
            asset_type="figure",
            file_name="no-meta.png",
            storage_key="uploads/no-meta.png",
            uploaded_by="owner-1",
        )
        session.add(asset)
        session.commit()
        system_id = system.id
        asset_id = asset.id

    response = client.post(
        f"/api/systems/{system_id}/assets/batch-confirm-qc",
        json={"assetIds": [asset_id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["succeeded"] == []
    assert len(body["data"]["failed"]) == 1
    assert "metadata" in body["data"]["failed"][0]["error"].lower()


def test_batch_confirm_asset_qc_empty_input(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.commit()
        system_id = system.id

    response = client.post(
        f"/api/systems/{system_id}/assets/batch-confirm-qc",
        json={"assetIds": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["succeeded"] == []
    assert body["data"]["failed"] == []
