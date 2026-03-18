from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.base import AuditMixin, Base, UUIDPrimaryKeyMixin
from app.persistence.types import JsonDict, LongText, ShortText


class Asset(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "assets"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    system_id: Mapped[str] = mapped_column(
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(ShortText, nullable=False)
    file_name: Mapped[str] = mapped_column(ShortText, nullable=False)
    storage_key: Mapped[str] = mapped_column(LongText, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(ShortText, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uploaded_by: Mapped[str] = mapped_column(ShortText, nullable=False)

    metadata_entry: Mapped[AssetMetadata | None] = relationship(
        back_populates="asset",
        uselist=False,
        cascade="all, delete-orphan",
    )


class AssetMetadata(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "asset_metadata"
    __table_args__ = (UniqueConstraint("asset_id", name="uq_asset_metadata_asset_id"),)

    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    semantic_description: Mapped[str | None] = mapped_column(LongText, nullable=True)
    source_description: Mapped[str | None] = mapped_column(LongText, nullable=True)
    instrument_info: Mapped[str | None] = mapped_column(LongText, nullable=True)
    sample_ids: Mapped[list[str] | None] = mapped_column(JsonDict, nullable=True)
    conditions_json: Mapped[dict[str, Any] | None] = mapped_column(JsonDict, nullable=True)
    qc_status: Mapped[str] = mapped_column(ShortText, nullable=False, default="pending")

    asset: Mapped[Asset] = relationship(back_populates="metadata_entry")
