from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import ReviewDecision
from app.persistence.base import AuditMixin, Base, UUIDPrimaryKeyMixin
from app.persistence.types import JsonDict


class Outline(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "outlines"
    __table_args__ = (UniqueConstraint("system_id", "version", name="uq_outlines_system_version"),)

    system_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    outline_json: Mapped[dict[str, object] | list[dict[str, object]]] = mapped_column(
        JsonDict,
        nullable=False,
        default=dict,
    )
    generated_from_claims_json: Mapped[list[str]] = mapped_column(
        JsonDict,
        nullable=False,
        default=list,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OutlineAssetBinding(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "outline_asset_bindings"
    __table_args__ = (
        UniqueConstraint(
            "outline_id",
            "section_key",
            "asset_id",
            name="uq_outline_asset_bindings_target",
        ),
    )

    outline_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("outlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    section_key: Mapped[str] = mapped_column(String(100), nullable=False)
    asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    binding_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class SectionDraft(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "section_drafts"
    __table_args__ = (
        UniqueConstraint(
            "system_id",
            "section_key",
            "version",
            name="uq_section_drafts_system_section_version",
        ),
    )

    system_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    outline_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("outlines.id", ondelete="SET NULL"),
        nullable=True,
    )
    section_key: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    generated_from_claims_json: Mapped[list[str]] = mapped_column(
        JsonDict,
        nullable=False,
        default=list,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_by_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewComment(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "review_comments"

    draft_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("section_drafts.id", ondelete="CASCADE"),
        nullable=False,
    )
    commenter_id: Mapped[str] = mapped_column(String(255), nullable=False)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=ReviewDecision.REQUEST_CHANGES.value,
    )
    context_json: Mapped[dict[str, object]] = mapped_column(JsonDict, nullable=False, default=dict)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = [
    "Outline",
    "OutlineAssetBinding",
    "ReviewComment",
    "SectionDraft",
]
