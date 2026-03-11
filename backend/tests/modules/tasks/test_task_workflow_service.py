from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.common.enums import EventType, GateKey, SystemState, TaskStatus
from app.common.schemas import Blocker
from app.modules.tasks.schemas import WorkflowEventAppend, WorkflowStartInput
from app.modules.tasks.service import TaskWorkflowService
from app.persistence.base import Base
from app.persistence.models.project import Project
from app.persistence.models.system import ExperimentalSystem
from app.persistence.models.workflow import WorkflowEvent, WorkflowInstance
from app.workflows.system_workflow import (
    WorkflowCommand,
    WorkflowEventCommand,
    WorkflowStartResult,
    append_system_workflow_event,
    start_system_workflow,
)


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


def _sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _build_service() -> tuple[TaskWorkflowService, SyncSessionAdapter, object]:
    engine = _sqlite_engine()
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            ExperimentalSystem.__table__,
            WorkflowInstance.__table__,
            WorkflowEvent.__table__,
        ],
    )
    adapter = SyncSessionAdapter(Session(engine))
    service = TaskWorkflowService(adapter)  # type: ignore[arg-type]
    return service, adapter, engine


def _seed_scope(session: Session) -> tuple[Project, ExperimentalSystem]:
    project = Project(name="Workflow Project", owner_id="owner-1")
    session.add(project)
    session.flush()

    system = ExperimentalSystem(project_id=project.id, system_no=1, title="System 1")
    session.add(system)
    session.flush()
    return project, system


async def test_start_workflow_creates_instance_event_and_job_handle() -> None:
    service, adapter, _engine = _build_service()
    try:
        project, system = _seed_scope(adapter.sync_session)

        result = await service.start_workflow(
            WorkflowStartInput(
                project_id=project.id,
                system_id=system.id,
                workflow_key="system.advance",
                current_state=SystemState.SYSTEM_DEFINED,
                current_gate=GateKey.G0,
                context={"requested_by": "owner-1"},
                message="advance queued",
                created_by="owner-1",
            )
        )
        await adapter.commit()

        assert result.handle.workflow_id == result.snapshot.workflow_id
        assert result.handle.job_id == f"system.advance:{system.id}:1"
        assert result.snapshot.current_state == SystemState.SYSTEM_DEFINED.value
        assert result.snapshot.current_gate == GateKey.G0.value
        assert result.snapshot.status == TaskStatus.QUEUED
        assert result.snapshot.latest_event is not None
        assert result.snapshot.latest_event.event_type == EventType.TASK_CREATED.value
        assert result.snapshot.latest_event.message == "advance queued"
        assert result.snapshot.context["requested_by"] == "owner-1"

        persisted_instance = adapter.sync_session.get(WorkflowInstance, result.snapshot.workflow_id)
        assert persisted_instance is not None
        assert persisted_instance.version == 1
        assert persisted_instance.workflow_key == "system.advance"

        persisted_snapshot = await service.get_workflow_snapshot(workflow_id=result.snapshot.workflow_id)
        assert persisted_snapshot is not None
        assert len(persisted_snapshot.events) == 1
    finally:
        await adapter.close()


async def test_append_event_records_progress_and_snapshot_history() -> None:
    service, adapter, _engine = _build_service()
    try:
        project, system = _seed_scope(adapter.sync_session)
        started = await service.start_workflow(
            WorkflowStartInput(
                project_id=project.id,
                system_id=system.id,
                workflow_key="system.advance",
                current_state=SystemState.SYSTEM_DEFINED,
                current_gate=GateKey.G0,
                message="advance queued",
            )
        )
        await adapter.commit()

        snapshot = await service.append_event(
            started.snapshot.workflow_id,
            WorkflowEventAppend(
                event_type=EventType.TASK_PROGRESS,
                message="advance running",
                status=TaskStatus.RUNNING,
                progress=40,
                payload={"step": "gate-review"},
                context_update={"last_step": "gate-review"},
            ),
        )
        await adapter.commit()

        assert snapshot.status == TaskStatus.RUNNING
        assert snapshot.latest_event is not None
        assert snapshot.latest_event.event_type == EventType.TASK_PROGRESS.value
        assert snapshot.latest_event.progress == 40
        assert snapshot.latest_event.payload == {"step": "gate-review"}
        assert snapshot.context["last_step"] == "gate-review"
        assert set(item.event_type for item in snapshot.events) == {
            EventType.TASK_CREATED.value,
            EventType.TASK_PROGRESS.value,
        }
        assert len(snapshot.events) == 2
    finally:
        await adapter.close()


async def test_record_gate_blocked_persists_blockers_in_snapshot() -> None:
    service, adapter, _engine = _build_service()
    try:
        project, system = _seed_scope(adapter.sync_session)
        started = await service.start_workflow(
            WorkflowStartInput(
                project_id=project.id,
                system_id=system.id,
                workflow_key="system.advance",
                current_state=SystemState.DRAFT,
                current_gate=GateKey.G0,
                message="advance queued",
            )
        )
        await adapter.commit()

        blocker = Blocker(
            code="system_definition_missing",
            message="System card is incomplete",
            gate=GateKey.G0,
            current_state=SystemState.DRAFT,
        )
        snapshot = await service.record_gate_blocked(
            workflow_id=started.snapshot.workflow_id,
            message="advance blocked",
            blockers=[blocker],
            current_gate=GateKey.G0.value,
            current_state=SystemState.DRAFT.value,
        )
        await adapter.commit()

        assert snapshot.status == TaskStatus.WAITING_USER
        assert snapshot.latest_event is not None
        assert snapshot.latest_event.event_type == EventType.GATE_BLOCKED.value
        assert snapshot.latest_blockers[0].code == "system_definition_missing"
        assert snapshot.latest_blockers[0].gate == GateKey.G0
        assert snapshot.latest_event.payload["blockers"][0]["code"] == "system_definition_missing"
    finally:
        await adapter.close()


async def test_get_workflow_snapshot_uses_latest_instance_for_system() -> None:
    service, adapter, engine = _build_service()
    reader = SyncSessionAdapter(Session(engine))
    reader_service = TaskWorkflowService(reader)  # type: ignore[arg-type]
    try:
        project, system = _seed_scope(adapter.sync_session)

        first = await service.start_workflow(
            WorkflowStartInput(
                project_id=project.id,
                system_id=system.id,
                workflow_key="system.advance",
                current_state=SystemState.DRAFT,
                message="first workflow",
            )
        )
        await adapter.commit()
        await service.record_gate_passed(
            workflow_id=first.snapshot.workflow_id,
            message="first passed",
            current_gate=GateKey.G0.value,
            from_state=SystemState.DRAFT.value,
            to_state=SystemState.SYSTEM_DEFINED.value,
        )
        await adapter.commit()

        second = await service.start_workflow(
            WorkflowStartInput(
                project_id=project.id,
                system_id=system.id,
                workflow_key="system.advance",
                current_state=SystemState.SYSTEM_DEFINED,
                current_gate=GateKey.G1,
                message="second workflow",
            )
        )
        await adapter.commit()

        snapshot = await reader_service.get_workflow_snapshot(
            system_id=system.id,
            workflow_key="system.advance",
        )

        assert snapshot is not None
        assert snapshot.workflow_id == second.snapshot.workflow_id
        assert snapshot.job_id == f"system.advance:{system.id}:2"
        assert snapshot.version == 2
        assert snapshot.current_gate == GateKey.G1.value
        assert snapshot.latest_event is not None
        assert snapshot.latest_event.message == "second workflow"
    finally:
        await reader.close()
        await adapter.close()


async def test_system_workflow_helpers_remain_thin_adapters() -> None:
    service, adapter, _engine = _build_service()
    try:
        project, system = _seed_scope(adapter.sync_session)

        result = await start_system_workflow(
            service,
            WorkflowCommand(
                project_id=project.id,
                system_id=system.id,
                workflow_key="system.advance",
                current_state=SystemState.DRAFT.value,
                target_state=SystemState.SYSTEM_DEFINED.value,
                current_gate=GateKey.G0.value,
                context={"origin": "systems-service"},
                message="advance queued",
            ),
        )
        await adapter.commit()

        assert isinstance(result, WorkflowStartResult)
        assert result.handle is not None
        assert result.handle.workflow_id == result.snapshot.workflow_id
        assert result.handle.status == TaskStatus.QUEUED

        assert result.snapshot.current_state == SystemState.DRAFT.value
        assert result.snapshot.context["target_state"] == SystemState.SYSTEM_DEFINED.value
        assert result.snapshot.context["origin"] == "systems-service"

        updated_snapshot = await append_system_workflow_event(
            service,
            WorkflowEventCommand(
                workflow_id=result.snapshot.workflow_id,
                event_type=EventType.GATE_PASSED,
                message="advance succeeded",
                status=TaskStatus.SUCCEEDED,
                from_state=SystemState.DRAFT.value,
                to_state=SystemState.SYSTEM_DEFINED.value,
                current_state=SystemState.SYSTEM_DEFINED.value,
                current_gate=GateKey.G0.value,
                context_update={"latest_blockers": []},
            ),
        )
        await adapter.commit()

        assert updated_snapshot.status == TaskStatus.SUCCEEDED
        assert updated_snapshot.current_state == SystemState.SYSTEM_DEFINED.value
        assert updated_snapshot.latest_event is not None
        assert updated_snapshot.latest_event.event_type == EventType.GATE_PASSED.value
    finally:
        await adapter.close()


async def test_queued_workflow_current_state_is_real_not_target() -> None:
    service, adapter, _engine = _build_service()
    try:
        project, system = _seed_scope(adapter.sync_session)

        result = await service.start_workflow(
            WorkflowStartInput(
                project_id=project.id,
                system_id=system.id,
                workflow_key="system.advance",
                current_state=SystemState.DRAFT,
                current_gate=GateKey.G0,
                context={"target_state": SystemState.SYSTEM_DEFINED.value},
                message="advance queued",
            )
        )
        await adapter.commit()

        assert result.snapshot.current_state == SystemState.DRAFT.value
        assert result.snapshot.context["target_state"] == SystemState.SYSTEM_DEFINED.value
        assert result.snapshot.status == TaskStatus.QUEUED

        persisted = await service.get_workflow_snapshot(
            workflow_id=result.snapshot.workflow_id,
        )
        assert persisted is not None
        assert persisted.current_state == SystemState.DRAFT.value
        assert persisted.context["target_state"] == SystemState.SYSTEM_DEFINED.value
    finally:
        await adapter.close()
