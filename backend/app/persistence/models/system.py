from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import SystemState
from app.persistence.base import AuditMixin, Base, UUIDPrimaryKeyMixin
from app.persistence.types import JsonDict, LongText, ShortText

if TYPE_CHECKING:
    from app.persistence.models.project import Project


class ExperimentalSystem(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "experimental_systems"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "system_no",
            name="uq_experimental_systems_project_system_no",
        ),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    system_no: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(ShortText, nullable=False)
    research_goal: Mapped[str | None] = mapped_column(LongText(), nullable=True)
    samples_subjects: Mapped[str | None] = mapped_column(LongText(), nullable=True)
    variables_controls: Mapped[str | None] = mapped_column(LongText(), nullable=True)
    output_metrics: Mapped[str | None] = mapped_column(LongText(), nullable=True)
    methods_summary: Mapped[str | None] = mapped_column(LongText(), nullable=True)
    system_card_json: Mapped[dict[str, Any]] = mapped_column(
        JsonDict,
        default=dict,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(64),
        default=SystemState.DRAFT.value,
        nullable=False,
        index=True,
    )

    project: Mapped["Project"] = relationship("Project", back_populates="systems")
    sections: Mapped[list["SystemSection"]] = relationship(
        "SystemSection",
        back_populates="system",
        cascade="all, delete-orphan",
    )


class SystemSection(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "system_sections"
    __table_args__ = (
        UniqueConstraint(
            "system_id",
            "section_key",
            name="uq_system_sections_system_section_key",
        ),
        UniqueConstraint(
            "system_id",
            "order_no",
            name="uq_system_sections_system_order_no",
        ),
    )

    system_id: Mapped[str] = mapped_column(
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_key: Mapped[str] = mapped_column(ShortText, nullable=False)
    title: Mapped[str] = mapped_column(ShortText, nullable=False)
    order_no: Mapped[int] = mapped_column(nullable=False)

    system: Mapped[ExperimentalSystem] = relationship(
        "ExperimentalSystem",
        back_populates="sections",
    )


__all__ = [
    "ExperimentalSystem",
    "SystemSection",
]
