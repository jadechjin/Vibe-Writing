"""create g4_snapshots table

Revision ID: 011_g4_snapshot
Revises: 010_figure_plan_data_question
Create Date: 2026-03-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "011_g4_snapshot"
down_revision: str | None = "010_figure_plan_data_question"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLE = "g4_snapshots"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "system_id",
            sa.String(36),
            sa.ForeignKey("experimental_systems.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("fingerprint", sa.String(16), nullable=False),
        sa.Column("skeleton_version", sa.Integer(), nullable=False),
        sa.Column("manifest_version", sa.Integer(), nullable=True),
        sa.Column("plan_versions_json", sa.JSON(), nullable=False),
        sa.Column("asset_versions_json", sa.JSON(), nullable=False),
        sa.Column("run_versions_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_table(_TABLE)
