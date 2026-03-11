from __future__ import annotations

import time
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.common.enums import EventType, SystemState, TaskStatus
from app.common.errors import ErrorCode
from app.main import create_app
from app.persistence import get_db_session
from app.persistence.base import Base
from app.persistence.models import (
    Asset,
    AssetMetadata,
    Claim,
    ExperimentalSystem,
    Outline,
    OutlineAssetBinding,
    Project,
    ProjectMember,
    ProjectMemberRole,
    ReviewComment,
    SectionDraft,
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
    Claim.__table__,
    Outline.__table__,
    OutlineAssetBinding.__table__,
    SectionDraft.__table__,
    ReviewComment.__table__,
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
    project = Project(name="Drafts Project", owner_id=owner_id)
    session.add(project)
    session.flush()
    session.add(
        ProjectMember(project_id=project.id, user_id=owner_id, role=ProjectMemberRole.OWNER.value)
    )
    session.flush()
    return project


def _create_system(
    session: Session,
    *,
    project_id: str,
    title: str = "System 1",
    status: str = SystemState.FIGURE_PLAN_READY.value,
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


def _add_system_section(
    session: Session,
    *,
    system_id: str,
    section_key: str,
    title: str,
    order_no: int,
) -> SystemSection:
    section = SystemSection(
        system_id=system_id,
        section_key=section_key,
        title=title,
        order_no=order_no,
    )
    session.add(section)
    session.flush()
    return section


def _wait_for_outline_completion(
    engine, workflow_id: str, system_id: str, *, expected_outline_count: int
) -> None:
    for _ in range(50):
        with Session(engine) as session:
            workflow = session.get(WorkflowInstance, workflow_id)
            outlines = session.scalars(
                select(Outline)
                .where(Outline.system_id == system_id)
                .order_by(Outline.version.asc())
            ).all()
            if (
                workflow is not None
                and workflow.status == TaskStatus.SUCCEEDED.value
                and len(outlines) == expected_outline_count
            ):
                return
        time.sleep(0.01)

    raise AssertionError("Outline generation did not complete in time")


def _wait_for_section_draft_completion(
    engine,
    workflow_id: str,
    system_id: str,
    *,
    expected_draft_count: int,
) -> None:
    for _ in range(50):
        with Session(engine) as session:
            workflow = session.get(WorkflowInstance, workflow_id)
            drafts = session.scalars(
                select(SectionDraft)
                .where(SectionDraft.system_id == system_id)
                .order_by(SectionDraft.version.asc())
            ).all()
            if (
                workflow is not None
                and workflow.status == TaskStatus.SUCCEEDED.value
                and len(drafts) == expected_draft_count
            ):
                return
        time.sleep(0.01)

    raise AssertionError("Section draft generation did not complete in time")


def _wait_for_workflow_status(engine, workflow_id: str, expected_status: str) -> None:
    for _ in range(50):
        with Session(engine) as session:
            workflow = session.get(WorkflowInstance, workflow_id)
            if workflow is not None and workflow.status == expected_status:
                return
        time.sleep(0.01)

    raise AssertionError(f"Workflow {workflow_id} did not reach status {expected_status} in time")


# ---------------------------------------------------------------------------
# Outline (G4)
# ---------------------------------------------------------------------------


def test_generate_outline_returns_accepted(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="approved claim",
            section_ref="introduction",
            status="approved",
        )
        session.add(claim)
        session.commit()
        system_id = system.id
        claim_id = claim.id

    response = client.post(f"/api/systems/{system_id}/outline/generate", json={})

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    handle = body["data"]["handle"]
    workflow_id = handle["workflow_id"]
    assert workflow_id is not None
    assert handle["job_id"].startswith(f"outline_generate:{system_id}:")
    assert handle["status"] == TaskStatus.QUEUED.value

    with Session(engine) as session:
        workflow = session.scalars(
            select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
        ).one()
        events = session.scalars(
            select(WorkflowEvent)
            .where(WorkflowEvent.instance_id == workflow.id)
            .order_by(WorkflowEvent.created_at.asc())
        ).all()

    assert workflow.workflow_key == "outline_generate"
    assert workflow.status == TaskStatus.QUEUED.value
    assert [event.event_type for event in events] == [EventType.TASK_CREATED.value]

    _wait_for_outline_completion(engine, workflow_id, system_id, expected_outline_count=1)

    with Session(engine) as session:
        outlines = session.scalars(
            select(Outline).where(Outline.system_id == system_id).order_by(Outline.version.asc())
        ).all()
        workflow = session.scalars(
            select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
        ).one()
        events = session.scalars(
            select(WorkflowEvent)
            .where(WorkflowEvent.instance_id == workflow.id)
            .order_by(WorkflowEvent.created_at.asc())
        ).all()

    assert len(outlines) == 1
    assert outlines[0].system_id == system_id
    assert outlines[0].version == 1
    assert outlines[0].status == "draft"
    assert outlines[0].generated_from_claims_json == [claim_id]
    assert workflow.status == TaskStatus.SUCCEEDED.value
    assert [event.event_type for event in events] == [
        EventType.TASK_CREATED.value,
        EventType.TASK_SUCCEEDED.value,
    ]

    list_response = client.get(f"/api/systems/{system_id}/outlines")
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["success"] is True
    assert len(list_body["data"]) == 1
    assert list_body["data"][0]["version"] == 1
    assert list_body["data"][0]["generatedFromClaimsJson"] == [claim_id]
    assert list_body["data"][0]["bindings"] == []


def test_list_outlines_empty(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.commit()
        system_id = system.id

    response = client.get(f"/api/systems/{system_id}/outlines")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == []


def test_confirm_outline(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="intro",
            title="Introduction",
            order_no=1,
        )
        outline = Outline(
            system_id=system.id,
            version=1,
            status="draft",
        )
        session.add(outline)
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
        binding = OutlineAssetBinding(
            outline_id=outline.id,
            asset_id=asset.id,
            section_key="intro",
        )
        session.add(binding)
        session.commit()
        outline_id = outline.id
        asset_id = asset.id

    response = client.post(f"/api/outlines/{outline_id}/confirm")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "confirmed"
    assert body["data"]["approvedAt"] is not None
    assert body["data"]["bindings"] == [
        {
            "id": body["data"]["bindings"][0]["id"],
            "outlineId": outline_id,
            "sectionKey": "intro",
            "assetId": asset_id,
            "bindingNote": None,
            "createdAt": body["data"]["bindings"][0]["createdAt"],
            "updatedAt": body["data"]["bindings"][0]["updatedAt"],
        }
    ]

    with Session(engine) as session:
        updated = session.get(Outline, outline_id)
    assert updated is not None
    assert updated.status == "confirmed"
    assert updated.approved_at is not None


def test_confirm_outline_reconfirm_keeps_original_approved_at(client: TestClient, engine) -> None:
    original_approved_at = datetime(2026, 1, 1, tzinfo=UTC)
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        outline = Outline(
            system_id=system.id,
            version=1,
            status="confirmed",
            approved_at=original_approved_at,
        )
        session.add(outline)
        session.commit()
        outline_id = outline.id

    expected_approved_at = original_approved_at.replace(tzinfo=None)

    response = client.post(f"/api/outlines/{outline_id}/confirm", json={"status": "confirmed"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["approvedAt"] == expected_approved_at.isoformat()

    with Session(engine) as session:
        updated = session.get(Outline, outline_id)
    assert updated is not None
    assert updated.approved_at == expected_approved_at


def test_list_outlines_includes_bindings(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        outline = Outline(
            system_id=system.id,
            version=1,
            status="confirmed",
        )
        session.add(outline)
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
        session.add(
            OutlineAssetBinding(
                outline_id=outline.id,
                asset_id=asset.id,
                section_key="intro",
                binding_note="supports intro",
            )
        )
        session.commit()
        system_id = system.id
        outline_id = outline.id
        asset_id = asset.id

    response = client.get(f"/api/systems/{system_id}/outlines")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == [
        {
            "id": outline_id,
            "systemId": system_id,
            "version": 1,
            "outlineJson": {},
            "generatedFromClaimsJson": [],
            "status": "confirmed",
            "bindings": [
                {
                    "id": body["data"][0]["bindings"][0]["id"],
                    "outlineId": outline_id,
                    "sectionKey": "intro",
                    "assetId": asset_id,
                    "bindingNote": "supports intro",
                    "createdAt": body["data"][0]["bindings"][0]["createdAt"],
                    "updatedAt": body["data"][0]["bindings"][0]["updatedAt"],
                }
            ],
            "approvedAt": body["data"][0]["approvedAt"],
            "createdAt": body["data"][0]["createdAt"],
            "updatedAt": body["data"][0]["updatedAt"],
        }
    ]


def test_confirm_outline_rejects_invalid_status(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        outline = Outline(
            system_id=system.id,
            version=1,
            status="draft",
        )
        session.add(outline)
        session.commit()
        outline_id = outline.id

    response = client.post(f"/api/outlines/{outline_id}/confirm", json={"status": "approved"})

    assert response.status_code == 422


def test_create_outline_binding(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="intro",
            title="Introduction",
            order_no=1,
        )
        outline = Outline(
            system_id=system.id,
            version=1,
            status="draft",
        )
        session.add(outline)
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
        outline_id = outline.id
        asset_id = asset.id

    response = client.post(
        f"/api/outlines/{outline_id}/bindings",
        json={"assetId": asset_id, "sectionKey": "intro"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["outlineId"] == outline_id
    assert body["data"]["assetId"] == asset_id
    assert body["data"]["sectionKey"] == "intro"

    with Session(engine) as session:
        binding = session.scalars(
            select(OutlineAssetBinding).where(OutlineAssetBinding.outline_id == outline_id)
        ).one()
    assert binding.asset_id == asset_id
    assert binding.section_key == "intro"


def test_create_outline_binding_rejects_unknown_section_key(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="results",
            title="Results",
            order_no=1,
        )
        outline = Outline(
            system_id=system.id,
            version=1,
            status="draft",
        )
        session.add(outline)
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
        outline_id = outline.id
        asset_id = asset.id

    response = client.post(
        f"/api/outlines/{outline_id}/bindings",
        json={"assetId": asset_id, "sectionKey": "intro"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "section" in body["error"].lower()


def test_create_outline_binding_missing_asset_returns_404(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        outline = Outline(
            system_id=system.id,
            version=1,
            status="draft",
        )
        session.add(outline)
        session.commit()
        outline_id = outline.id

    response = client.post(
        f"/api/outlines/{outline_id}/bindings",
        json={"assetId": "missing-asset-id", "sectionKey": "intro"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False


def test_create_outline_binding_rejects_cross_system_asset(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system1 = _create_system(session, project_id=project.id, title="System 1", system_no=1)
        system2 = _create_system(session, project_id=project.id, title="System 2", system_no=2)
        outline = Outline(
            system_id=system1.id,
            version=1,
            status="draft",
        )
        session.add(outline)
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
        outline_id = outline.id
        asset_id = asset.id

    response = client.post(
        f"/api/outlines/{outline_id}/bindings",
        json={"assetId": asset_id, "sectionKey": "intro"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "system" in body["error"].lower()


def test_create_outline_binding_duplicate_returns_409(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="intro",
            title="Intro",
            order_no=1,
        )
        outline = Outline(
            system_id=system.id,
            version=1,
            status="draft",
        )
        session.add(outline)
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
        binding = OutlineAssetBinding(
            outline_id=outline.id,
            asset_id=asset.id,
            section_key="intro",
        )
        session.add(binding)
        session.commit()
        outline_id = outline.id
        asset_id = asset.id

    response = client.post(
        f"/api/outlines/{outline_id}/bindings",
        json={"assetId": asset_id, "sectionKey": "intro"},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert "already exists" in body["error"].lower() or "duplicate" in body["error"].lower()


# ---------------------------------------------------------------------------
# SectionDraft + Review (G5)
# ---------------------------------------------------------------------------


def test_generate_section_draft_returns_accepted(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="introduction",
            title="Introduction",
            order_no=1,
        )
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="approved claim",
            section_ref="introduction",
            status="approved",
        )
        session.add(claim)
        session.flush()
        outline = Outline(
            system_id=system.id,
            version=1,
            status="confirmed",
            outline_json={
                "sections": [
                    {
                        "section_key": "introduction",
                        "claim_ids": [claim.id],
                    }
                ]
            },
        )
        session.add(outline)
        session.commit()
        system_id = system.id
        claim_id = claim.id
        outline_id = outline.id

    response = client.post(
        f"/api/systems/{system_id}/sections/introduction/draft",
        json={"claimIds": [], "outlineId": outline_id},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    handle = body["data"]["handle"]
    workflow_id = handle["workflow_id"]
    assert workflow_id is not None
    assert handle["job_id"].startswith(f"section_draft_generate:{system_id}:")
    assert handle["status"] == TaskStatus.QUEUED.value

    with Session(engine) as session:
        workflow = session.scalars(
            select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
        ).one()
        events = session.scalars(
            select(WorkflowEvent)
            .where(WorkflowEvent.instance_id == workflow.id)
            .order_by(WorkflowEvent.created_at.asc())
        ).all()

    assert workflow.workflow_key == "section_draft_generate"
    assert workflow.status == TaskStatus.QUEUED.value
    assert workflow.context_json["claim_ids"] == [claim_id]
    assert [event.event_type for event in events] == [EventType.TASK_CREATED.value]

    _wait_for_section_draft_completion(engine, workflow_id, system_id, expected_draft_count=1)

    with Session(engine) as session:
        drafts = session.scalars(
            select(SectionDraft)
            .where(SectionDraft.system_id == system_id)
            .order_by(SectionDraft.version.asc())
        ).all()
        workflow = session.scalars(
            select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
        ).one()
        events = session.scalars(
            select(WorkflowEvent)
            .where(WorkflowEvent.instance_id == workflow.id)
            .order_by(WorkflowEvent.created_at.asc())
        ).all()

    assert len(drafts) == 1
    assert drafts[0].system_id == system_id
    assert drafts[0].outline_id == outline_id
    assert drafts[0].section_key == "introduction"
    assert drafts[0].version == 1
    assert drafts[0].status == "draft"
    assert drafts[0].generated_from_claims_json == [claim_id]
    assert workflow.status == TaskStatus.SUCCEEDED.value
    assert [event.event_type for event in events] == [
        EventType.TASK_CREATED.value,
        EventType.TASK_SUCCEEDED.value,
    ]

    list_response = client.get(f"/api/systems/{system_id}/drafts")
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["success"] is True
    assert len(list_body["data"]) == 1
    assert list_body["data"][0]["sectionKey"] == "introduction"
    assert list_body["data"][0]["generatedFromClaimsJson"] == [claim_id]
    assert list_body["data"][0]["reviewComments"] == []


def test_generate_section_draft_uses_list_outline_shape_when_claim_ids_empty(
    client: TestClient, engine
) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="introduction",
            title="Introduction",
            order_no=1,
        )
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="approved claim",
            section_ref="introduction",
            status="approved",
        )
        session.add(claim)
        session.flush()
        outline = Outline(
            system_id=system.id,
            version=1,
            status="confirmed",
            outline_json=[
                {
                    "section_key": "introduction",
                    "claim_ids": [claim.id],
                }
            ],
        )
        session.add(outline)
        session.commit()
        system_id = system.id
        outline_id = outline.id
        claim_id = claim.id

    response = client.post(
        f"/api/systems/{system_id}/sections/introduction/draft",
        json={"claimIds": [], "outlineId": outline_id},
    )

    assert response.status_code == 202
    workflow_id = response.json()["data"]["handle"]["workflow_id"]
    assert workflow_id is not None

    _wait_for_section_draft_completion(engine, workflow_id, system_id, expected_draft_count=1)

    with Session(engine) as session:
        draft = session.scalars(
            select(SectionDraft).where(SectionDraft.system_id == system_id)
        ).one()
    assert draft.generated_from_claims_json == [claim_id]


def test_generate_section_draft_uses_workflow_claim_snapshot_when_outline_changes_after_acceptance(
    client: TestClient,
    engine,
) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="introduction",
            title="Introduction",
            order_no=1,
        )
        claim1 = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="approved claim 1",
            section_ref="introduction",
            status="approved",
        )
        claim2 = Claim(
            system_id=system.id,
            claim_id="C2",
            statement="approved claim 2",
            section_ref="introduction",
            status="approved",
        )
        session.add_all([claim1, claim2])
        session.flush()
        outline = Outline(
            system_id=system.id,
            version=1,
            status="confirmed",
            outline_json={
                "sections": [
                    {
                        "section_key": "introduction",
                        "claim_ids": [claim1.id],
                    }
                ]
            },
        )
        session.add(outline)
        session.commit()
        system_id = system.id
        outline_id = outline.id
        claim1_id = claim1.id
        claim2_id = claim2.id

    response = client.post(
        f"/api/systems/{system_id}/sections/introduction/draft",
        json={"claimIds": [], "outlineId": outline_id},
    )

    assert response.status_code == 202
    workflow_id = response.json()["data"]["handle"]["workflow_id"]
    assert workflow_id is not None

    with Session(engine) as session:
        workflow = session.get(WorkflowInstance, workflow_id)
        assert workflow is not None
        assert workflow.context_json["claim_ids"] == [claim1_id]
        outline = session.get(Outline, outline_id)
        assert outline is not None
        outline.outline_json = {
            "sections": [
                {
                    "section_key": "introduction",
                    "claim_ids": [claim2_id],
                }
            ]
        }
        session.commit()

    _wait_for_section_draft_completion(engine, workflow_id, system_id, expected_draft_count=1)

    with Session(engine) as session:
        draft = session.scalars(
            select(SectionDraft).where(SectionDraft.system_id == system_id)
        ).one()
    assert draft.generated_from_claims_json == [claim1_id]


def test_list_drafts_includes_review_comments(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        draft = SectionDraft(
            system_id=system.id,
            section_key="introduction",
            version=1,
            content_md="draft text",
            status="draft",
        )
        session.add(draft)
        session.flush()
        session.add(
            ReviewComment(
                draft_id=draft.id,
                commenter_id="reviewer-1",
                comment_text="Need stronger evidence",
                decision="request_changes",
            )
        )
        session.commit()
        system_id = system.id
        draft_id = draft.id

    response = client.get(f"/api/systems/{system_id}/drafts")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"][0]["reviewComments"] == [
        {
            "id": body["data"][0]["reviewComments"][0]["id"],
            "draftId": draft_id,
            "commenterId": "reviewer-1",
            "commentText": "Need stronger evidence",
            "decision": "request_changes",
            "contextJson": {},
            "resolvedAt": None,
            "createdAt": body["data"][0]["reviewComments"][0]["createdAt"],
            "updatedAt": body["data"][0]["reviewComments"][0]["updatedAt"],
        }
    ]


def test_generate_section_draft_failure_payload_hides_internal_error(
    client: TestClient,
    engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(_section_key: str, _claims: list[Claim]) -> str:
        raise RuntimeError("sensitive internal error")

    monkeypatch.setattr("app.modules.drafts.service._build_generated_section_draft_content", _boom)

    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="introduction",
            title="Introduction",
            order_no=1,
        )
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="approved claim",
            section_ref="introduction",
            status="approved",
        )
        session.add(claim)
        session.commit()
        system_id = system.id
        claim_id = claim.id

    response = client.post(
        f"/api/systems/{system_id}/sections/introduction/draft",
        json={"claimIds": [claim_id]},
    )

    assert response.status_code == 202
    workflow_id = response.json()["data"]["handle"]["workflow_id"]
    assert workflow_id is not None

    _wait_for_workflow_status(engine, workflow_id, TaskStatus.FAILED.value)

    with Session(engine) as session:
        workflow = session.get(WorkflowInstance, workflow_id)
        events = session.scalars(
            select(WorkflowEvent)
            .where(WorkflowEvent.instance_id == workflow_id)
            .order_by(WorkflowEvent.created_at.asc())
        ).all()

    assert workflow is not None
    assert workflow.status == TaskStatus.FAILED.value
    assert workflow.last_error == "Section draft generation failed unexpectedly for introduction"
    assert events[-1].event_type == EventType.TASK_FAILED.value
    assert events[-1].payload_json["code"] == ErrorCode.WORKFLOW_ERROR.value
    assert events[-1].payload_json["details"] == {}
    assert events[-1].payload_json["status"] == TaskStatus.FAILED.value
    assert (
        events[-1].payload_json["message"]
        == "Section draft generation failed unexpectedly for introduction"
    )
    assert "sensitive internal error" not in str(events[-1].payload_json)


def test_list_drafts_empty(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.commit()
        system_id = system.id

    response = client.get(f"/api/systems/{system_id}/drafts")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == []


def test_approve_draft(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        draft = SectionDraft(
            system_id=system.id,
            section_key="introduction",
            version=1,
            content_md="draft text",
            status="draft",
        )
        session.add(draft)
        session.flush()
        comment = ReviewComment(
            draft_id=draft.id,
            commenter_id="reviewer-1",
            comment_text="Looks good",
            decision="approve",
        )
        session.add(comment)
        session.commit()
        draft_id = draft.id

    response = client.post(f"/api/drafts/{draft_id}/approve")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "approved"
    assert body["data"]["approvedAt"] is not None
    assert body["data"]["reviewComments"] == [
        {
            "id": body["data"]["reviewComments"][0]["id"],
            "draftId": draft_id,
            "commenterId": "reviewer-1",
            "commentText": "Looks good",
            "decision": "approve",
            "contextJson": {},
            "resolvedAt": None,
            "createdAt": body["data"]["reviewComments"][0]["createdAt"],
            "updatedAt": body["data"]["reviewComments"][0]["updatedAt"],
        }
    ]

    with Session(engine) as session:
        updated = session.get(SectionDraft, draft_id)
    assert updated is not None
    assert updated.status == "approved"
    assert updated.approved_at is not None


def test_approve_draft_rejects_invalid_status(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        draft = SectionDraft(
            system_id=system.id,
            section_key="introduction",
            version=1,
            content_md="draft text",
            status="draft",
        )
        session.add(draft)
        session.commit()
        draft_id = draft.id

    response = client.post(f"/api/drafts/{draft_id}/approve", json={"status": "confirmed"})

    assert response.status_code == 422


def test_approve_draft_reapprove_keeps_original_approved_at(client: TestClient, engine) -> None:
    original_approved_at = datetime(2026, 1, 1, tzinfo=UTC)
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        draft = SectionDraft(
            system_id=system.id,
            section_key="introduction",
            version=1,
            content_md="draft text",
            status="approved",
            approved_at=original_approved_at,
        )
        session.add(draft)
        session.commit()
        draft_id = draft.id

    expected_approved_at = original_approved_at.replace(tzinfo=None)

    response = client.post(f"/api/drafts/{draft_id}/approve", json={"status": "approved"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["approvedAt"] == expected_approved_at.isoformat()

    with Session(engine) as session:
        updated = session.get(SectionDraft, draft_id)
    assert updated is not None
    assert updated.approved_at == expected_approved_at


def test_add_review_comment(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        draft = SectionDraft(
            system_id=system.id,
            section_key="introduction",
            version=1,
            content_md="draft text",
            status="draft",
        )
        session.add(draft)
        session.commit()
        draft_id = draft.id

    response = client.post(
        f"/api/drafts/{draft_id}/review",
        json={
            "commenterId": "reviewer-1",
            "commentText": "Needs revision",
            "decision": "request_changes",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["draftId"] == draft_id
    assert body["data"]["commenterId"] == "reviewer-1"
    assert body["data"]["commentText"] == "Needs revision"
    assert body["data"]["decision"] == "request_changes"

    with Session(engine) as session:
        comment = session.scalars(
            select(ReviewComment).where(ReviewComment.draft_id == draft_id)
        ).one()
    assert comment.commenter_id == "reviewer-1"
    assert comment.comment_text == "Needs revision"
    assert comment.decision == "request_changes"


def test_add_review_comment_rejects_invalid_decision(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        draft = SectionDraft(
            system_id=system.id,
            section_key="introduction",
            version=1,
            content_md="draft text",
            status="draft",
        )
        session.add(draft)
        session.commit()
        draft_id = draft.id

    response = client.post(
        f"/api/drafts/{draft_id}/review",
        json={
            "commenterId": "reviewer-1",
            "commentText": "Needs revision",
            "decision": "confirmed",
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 404 scenarios
# ---------------------------------------------------------------------------


def test_generate_outline_missing_system_returns_404(client: TestClient) -> None:
    response = client.post("/api/systems/missing-system/outline/generate", json={})

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_generate_draft_missing_system_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/systems/missing-system/sections/introduction/draft",
        json={"claimIds": []},
    )

    assert response.status_code == 404
    assert response.json()["success"] is False


# ---------------------------------------------------------------------------
# HC-13: Section draft claim validation
# ---------------------------------------------------------------------------


def test_generate_section_draft_requires_claim_ids_without_outline(
    client: TestClient, engine
) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="introduction",
            title="Introduction",
            order_no=1,
        )
        session.commit()
        system_id = system.id

    response = client.post(
        f"/api/systems/{system_id}/sections/introduction/draft",
        json={"claimIds": []},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "claim" in body["error"].lower()


def test_generate_section_draft_requires_claims_when_outline_cannot_supply_any(
    client: TestClient, engine
) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="introduction",
            title="Introduction",
            order_no=1,
        )
        outline = Outline(
            system_id=system.id,
            version=1,
            status="confirmed",
            outline_json={"sections": []},
        )
        session.add(outline)
        session.commit()
        system_id = system.id
        outline_id = outline.id

    response = client.post(
        f"/api/systems/{system_id}/sections/introduction/draft",
        json={"claimIds": [], "outlineId": outline_id},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "claim" in body["error"].lower()


def test_generate_section_draft_rejects_unapproved_claim(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="introduction",
            title="Introduction",
            order_no=1,
        )
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="test claim",
            section_ref="introduction",
            status="draft",
        )
        session.add(claim)
        session.commit()
        system_id = system.id
        claim_id = claim.id

    response = client.post(
        f"/api/systems/{system_id}/sections/introduction/draft",
        json={"claimIds": [claim_id]},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "approved" in body["error"].lower()


def test_generate_section_draft_rejects_cross_system_claim(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system1 = _create_system(session, project_id=project.id, title="System 1", system_no=1)
        system2 = _create_system(session, project_id=project.id, title="System 2", system_no=2)
        _add_system_section(
            session,
            system_id=system1.id,
            section_key="introduction",
            title="Introduction",
            order_no=1,
        )
        claim = Claim(
            system_id=system2.id,
            claim_id="C1",
            statement="test claim",
            section_ref="introduction",
            status="approved",
        )
        session.add(claim)
        session.commit()
        system_id = system1.id
        claim_id = claim.id

    response = client.post(
        f"/api/systems/{system_id}/sections/introduction/draft",
        json={"claimIds": [claim_id]},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "system" in body["error"].lower()


def test_generate_section_draft_rejects_missing_outline(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="introduction",
            title="Introduction",
            order_no=1,
        )
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="approved claim",
            section_ref="introduction",
            status="approved",
        )
        session.add(claim)
        session.commit()
        system_id = system.id
        claim_id = claim.id

    response = client.post(
        f"/api/systems/{system_id}/sections/introduction/draft",
        json={"claimIds": [claim_id], "outlineId": "missing-outline-id"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False


def test_generate_section_draft_rejects_cross_system_outline(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system1 = _create_system(session, project_id=project.id, title="System 1", system_no=1)
        system2 = _create_system(session, project_id=project.id, title="System 2", system_no=2)
        _add_system_section(
            session,
            system_id=system1.id,
            section_key="introduction",
            title="Introduction",
            order_no=1,
        )
        claim = Claim(
            system_id=system1.id,
            claim_id="C1",
            statement="approved claim",
            section_ref="introduction",
            status="approved",
        )
        outline = Outline(
            system_id=system2.id,
            version=1,
            status="confirmed",
        )
        session.add_all([claim, outline])
        session.commit()
        system_id = system1.id
        claim_id = claim.id
        outline_id = outline.id

    response = client.post(
        f"/api/systems/{system_id}/sections/introduction/draft",
        json={"claimIds": [claim_id], "outlineId": outline_id},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "outline" in body["error"].lower() or "system" in body["error"].lower()


def test_generate_section_draft_rejects_claim_section_mismatch(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        _add_system_section(
            session,
            system_id=system.id,
            section_key="introduction",
            title="Introduction",
            order_no=1,
        )
        _add_system_section(
            session,
            system_id=system.id,
            section_key="results",
            title="Results",
            order_no=2,
        )
        claim = Claim(
            system_id=system.id,
            claim_id="C1",
            statement="approved claim",
            section_ref="results",
            status="approved",
        )
        session.add(claim)
        session.commit()
        system_id = system.id
        claim_id = claim.id

    response = client.post(
        f"/api/systems/{system_id}/sections/introduction/draft",
        json={"claimIds": [claim_id]},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "section" in body["error"].lower()
