from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import AuditMixin, Base, UUIDPrimaryKeyMixin
from app.persistence.types import JsonDict, ShortText


class AssetManifest(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "asset_manifests"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "system_id",
            "version",
            name="uq_asset_manifests_project_system_version",
        ),
    )

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    system_id: Mapped[str] = mapped_column(
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(ShortText, nullable=False, default="draft")
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JsonDict, nullable=False, default=dict)
