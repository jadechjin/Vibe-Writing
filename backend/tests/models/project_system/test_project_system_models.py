from sqlalchemy import UniqueConstraint, create_engine
from sqlalchemy.orm import Session

from app.common.enums import SystemState
from app.persistence.base import Base
from app.persistence.models.project import Project, ProjectMember, ProjectMemberRole, ProjectStatus
from app.persistence.models.system import ExperimentalSystem, SystemSection


def test_project_and_system_tables_define_expected_unique_constraints() -> None:
    project_member_constraints = {
        tuple(constraint.columns.keys())
        for constraint in ProjectMember.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    system_constraints = {
        tuple(constraint.columns.keys())
        for constraint in ExperimentalSystem.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    section_constraints = {
        tuple(constraint.columns.keys())
        for constraint in SystemSection.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("project_id", "user_id") in project_member_constraints
    assert ("project_id", "system_no") in system_constraints
    assert ("system_id", "section_key") in section_constraints
    assert ("system_id", "order_no") in section_constraints


def test_project_and_system_models_apply_defaults_on_flush() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            ProjectMember.__table__,
            ExperimentalSystem.__table__,
            SystemSection.__table__,
        ],
    )

    with Session(engine) as session:
        project = Project(name="Thesis MVP", owner_id="owner-1")
        session.add(project)
        session.flush()

        member = ProjectMember(
            project_id=project.id,
            user_id="editor-1",
            role=ProjectMemberRole.EDITOR.value,
        )
        system = ExperimentalSystem(project_id=project.id, system_no=1, title="System 1")
        session.add_all([member, system])
        session.flush()

        section = SystemSection(
            system_id=system.id,
            section_key="introduction",
            title="引言",
            order_no=1,
        )
        session.add(section)
        session.flush()

        assert project.status == ProjectStatus.DRAFT.value
        assert project.thesis_schema_json == {}
        assert project.created_at is not None
        assert member.role == ProjectMemberRole.EDITOR.value
        assert system.status == SystemState.DRAFT.value
        assert system.system_card_json == {}
        assert section.system_id == system.id
