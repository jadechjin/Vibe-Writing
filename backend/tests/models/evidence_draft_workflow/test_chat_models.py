from __future__ import annotations

import pytest
from sqlalchemy import UniqueConstraint, create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.persistence.base import Base
from app.persistence.models import (
    ExperimentalSystem,
    FigurePlan,
    FigurePlanChatMessage,
    FigurePlanChatSession,
    Project,
)


def _sqlite_memory_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _unique_constraint_names(model: type) -> set[str]:
    return {constraint.name for constraint in model.__table__.constraints if constraint.name}


def _index_names(model: type) -> set[str]:
    return {index.name for index in model.__table__.indexes if index.name}


def _seed_chat_context(session: Session) -> FigurePlan:
    project = Project(name="Chat Project", owner_id="owner-1")
    session.add(project)
    session.flush()

    system = ExperimentalSystem(
        project_id=project.id,
        system_no=1,
        title="System 1",
    )
    session.add(system)
    session.flush()

    plan = FigurePlan(
        system_id=system.id,
        figure_no="fig-1",
        title="Figure 1",
        claim_text="claim",
        status="draft",
        version=1,
        data_needed_json=[],
        method_json={},
        acceptance_criteria_json=[],
    )
    session.add(plan)
    session.flush()
    return plan


def test_chat_models_define_expected_constraints() -> None:
    session_constraints = {
        tuple(constraint.columns.keys())
        for constraint in FigurePlanChatSession.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_figure_plan_chat_sessions_plan_provider" in _unique_constraint_names(
        FigurePlanChatSession
    )
    assert ("figure_plan_id", "provider") in session_constraints
    assert "ix_figure_plan_chat_messages_session_turn" in _index_names(FigurePlanChatMessage)


def test_chat_session_unique_constraint_rejects_duplicate_provider_per_plan() -> None:
    engine = _sqlite_memory_engine()
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            ExperimentalSystem.__table__,
            FigurePlan.__table__,
            FigurePlanChatSession.__table__,
        ],
    )

    with Session(engine) as session:
        plan = _seed_chat_context(session)
        session.add(
            FigurePlanChatSession(
                figure_plan_id=plan.id,
                provider="claude",
                status="active",
            )
        )
        session.flush()

        session.add(
            FigurePlanChatSession(
                figure_plan_id=plan.id,
                provider="claude",
                status="active",
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_chat_message_unique_index_rejects_duplicate_turn_index_per_session() -> None:
    engine = _sqlite_memory_engine()
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            ExperimentalSystem.__table__,
            FigurePlan.__table__,
            FigurePlanChatSession.__table__,
            FigurePlanChatMessage.__table__,
        ],
    )

    with Session(engine) as session:
        plan = _seed_chat_context(session)
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
                role="user",
                content="first",
                status="completed",
                turn_index=0,
            )
        )
        session.flush()

        session.add(
            FigurePlanChatMessage(
                session_id=chat_session.id,
                role="assistant",
                content="duplicate",
                status="streaming",
                turn_index=0,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
