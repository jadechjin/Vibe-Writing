"""extend analysis_runs for image analysis workbench

Revision ID: 008_analysis_run_image_analysis
Revises: 007_figure_plan_chat
Create Date: 2026-03-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "008_analysis_run_image_analysis"
down_revision: str | None = "007_figure_plan_chat"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLE = "analysis_runs"
_FK_NAME = "fk_analysis_runs_figure_plan_id_figure_plans"
_INDEX_NAME = "ix_analysis_runs_figure_plan_id"


def upgrade() -> None:
    op.add_column(_TABLE, sa.Column("figure_plan_id", sa.String(length=36), nullable=True))
    op.add_column(
        _TABLE,
        sa.Column(
            "analysis_type",
            sa.String(length=50),
            nullable=False,
            server_default="comprehensive",
        ),
    )
    op.create_foreign_key(
        _FK_NAME,
        _TABLE,
        "figure_plans",
        ["figure_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(_INDEX_NAME, _TABLE, ["figure_plan_id"], unique=False)


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name=_TABLE)
    op.drop_constraint(_FK_NAME, _TABLE, type_="foreignkey")
    op.drop_column(_TABLE, "analysis_type")
    op.drop_column(_TABLE, "figure_plan_id")
