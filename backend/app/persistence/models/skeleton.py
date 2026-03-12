from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import AuditMixin, Base, UUIDPrimaryKeyMixin
from app.persistence.types import JsonDict, LongText


class StructureSkeleton(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "structure_skeletons"
    __table_args__ = (
        UniqueConstraint(
            "system_id",
            "version",
            name="uq_structure_skeletons_system_version",
        ),
    )

    system_id: Mapped[str] = mapped_column(
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    skeleton_json: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=dict, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(LongText(), nullable=True)
    source_asset_ids: Mapped[list[str]] = mapped_column(JsonDict, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = ["StructureSkeleton"]
