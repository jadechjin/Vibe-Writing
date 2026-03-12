"""create structure_skeletons table

Revision ID: 004_structure_skeletons
Revises: 003_evidence_draft_workflow
Create Date: 2026-03-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004_structure_skeletons"
down_revision: str | None = "003_evidence_draft_workflow"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "structure_skeletons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("system_id", sa.String(36), sa.ForeignKey("experimental_systems.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("skeleton_json", sa.JSON, nullable=False),
        sa.Column("change_summary", sa.String, nullable=True),
        sa.Column("source_asset_ids", sa.JSON, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.UniqueConstraint("system_id", "version", name="uq_structure_skeletons_system_version"),
    )


def downgrade() -> None:
    op.drop_table("structure_skeletons")
