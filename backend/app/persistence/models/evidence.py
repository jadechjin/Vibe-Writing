from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import TaskStatus
from app.persistence.base import AuditMixin, Base, UUIDPrimaryKeyMixin
from app.persistence.types import JsonDict


class FigurePlan(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "figure_plans"
    __table_args__ = (
        UniqueConstraint(
            "system_id",
            "figure_no",
            "version",
            name="uq_figure_plans_system_figure_version",
        ),
    )

    system_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    figure_no: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    data_needed_json: Mapped[list[dict[str, object]] | dict[str, object]] = mapped_column(
        JsonDict,
        nullable=False,
        default=list,
    )
    method_json: Mapped[dict[str, object]] = mapped_column(JsonDict, nullable=False, default=dict)
    acceptance_criteria_json: Mapped[list[dict[str, object]] | dict[str, object]] = mapped_column(
        JsonDict,
        nullable=False,
        default=list,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class FigurePlanAsset(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "figure_plan_assets"
    __table_args__ = (
        UniqueConstraint(
            "figure_plan_id",
            "asset_id",
            "role",
            name="uq_figure_plan_assets_binding",
        ),
    )

    figure_plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("figure_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AnalysisRun(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "analysis_runs"

    system_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TaskStatus.QUEUED.value,
    )
    input_payload_json: Mapped[dict[str, object]] = mapped_column(
        JsonDict,
        nullable=False,
        default=dict,
    )
    result_payload_json: Mapped[dict[str, object]] = mapped_column(
        JsonDict,
        nullable=False,
        default=dict,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Claim(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "claims"
    __table_args__ = (
        UniqueConstraint("system_id", "claim_id", "version", name="uq_claims_system_claim_version"),
    )

    system_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_id: Mapped[str] = mapped_column(String(100), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    section_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(50), nullable=False, default="unreviewed")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClaimEvidenceLink(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "claim_evidence_links"
    __table_args__ = (
        Index(
            "ix_claim_evidence_links_unique_without_run",
            "claim_record_id",
            "asset_id",
            unique=True,
            postgresql_where=text("analysis_run_id IS NULL"),
            sqlite_where=text("analysis_run_id IS NULL"),
        ),
        Index(
            "ix_claim_evidence_links_unique_with_run",
            "claim_record_id",
            "asset_id",
            "analysis_run_id",
            unique=True,
            postgresql_where=text("analysis_run_id IS NOT NULL"),
            sqlite_where=text("analysis_run_id IS NOT NULL"),
        ),
    )

    claim_record_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    statistical_support: Mapped[dict[str, object]] = mapped_column(
        JsonDict,
        nullable=False,
        default=dict,
    )
    analysis_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("analysis_runs.id"),
        nullable=True,
    )


__all__ = [
    "AnalysisRun",
    "Claim",
    "ClaimEvidenceLink",
    "FigurePlan",
    "FigurePlanAsset",
]
