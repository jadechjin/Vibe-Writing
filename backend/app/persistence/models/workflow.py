from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import SystemState, TaskStatus
from app.persistence.base import AuditMixin, Base, UUIDPrimaryKeyMixin
from app.persistence.types import JsonDict


class WorkflowInstance(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "workflow_instances"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "system_id",
            "workflow_key",
            "version",
            name="uq_workflow_instances_scope_key_version",
        ),
    )

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    system_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_key: Mapped[str] = mapped_column(String(100), nullable=False)
    current_state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=SystemState.DRAFT.value,
    )
    current_gate: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=TaskStatus.QUEUED.value)
    context_json: Mapped[dict[str, object]] = mapped_column(JsonDict, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkflowEvent(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "workflow_events"

    instance_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    to_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JsonDict, nullable=False, default=dict)


class ApprovalTask(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "approval_tasks"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    system_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_instance_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("workflow_instances.id", ondelete="SET NULL"),
        nullable=True,
    )
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    reviewer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = ["ApprovalTask", "WorkflowEvent", "WorkflowInstance"]
