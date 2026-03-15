from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.main import create_app
from app.persistence import get_db_session
from app.persistence.base import Base
from app.persistence.models import (
    Asset,
    ExperimentalSystem,
    FigurePlan,
    FigurePlanAsset,
    FigurePlanChatMessage,
    FigurePlanChatSession,
    Project,
    ProjectMember,
    ProjectMemberRole,
    SystemSection,
)

ALL_TABLES = [
    Project.__table__,
    ProjectMember.__table__,
    ExperimentalSystem.__table__,
    SystemSection.__table__,
    Asset.__table__,
    FigurePlan.__table__,
    FigurePlanAsset.__table__,
    FigurePlanChatSession.__table__,
    FigurePlanChatMessage.__table__,
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


def _seed_plan_context(session: Session) -> tuple[FigurePlan, str]:
    project = Project(name="Evidence Project", owner_id="owner-1")
    session.add(project)
    session.flush()

    session.add(
        ProjectMember(
            project_id=project.id,
            user_id="owner-1",
            role=ProjectMemberRole.OWNER.value,
        )
    )
    session.flush()

    system = ExperimentalSystem(
        project_id=project.id,
        system_no=1,
        title="System 1",
    )
    session.add(system)
    session.flush()

    session.add(
        SystemSection(
            system_id=system.id,
            section_key="results",
            title="Results",
            order_no=1,
        )
    )
    session.flush()

    plan = FigurePlan(
        system_id=system.id,
        figure_no="fig-1",
        title="Figure Title",
        claim_text="Show the main effect",
        section_key="results",
        brief_text="Need a comparison chart",
        status="draft",
        version=1,
        data_needed_json=[],
        method_json={},
        acceptance_criteria_json=[],
    )
    session.add(plan)
    session.flush()
    return plan, project.id


def _seed_uploaded_asset(session: Session, plan: FigurePlan, *, project_id: str) -> None:
    asset = Asset(
        project_id=project_id,
        system_id=plan.system_id,
        asset_type="figure_material",
        file_name="source-image.png",
        storage_key="uploads/source-image.png",
        mime_type="image/png",
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
    session.flush()


def _seed_busy_session(session: Session, plan: FigurePlan) -> None:
    chat_session = FigurePlanChatSession(
        figure_plan_id=plan.id,
        provider="claude",
        status="active",
    )
    session.add(chat_session)
    session.flush()

    session.add(
        FigurePlanChatMessage(
            session_id=chat_session.id,
            role="assistant",
            content="still running",
            status="streaming",
            turn_index=0,
        )
    )
    session.flush()


def test_send_chat_message_returns_409_when_session_is_busy(client: TestClient, engine) -> None:
    with Session(engine) as session:
        plan, _ = _seed_plan_context(session)
        _seed_busy_session(session, plan)
        session.commit()
        plan_id = plan.id

    response = client.post(
        f"/api/figure-plans/{plan_id}/chat/messages",
        json={"provider": "claude", "content": "hello"},
    )

    assert response.status_code == 409


def test_send_chat_message_includes_uploaded_images_in_context(
    client: TestClient,
    engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    async def fake_invoke_chat_stream(
        provider,
        message: str,
        session_id: str | None = None,
        context: str = "",
    ) -> AsyncGenerator[str, None]:
        captured["provider"] = provider.value
        captured["message"] = message
        captured["context"] = context
        captured["session_id"] = session_id or ""
        yield "ack"

    monkeypatch.setattr(
        "app.modules.evidence.service.invoke_chat_stream",
        fake_invoke_chat_stream,
    )

    with Session(engine) as session:
        plan, project_id = _seed_plan_context(session)
        _seed_uploaded_asset(session, plan, project_id=project_id)
        session.commit()
        plan_id = plan.id

    with client.stream(
        "POST",
        f"/api/figure-plans/{plan_id}/chat/messages",
        json={"provider": "claude", "content": "describe it"},
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "ack" in body
    assert "Figure Title" in captured["context"]
    assert "Show the main effect" in captured["context"]
    assert "Results" in captured["context"]
    assert "Need a comparison chart" in captured["context"]
    assert "Uploaded Images" in captured["context"]
    assert "source-image.png" in captured["context"]


def test_send_chat_message_rejects_unknown_provider(client: TestClient, engine) -> None:
    with Session(engine) as session:
        plan, _ = _seed_plan_context(session)
        session.commit()
        plan_id = plan.id

    response = client.post(
        f"/api/figure-plans/{plan_id}/chat/messages",
        json={"provider": "unknown", "content": "hello"},
    )

    assert response.status_code == 422
