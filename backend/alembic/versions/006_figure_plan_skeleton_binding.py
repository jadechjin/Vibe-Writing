"""add skeleton binding columns to figure_plans

Revision ID: 006_figure_plan_skeleton_binding
Revises: 005_drop_sysdef_cols
Create Date: 2026-03-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "006_figure_plan_skeleton_binding"
down_revision: str | None = "005_drop_sysdef_cols"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLE = "figure_plans"


def upgrade() -> None:
    op.add_column(_TABLE, sa.Column("section_key", sa.String(100), nullable=True))
    op.add_column(_TABLE, sa.Column("skeleton_version", sa.Integer, nullable=True))
    op.add_column(_TABLE, sa.Column("brief_text", sa.Text, nullable=True))
    op.add_column(_TABLE, sa.Column("brief_confirmed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column(_TABLE, "brief_confirmed_at")
    op.drop_column(_TABLE, "brief_text")
    op.drop_column(_TABLE, "skeleton_version")
    op.drop_column(_TABLE, "section_key")
