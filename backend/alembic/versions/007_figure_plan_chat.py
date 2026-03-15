"""create figure_plan_chat_sessions and figure_plan_chat_messages tables

Revision ID: 007_figure_plan_chat
Revises: 006_figure_plan_skeleton_binding
Create Date: 2026-03-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "007_figure_plan_chat"
down_revision: str | None = "006_figure_plan_skeleton_binding"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "figure_plan_chat_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("figure_plan_id", sa.String(36), sa.ForeignKey("figure_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_session_id", sa.String(255), nullable=True),
        sa.Column("work_dir", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_figure_plan_chat_sessions_plan_provider",
        "figure_plan_chat_sessions",
        ["figure_plan_id", "provider"],
    )

    op.create_table(
        "figure_plan_chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("figure_plan_chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("status", sa.String(50), nullable=False, server_default="completed"),
        sa.Column("turn_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_text", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_figure_plan_chat_messages_session_turn",
        "figure_plan_chat_messages",
        ["session_id", "turn_index"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_figure_plan_chat_messages_session_turn",
        table_name="figure_plan_chat_messages",
    )
    op.drop_table("figure_plan_chat_messages")
    op.drop_constraint(
        "uq_figure_plan_chat_sessions_plan_provider",
        "figure_plan_chat_sessions",
        type_="unique",
    )
    op.drop_table("figure_plan_chat_sessions")
