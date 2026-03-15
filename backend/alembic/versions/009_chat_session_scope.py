"""add scope to figure_plan_chat_sessions

Revision ID: 009_chat_session_scope
Revises: 008_analysis_run_image_analysis
Create Date: 2026-03-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "009_chat_session_scope"
down_revision: str | None = "008_analysis_run_image_analysis"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLE = "figure_plan_chat_sessions"
_OLD_UQ = "uq_figure_plan_chat_sessions_plan_provider"
_NEW_UQ = "uq_figure_plan_chat_sessions_plan_provider_scope"


def upgrade() -> None:
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.add_column(
            sa.Column("scope", sa.String(length=50), nullable=False, server_default="planning")
        )
        batch_op.drop_constraint(_OLD_UQ, type_="unique")
        batch_op.create_unique_constraint(
            _NEW_UQ,
            ["figure_plan_id", "provider", "scope"],
        )


def downgrade() -> None:
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.drop_constraint(_NEW_UQ, type_="unique")
        batch_op.create_unique_constraint(
            _OLD_UQ,
            ["figure_plan_id", "provider"],
        )
        batch_op.drop_column("scope")
