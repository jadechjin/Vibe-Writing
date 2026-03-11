from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.base import AuditMixin, Base, UUIDPrimaryKeyMixin
from app.persistence.types import JsonDict, ShortText

if TYPE_CHECKING:
    from app.persistence.models.system import ExperimentalSystem


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectMemberRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class Project(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(ShortText, nullable=False)
    owner_id: Mapped[str] = mapped_column(ShortText, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default=ProjectStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    template_asset_id: Mapped[str | None] = mapped_column(ShortText, nullable=True)
    thesis_schema_json: Mapped[dict[str, Any]] = mapped_column(
        JsonDict,
        default=dict,
        nullable=False,
    )

    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    systems: Mapped[list["ExperimentalSystem"]] = relationship(
        "ExperimentalSystem",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectMember(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(ShortText, nullable=False, index=True)
    role: Mapped[str] = mapped_column(
        String(32),
        default=ProjectMemberRole.EDITOR.value,
        nullable=False,
    )

    project: Mapped[Project] = relationship("Project", back_populates="members")


__all__ = [
    "Project",
    "ProjectMember",
    "ProjectMemberRole",
    "ProjectStatus",
]
