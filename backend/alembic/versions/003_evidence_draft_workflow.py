"""create evidence, draft, and workflow tables

Revision ID: 003_evidence_draft_workflow
Revises: 002_assets_manifest
Create Date: 2026-03-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003_evidence_draft_workflow"
down_revision: str | None = "002_assets_manifest"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "figure_plans",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("system_id", sa.String(length=36), nullable=False),
        sa.Column("figure_no", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("data_needed_json", sa.JSON(), nullable=False),
        sa.Column("method_json", sa.JSON(), nullable=False),
        sa.Column("acceptance_criteria_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["system_id"], ["experimental_systems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "system_id",
            "figure_no",
            "version",
            name="uq_figure_plans_system_figure_version",
        ),
    )

    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("system_id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=True),
        sa.Column("run_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("input_payload_json", sa.JSON(), nullable=False),
        sa.Column("result_payload_json", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["system_id"], ["experimental_systems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "claims",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("system_id", sa.String(length=36), nullable=False),
        sa.Column("claim_id", sa.String(length=100), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("section_ref", sa.String(length=100), nullable=False),
        sa.Column("confidence_level", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["system_id"], ["experimental_systems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "system_id",
            "claim_id",
            "version",
            name="uq_claims_system_claim_version",
        ),
    )

    op.create_table(
        "outlines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("system_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("outline_json", sa.JSON(), nullable=False),
        sa.Column("generated_from_claims_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["system_id"], ["experimental_systems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("system_id", "version", name="uq_outlines_system_version"),
    )

    op.create_table(
        "workflow_instances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("system_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_key", sa.String(length=100), nullable=False),
        sa.Column("current_state", sa.String(length=100), nullable=False),
        sa.Column("current_gate", sa.String(length=10), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("context_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["system_id"], ["experimental_systems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "system_id",
            "workflow_key",
            "version",
            name="uq_workflow_instances_scope_key_version",
        ),
    )

    op.create_table(
        "figure_plan_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("figure_plan_id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["figure_plan_id"], ["figure_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "figure_plan_id",
            "asset_id",
            "role",
            name="uq_figure_plan_assets_binding",
        ),
    )

    op.create_table(
        "claim_evidence_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("claim_record_id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("statistical_support", sa.JSON(), nullable=False),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_record_id"], ["claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_claim_evidence_links_unique_without_run",
        "claim_evidence_links",
        ["claim_record_id", "asset_id"],
        unique=True,
        postgresql_where=sa.text("analysis_run_id IS NULL"),
        sqlite_where=sa.text("analysis_run_id IS NULL"),
    )
    op.create_index(
        "ix_claim_evidence_links_unique_with_run",
        "claim_evidence_links",
        ["claim_record_id", "asset_id", "analysis_run_id"],
        unique=True,
        postgresql_where=sa.text("analysis_run_id IS NOT NULL"),
        sqlite_where=sa.text("analysis_run_id IS NOT NULL"),
    )

    op.create_table(
        "outline_asset_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("outline_id", sa.String(length=36), nullable=False),
        sa.Column("section_key", sa.String(length=100), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("binding_note", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outline_id"], ["outlines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "outline_id",
            "section_key",
            "asset_id",
            name="uq_outline_asset_bindings_target",
        ),
    )

    op.create_table(
        "section_drafts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("system_id", sa.String(length=36), nullable=False),
        sa.Column("outline_id", sa.String(length=36), nullable=True),
        sa.Column("section_key", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("generated_from_claims_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_by_agent", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["outline_id"], ["outlines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["system_id"], ["experimental_systems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "system_id",
            "section_key",
            "version",
            name="uq_section_drafts_system_section_version",
        ),
    )

    op.create_table(
        "workflow_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("instance_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("from_state", sa.String(length=100), nullable=True),
        sa.Column("to_state", sa.String(length=100), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["instance_id"], ["workflow_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "review_comments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("draft_id", sa.String(length=36), nullable=False),
        sa.Column("commenter_id", sa.String(length=255), nullable=False),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(length=50), nullable=True),
        sa.Column("context_json", sa.JSON(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["draft_id"], ["section_drafts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "approval_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("system_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_instance_id", sa.String(length=36), nullable=True),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("reviewer_id", sa.String(length=255), nullable=True),
        sa.Column("decision", sa.String(length=50), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["system_id"], ["experimental_systems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workflow_instance_id"],
            ["workflow_instances.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("approval_tasks")
    op.drop_table("review_comments")
    op.drop_table("workflow_events")
    op.drop_table("section_drafts")
    op.drop_table("outline_asset_bindings")
    op.drop_index(
        "ix_claim_evidence_links_unique_with_run",
        table_name="claim_evidence_links",
    )
    op.drop_index(
        "ix_claim_evidence_links_unique_without_run",
        table_name="claim_evidence_links",
    )
    op.drop_table("claim_evidence_links")
    op.drop_table("figure_plan_assets")
    op.drop_table("workflow_instances")
    op.drop_table("outlines")
    op.drop_table("claims")
    op.drop_table("analysis_runs")
    op.drop_table("figure_plans")
