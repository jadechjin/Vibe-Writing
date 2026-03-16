"""add data_question and evidence_text to figure_plans

Revision ID: 010_figure_plan_data_question
Revises: 009_chat_session_scope
Create Date: 2026-03-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "010_figure_plan_data_question"
down_revision: str | None = "009_chat_session_scope"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLE = "figure_plans"


def upgrade() -> None:
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.add_column(sa.Column("data_question", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("evidence_text", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.drop_column("evidence_text")
        batch_op.drop_column("data_question")
