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
    section_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    skeleton_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    brief_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    brief_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    data_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)


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
    __table_args__ = (Index("ix_analysis_runs_figure_plan_id", "figure_plan_id"),)

    system_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("experimental_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    figure_plan_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("figure_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    asset_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_type: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="comprehensive",
        server_default=text("'comprehensive'"),
    )
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


class FigurePlanChatSession(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "figure_plan_chat_sessions"
    __table_args__ = (
        UniqueConstraint(
            "figure_plan_id",
            "provider",
            "scope",
            name="uq_figure_plan_chat_sessions_plan_provider_scope",
        ),
    )

    figure_plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("figure_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    scope: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="planning",
        server_default=text("'planning'"),
    )
    provider_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_dir: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FigurePlanChatMessage(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "figure_plan_chat_messages"
    __table_args__ = (
        Index(
            "ix_figure_plan_chat_messages_session_turn",
            "session_id",
            "turn_index",
            unique=True,
        ),
    )

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("figure_plan_chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)


__all__ = [
    "AnalysisRun",
    "Claim",
    "ClaimEvidenceLink",
    "FigurePlan",
    "FigurePlanAsset",
    "FigurePlanChatMessage",
    "FigurePlanChatSession",
]
