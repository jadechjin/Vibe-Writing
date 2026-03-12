from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.modules.projects.router import router as projects_router
from app.persistence import get_db_session
from app.persistence.base import Base
from app.persistence.models import (
    ExperimentalSystem,
    Project,
    ProjectMember,
    ProjectMemberRole,
    SystemSection,
)


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            ProjectMember.__table__,
            ExperimentalSystem.__table__,
            SystemSection.__table__,
        ],
    )
    yield engine
    Base.metadata.drop_all(
        engine,
        tables=[
            SystemSection.__table__,
            ExperimentalSystem.__table__,
            ProjectMember.__table__,
            Project.__table__,
        ],
    )
    engine.dispose()


@pytest.fixture()
def client(engine) -> Generator[TestClient, None, None]:
    app = create_app()
    app.include_router(projects_router, prefix="/api")

    def override_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_create_project_persists_project_and_owner_member(client: TestClient, engine) -> None:
    response = client.post(
        "/api/projects",
        json={
            "name": " Thesis MVP ",
            "ownerId": " owner-1 ",
            "thesisSchemaJson": {"chapters": ["results"]},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["name"] == "Thesis MVP"
    assert body["data"]["ownerId"] == "owner-1"
    assert body["data"]["status"] == "draft"
    assert body["data"]["systemCount"] == 0
    assert body["data"]["systems"] == []
    assert body["data"]["thesisSchemaJson"] == {"chapters": ["results"]}

    with Session(engine) as session:
        project = session.scalars(select(Project)).one()
        owner_member = session.scalars(select(ProjectMember)).one()

    assert project.name == "Thesis MVP"
    assert project.owner_id == "owner-1"
    assert project.thesis_schema_json == {"chapters": ["results"]}
    assert owner_member.project_id == project.id
    assert owner_member.user_id == "owner-1"
    assert owner_member.role == ProjectMemberRole.OWNER.value


def test_list_projects_returns_database_records(client: TestClient, engine) -> None:
    with Session(engine) as session:
        alpha = _create_project(session, name="Alpha", owner_id="owner-a")
        beta = _create_project(session, name="Beta", owner_id="owner-b")
        session.add_all(
            [
                ExperimentalSystem(project_id=alpha.id, system_no=1, title="Alpha System"),
                ExperimentalSystem(project_id=beta.id, system_no=1, title="Beta System 1"),
                ExperimentalSystem(project_id=beta.id, system_no=2, title="Beta System 2"),
            ]
        )
        session.commit()

    response = client.get("/api/projects")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"] == {"total": 2, "page": 1, "limit": 2}

    items = {item["name"]: item for item in body["data"]}
    assert items["Alpha"]["ownerId"] == "owner-a"
    assert items["Alpha"]["systemCount"] == 1
    assert items["Beta"]["ownerId"] == "owner-b"
    assert items["Beta"]["systemCount"] == 2


def test_get_project_detail_returns_system_summaries(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(
            session,
            name="Detail Project",
            owner_id="owner-detail",
            thesis_schema_json={"outline": ["intro", "discussion"]},
        )
        system_one = ExperimentalSystem(project_id=project.id, system_no=1, title="System 1")
        system_two = ExperimentalSystem(project_id=project.id, system_no=2, title="System 2")
        session.add_all([system_one, system_two])
        session.flush()
        session.add_all(
            [
                SystemSection(system_id=system_one.id, section_key="intro", title="引言", order_no=1),
                SystemSection(system_id=system_one.id, section_key="methods", title="方法", order_no=2),
                SystemSection(system_id=system_two.id, section_key="results", title="结果", order_no=1),
            ]
        )
        session.commit()
        project_id = project.id

    response = client.get(f"/api/projects/{project_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"] == project_id
    assert body["data"]["name"] == "Detail Project"
    assert body["data"]["ownerId"] == "owner-detail"
    assert body["data"]["systemCount"] == 2
    assert body["data"]["thesisSchemaJson"] == {"outline": ["intro", "discussion"]}

    systems = body["data"]["systems"]
    assert [system["systemNo"] for system in systems] == [1, 2]
    assert systems[0]["title"] == "System 1"
    assert systems[0]["sectionCount"] == 2
    assert systems[0]["status"] == "Draft"
    assert systems[1]["title"] == "System 2"
    assert systems[1]["sectionCount"] == 1


def _create_project(
    session: Session,
    *,
    name: str,
    owner_id: str,
    thesis_schema_json: dict | None = None,
) -> Project:
    project = Project(
        name=name,
        owner_id=owner_id,
        thesis_schema_json=thesis_schema_json or {},
    )
    session.add(project)
    session.flush()
    session.add(
        ProjectMember(
            project_id=project.id,
            user_id=owner_id,
            role=ProjectMemberRole.OWNER.value,
        )
    )
    return project


# ---- Completion metrics tests ----


def test_project_detail_zero_completions(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session, name="Zero", owner_id="owner-z")
        session.add(
            ExperimentalSystem(
                project_id=project.id, system_no=1, title="S1", status="Draft"
            )
        )
        session.add(
            ExperimentalSystem(
                project_id=project.id, system_no=2, title="S2", status="Section_Drafting"
            )
        )
        session.commit()
        pid = project.id

    resp = client.get(f"/api/projects/{pid}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["completedSystemCount"] == 0
    assert data["introductionUnlocked"] is False


def test_project_detail_partial_completions(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session, name="Partial", owner_id="owner-p")
        session.add(
            ExperimentalSystem(
                project_id=project.id, system_no=1, title="S1", status="Chapter_Approved"
            )
        )
        session.add(
            ExperimentalSystem(
                project_id=project.id, system_no=2, title="S2", status="Draft"
            )
        )
        session.commit()
        pid = project.id

    resp = client.get(f"/api/projects/{pid}")
    data = resp.json()["data"]
    assert data["completedSystemCount"] == 1
    assert data["introductionUnlocked"] is False


def test_project_detail_threshold_exact_unlocks(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session, name="Exact", owner_id="owner-e")
        for i in range(1, 4):
            session.add(
                ExperimentalSystem(
                    project_id=project.id,
                    system_no=i,
                    title=f"S{i}",
                    status="Chapter_Approved",
                )
            )
        session.commit()
        pid = project.id

    resp = client.get(f"/api/projects/{pid}")
    data = resp.json()["data"]
    assert data["completedSystemCount"] == 3
    assert data["introductionUnlocked"] is True


def test_project_detail_above_threshold(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session, name="Above", owner_id="owner-a")
        for i in range(1, 6):
            status = "Chapter_Approved" if i <= 4 else "Draft"
            session.add(
                ExperimentalSystem(
                    project_id=project.id,
                    system_no=i,
                    title=f"S{i}",
                    status=status,
                )
            )
        session.commit()
        pid = project.id

    resp = client.get(f"/api/projects/{pid}")
    data = resp.json()["data"]
    assert data["completedSystemCount"] == 4
    assert data["introductionUnlocked"] is True
