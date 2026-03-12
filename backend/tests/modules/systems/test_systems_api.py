from __future__ import annotations

from collections.abc import Generator
from contextlib import AbstractAsyncContextManager
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.common.enums import EventType, GateKey, SystemState, TaskStatus
from app.main import create_app
from app.modules.systems.service import advance_system
from app.modules.tasks.service import TaskWorkflowService
from app.persistence import get_db_session
from app.persistence.base import Base
from app.persistence.models.asset import Asset
from app.persistence.models.evidence import FigurePlan
from app.persistence.models.manifest import AssetManifest
from app.persistence.models.project import Project, ProjectMember, ProjectMemberRole
from app.persistence.models.system import ExperimentalSystem, SystemSection
from app.persistence.models.workflow import WorkflowEvent, WorkflowInstance


class RunSyncAsyncSession(AsyncSession):
    pass


class FakeAsyncSessionContext(AbstractAsyncContextManager[RunSyncAsyncSession]):
    def __init__(self, session: RunSyncAsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> RunSyncAsyncSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class SyncSessionAdapter:
    def __init__(self, session: Session) -> None:
        self.sync_session = session

    def add(self, instance: object) -> None:
        self.sync_session.add(instance)

    async def flush(self) -> None:
        self.sync_session.flush()

    async def refresh(self, instance: object) -> None:
        self.sync_session.refresh(instance)

    async def execute(self, statement):
        return self.sync_session.execute(statement)

    async def commit(self) -> None:
        self.sync_session.commit()

    async def close(self) -> None:
        self.sync_session.close()


ALL_TABLES = [
    Project.__table__,
    ProjectMember.__table__,
    ExperimentalSystem.__table__,
    SystemSection.__table__,
    Asset.__table__,
    AssetManifest.__table__,
    FigurePlan.__table__,
    WorkflowInstance.__table__,
    WorkflowEvent.__table__,
]

DROP_TABLES = list(reversed(ALL_TABLES))


def _sqlite_engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


@pytest.fixture()
def engine():
    eng = _sqlite_engine()
    Base.metadata.create_all(eng, tables=ALL_TABLES)
    yield eng
    Base.metadata.drop_all(eng, tables=DROP_TABLES)
    eng.dispose()


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


@pytest.fixture()
def async_client(engine, monkeypatch) -> Generator[TestClient, None, None]:
    app = create_app()
    sync_session = Session(engine)
    session = object.__new__(RunSyncAsyncSession)
    session.run_sync = AsyncMock(side_effect=lambda fn, *args, **kwargs: fn(sync_session, *args, **kwargs))
    session.execute = AsyncMock(side_effect=lambda statement, *args, **kwargs: sync_session.execute(statement, *args, **kwargs))
    session.flush = AsyncMock(side_effect=sync_session.flush)
    session.refresh = AsyncMock(side_effect=sync_session.refresh)
    session.commit = AsyncMock(side_effect=sync_session.commit)
    session.close = AsyncMock(side_effect=sync_session.close)
    session.add = sync_session.add
    session.sync_session = sync_session

    session_factory = lambda: FakeAsyncSessionContext(session)
    monkeypatch.setattr("app.persistence.session.async_session_factory", session_factory)

    with TestClient(app) as test_client:
        yield test_client

    sync_session.close()


def _create_project(
    session: Session,
    *,
    name: str = "Test Project",
    owner_id: str = "owner-1",
    thesis_schema_json: dict | None = None,
) -> Project:
    project = Project(
        name=name,
        owner_id=owner_id,
        thesis_schema_json=thesis_schema_json or {},
    )
    session.add(project)
    session.flush()
    session.add(ProjectMember(project_id=project.id, user_id=owner_id, role=ProjectMemberRole.OWNER.value))
    session.flush()
    return project


def _create_system(
    session: Session,
    *,
    project_id: str,
    system_no: int = 1,
    title: str = "Test System",
    status: str = SystemState.DRAFT.value,
    research_goal: str | None = None,
    samples_subjects: str | None = None,
    variables_controls: str | None = None,
    output_metrics: str | None = None,
    methods_summary: str | None = None,
    system_card_json: dict | None = None,
) -> ExperimentalSystem:
    system = ExperimentalSystem(
        project_id=project_id,
        system_no=system_no,
        title=title,
        status=status,
        research_goal=research_goal,
        samples_subjects=samples_subjects,
        variables_controls=variables_controls,
        output_metrics=output_metrics,
        methods_summary=methods_summary,
        system_card_json=system_card_json or {},
    )
    session.add(system)
    session.flush()
    return system


def test_create_system_persists_and_returns_detail(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(
            session,
            thesis_schema_json={
                "outline": ["Introduction", "Methods", "Results"],
                "chapters": ["Ignored Chapter"],
            },
        )
        session.commit()
        project_id = project.id

    response = client.post(
        f"/api/projects/{project_id}/systems",
        json={
            "title": " My Experiment ",
            "researchGoal": "Test hypothesis about X",
            "samplesSubjects": "10 samples",
            "variablesControls": "Temperature, pressure",
            "outputMetrics": "Yield percentage",
            "methodsSummary": "Standard protocol",
            "systemCardJson": {"key": "value"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["title"] == "My Experiment"
    assert data["systemNo"] == 1
    assert data["projectId"] == project_id
    assert data["status"] == SystemState.DRAFT.value
    assert data["researchGoal"] == "Test hypothesis about X"
    assert data["systemCardJson"] == {"key": "value"}
    assert [
        (section["sectionKey"], section["title"], section["orderNo"])
        for section in data["sections"]
    ] == [
        ("introduction", "Introduction", 1),
        ("methods", "Methods", 2),
        ("results", "Results", 3),
    ]

    with Session(engine) as session:
        system = session.scalars(select(ExperimentalSystem)).one()
        sections = session.scalars(
            select(SystemSection)
            .where(SystemSection.system_id == system.id)
            .order_by(SystemSection.order_no.asc(), SystemSection.section_key.asc())
        ).all()
    assert system.title == "My Experiment"
    assert system.project_id == project_id
    assert system.system_no == 1
    assert [
        (section.section_key, section.title, section.order_no)
        for section in sections
    ] == [
        ("introduction", "Introduction", 1),
        ("methods", "Methods", 2),
        ("results", "Results", 3),
    ]


def test_get_system_detail_uses_chapters_when_outline_missing(
    client: TestClient,
    engine,
) -> None:
    with Session(engine) as session:
        project = _create_project(
            session,
            thesis_schema_json={"outline": [], "chapters": ["Materials", "Discussion"]},
        )
        session.commit()
        project_id = project.id

    create_response = client.post(
        f"/api/projects/{project_id}/systems",
        json={"title": "Chapter Based System"},
    )

    assert create_response.status_code == 201
    system_id = create_response.json()["data"]["id"]

    detail_response = client.get(f"/api/systems/{system_id}")

    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["success"] is True
    assert [
        (section["sectionKey"], section["title"], section["orderNo"])
        for section in body["data"]["sections"]
    ] == [
        ("materials", "Materials", 1),
        ("discussion", "Discussion", 2),
    ]


def test_get_system_detail_returns_default_sections_when_schema_missing(
    client: TestClient,
    engine,
) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        session.commit()
        project_id = project.id

    create_response = client.post(
        f"/api/projects/{project_id}/systems",
        json={"title": "Fallback System"},
    )

    assert create_response.status_code == 201
    system_id = create_response.json()["data"]["id"]

    detail_response = client.get(f"/api/systems/{system_id}")

    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["success"] is True
    assert [
        (section["sectionKey"], section["title"], section["orderNo"])
        for section in body["data"]["sections"]
    ] == [
        ("introduction", "引言", 1),
        ("materials_and_methods", "实验材料与方法", 2),
        ("results_and_discussion", "结果与讨论", 3),
        ("chapter_summary", "本章小结", 4),
    ]


def test_create_system_preserves_explicit_section_keys_from_schema(
    client: TestClient,
    engine,
) -> None:
    with Session(engine) as session:
        project = _create_project(
            session,
            thesis_schema_json={
                "outline": [
                    {
                        "sectionKey": "results-discussion",
                        "title": "Results & Discussion",
                    }
                ]
            },
        )
        session.commit()
        project_id = project.id

    response = client.post(
        f"/api/projects/{project_id}/systems",
        json={"title": "Schema Key Preservation"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert [
        (section["sectionKey"], section["title"], section["orderNo"])
        for section in body["data"]["sections"]
    ] == [
        ("results-discussion", "Results & Discussion", 1),
    ]


def test_create_system_auto_increments_system_no(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        _create_system(session, project_id=project.id, system_no=1, title="System 1")
        session.commit()
        project_id = project.id

    response = client.post(
        f"/api/projects/{project_id}/systems",
        json={"title": "System 2"},
    )

    assert response.status_code == 201
    assert response.json()["data"]["systemNo"] == 2


def test_create_system_returns_404_for_missing_project(client: TestClient) -> None:
    response = client.post(
        "/api/projects/nonexistent-id/systems",
        json={"title": "Orphan System"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False


def test_update_system_definition(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id, title="Original Title")
        session.commit()
        system_id = system.id

    response = client.patch(
        f"/api/systems/{system_id}",
        json={
            "title": "Updated Title",
            "researchGoal": "New goal",
            "systemCardJson": {"updated": True},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["title"] == "Updated Title"
    assert body["data"]["researchGoal"] == "New goal"
    assert body["data"]["systemCardJson"] == {"updated": True}


def test_update_system_returns_404_for_missing_system(client: TestClient) -> None:
    response = client.patch(
        "/api/systems/nonexistent-id",
        json={"title": "No Such System"},
    )

    assert response.status_code == 404


def test_get_workflow_returns_null_when_no_workflow(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.commit()
        system_id = system.id

    response = client.get(f"/api/systems/{system_id}/workflow")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] is None


def test_advance_route_uses_asyncsession_run_sync_for_g1_blocked(async_client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(
            session,
            project_id=project.id,
            status=SystemState.SYSTEM_DEFINED.value,
            research_goal="Investigate X",
            samples_subjects="10 mice",
            variables_controls="Temperature",
            output_metrics="Survival rate",
            methods_summary="Standard protocol",
            system_card_json={"hypothesis": "X causes Y"},
        )
        session.commit()
        system_id = system.id

    response = async_client.post(f"/api/systems/{system_id}/advance")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["outcome"] == "blocked"
    assert body["data"]["gate"] == GateKey.G1.value
    assert body["data"]["currentState"] == SystemState.SYSTEM_DEFINED.value
    assert body["data"]["blockers"][0]["code"] == "figure_plan_not_ready"


async def test_advance_blocked_on_g0_returns_blockers() -> None:
    eng = _sqlite_engine()
    Base.metadata.create_all(eng, tables=ALL_TABLES)
    adapter = SyncSessionAdapter(Session(eng))
    try:
        project = Project(name="Test Project", owner_id="owner-1")
        adapter.sync_session.add(project)
        adapter.sync_session.flush()
        adapter.sync_session.add(
            ProjectMember(project_id=project.id, user_id="owner-1", role=ProjectMemberRole.OWNER.value)
        )
        adapter.sync_session.flush()

        system = ExperimentalSystem(
            project_id=project.id,
            system_no=1,
            title="Incomplete System",
            status=SystemState.DRAFT.value,
        )
        adapter.sync_session.add(system)
        adapter.sync_session.flush()
        adapter.sync_session.commit()

        result = await advance_system(adapter, system.id)  # type: ignore[arg-type]

        assert result.outcome == "blocked"
        assert result.gate == GateKey.G0
        assert result.current_state == SystemState.DRAFT
        assert len(result.blockers) > 0
        assert result.blockers[0].code == "system_definition_incomplete"
        assert result.snapshot is not None
        assert result.snapshot.status == TaskStatus.WAITING_USER

        instances = adapter.sync_session.scalars(select(WorkflowInstance)).all()
        assert len(instances) == 1
        assert instances[0].status == TaskStatus.WAITING_USER.value

        events = adapter.sync_session.scalars(select(WorkflowEvent)).all()
        assert len(events) >= 2
        event_types = [e.event_type for e in events]
        assert EventType.GATE_BLOCKED.value in event_types
    finally:
        await adapter.close()
        Base.metadata.drop_all(eng, tables=DROP_TABLES)
        eng.dispose()


async def test_advance_passed_from_g0_to_system_defined() -> None:
    eng = _sqlite_engine()
    Base.metadata.create_all(eng, tables=ALL_TABLES)
    adapter = SyncSessionAdapter(Session(eng))
    try:
        project = Project(name="Test Project", owner_id="owner-1")
        adapter.sync_session.add(project)
        adapter.sync_session.flush()
        adapter.sync_session.add(
            ProjectMember(project_id=project.id, user_id="owner-1", role=ProjectMemberRole.OWNER.value)
        )
        adapter.sync_session.flush()

        system = ExperimentalSystem(
            project_id=project.id,
            system_no=1,
            title="Complete System",
            status=SystemState.DRAFT.value,
            research_goal="Investigate X",
            samples_subjects="10 mice",
            variables_controls="Temperature",
            output_metrics="Survival rate",
            methods_summary="Standard protocol",
            system_card_json={"hypothesis": "X causes Y"},
        )
        adapter.sync_session.add(system)
        adapter.sync_session.flush()
        adapter.sync_session.commit()

        system_id = system.id

        result = await advance_system(adapter, system_id)  # type: ignore[arg-type]

        assert result.outcome == "accepted"
        assert result.gate == GateKey.G0
        assert result.from_state == SystemState.DRAFT
        assert result.to_state == SystemState.SYSTEM_DEFINED
        assert result.handle is not None
        assert result.snapshot is not None
        assert result.snapshot.status == TaskStatus.SUCCEEDED

        adapter.sync_session.expire_all()
        updated_system = adapter.sync_session.get(ExperimentalSystem, system_id)
        assert updated_system is not None
        assert updated_system.status == SystemState.SYSTEM_DEFINED.value

        events = adapter.sync_session.scalars(select(WorkflowEvent)).all()
        event_types = [e.event_type for e in events]
        assert EventType.GATE_PASSED.value in event_types
    finally:
        await adapter.close()
        Base.metadata.drop_all(eng, tables=DROP_TABLES)
        eng.dispose()


async def test_get_workflow_snapshot_after_advance() -> None:
    eng = _sqlite_engine()
    Base.metadata.create_all(eng, tables=ALL_TABLES)
    adapter = SyncSessionAdapter(Session(eng))
    try:
        project = Project(name="Test Project", owner_id="owner-1")
        adapter.sync_session.add(project)
        adapter.sync_session.flush()
        adapter.sync_session.add(
            ProjectMember(project_id=project.id, user_id="owner-1", role=ProjectMemberRole.OWNER.value)
        )
        adapter.sync_session.flush()

        system = ExperimentalSystem(
            project_id=project.id,
            system_no=1,
            title="Complete System",
            status=SystemState.DRAFT.value,
            research_goal="Investigate X",
            samples_subjects="10 mice",
            variables_controls="Temperature",
            output_metrics="Survival rate",
            methods_summary="Standard protocol",
            system_card_json={"hypothesis": "X causes Y"},
        )
        adapter.sync_session.add(system)
        adapter.sync_session.flush()
        adapter.sync_session.commit()

        await advance_system(adapter, system.id)  # type: ignore[arg-type]

        task_service = TaskWorkflowService(adapter)  # type: ignore[arg-type]
        snapshot = await task_service.get_workflow_snapshot(
            system_id=system.id,
            workflow_key="system_advance",
        )

        assert snapshot is not None
        assert snapshot.system_id == system.id
        assert snapshot.workflow_key == "system_advance"
        assert len(snapshot.events) >= 2
    finally:
        await adapter.close()
        Base.metadata.drop_all(eng, tables=DROP_TABLES)
        eng.dispose()


# ---- Restricted deletion tests ----


def test_delete_empty_system_returns_204(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.commit()
        system_id = system.id

    resp = client.delete(f"/api/systems/{system_id}")
    assert resp.status_code == 204

    with Session(engine) as session:
        remaining = session.scalars(select(ExperimentalSystem)).all()
        assert len(remaining) == 0


def test_delete_system_with_assets_returns_409(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.add(
            Asset(
                project_id=project.id,
                system_id=system.id,
                asset_type="image",
                file_name="fig1.png",
                storage_key="s3://bucket/fig1.png",
                uploaded_by="owner-1",
            )
        )
        session.commit()
        system_id = system.id

    resp = client.delete(f"/api/systems/{system_id}")
    assert resp.status_code == 409
    body = resp.json()
    assert body["success"] is False
    assert "associated data" in body["error"]


def test_delete_system_with_manifest_returns_409(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.add(
            AssetManifest(
                project_id=project.id,
                system_id=system.id,
                version=1,
                status="draft",
                manifest_json={},
            )
        )
        session.commit()
        system_id = system.id

    resp = client.delete(f"/api/systems/{system_id}")
    assert resp.status_code == 409
    body = resp.json()
    assert body["success"] is False
    assert "associated data" in body["error"]


def test_delete_system_with_workflow_returns_409(client: TestClient, engine) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        system = _create_system(session, project_id=project.id)
        session.add(
            WorkflowInstance(
                project_id=project.id,
                system_id=system.id,
                workflow_key="system_advance",
                current_state="Draft",
                current_gate="G0",
                status="queued",
                version=1,
            )
        )
        session.commit()
        system_id = system.id

    resp = client.delete(f"/api/systems/{system_id}")
    assert resp.status_code == 409
    body = resp.json()
    assert body["success"] is False


def test_delete_nonexistent_system_returns_404(client: TestClient) -> None:
    resp = client.delete("/api/systems/nonexistent-id")
    assert resp.status_code == 404


# ---- system_no concurrent safety test ----


def test_create_system_with_duplicate_system_no_returns_409(
    client: TestClient, engine
) -> None:
    with Session(engine) as session:
        project = _create_project(session)
        _create_system(session, project_id=project.id, system_no=1, title="Existing")
        session.commit()
        project_id = project.id

    # Manually insert a system_no=2 so the next auto-computed no (2) will collide
    with Session(engine) as session:
        session.add(
            ExperimentalSystem(
                project_id=project_id,
                system_no=2,
                title="Sneaky",
            )
        )
        session.commit()

    # The service will compute next_no = max(2) + 1 = 3, but let's force a collision
    # by pre-inserting system_no=3 right before the API call
    with Session(engine) as session:
        session.add(
            ExperimentalSystem(
                project_id=project_id,
                system_no=3,
                title="Collision Target",
            )
        )
        session.commit()

    # Now max system_no is 3, next computed = 4 which won't collide...
    # To truly test IntegrityError, we patch get_next_system_no to return an existing no
    from unittest.mock import patch

    with patch(
        "app.modules.systems.service.repository.get_next_system_no",
        return_value=1,  # already exists
    ):
        resp = client.post(
            f"/api/projects/{project_id}/systems",
            json={"title": "Colliding System"},
        )

    assert resp.status_code == 409
    body = resp.json()
    assert body["success"] is False
    assert "conflict" in body["error"].lower() or "retry" in body["error"].lower()
