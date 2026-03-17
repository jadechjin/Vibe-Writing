from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import AuditMixin, Base, UUIDPrimaryKeyMixin
from app.persistence.types import JsonDict


class G4Snapshot(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "g4_snapshots"

    system_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fingerprint: Mapped[str] = mapped_column(String(16), nullable=False)
    skeleton_version: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plan_versions_json: Mapped[dict[str, Any]] = mapped_column(
        JsonDict, nullable=False, default=dict
    )
    asset_versions_json: Mapped[dict[str, Any]] = mapped_column(
        JsonDict, nullable=False, default=dict
    )
    run_versions_json: Mapped[dict[str, Any]] = mapped_column(
        JsonDict, nullable=False, default=dict
    )


__all__ = ["G4Snapshot"]
