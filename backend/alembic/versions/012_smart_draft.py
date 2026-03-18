"""012 smart draft traceability and chat

Add traceability_json + traceability_stale to section_drafts.
Create draft_chat_sessions + draft_chat_messages tables.
"""

from alembic import op
import sqlalchemy as sa

revision = "012_smart_draft"
down_revision = "011_g4_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- section_drafts enhancements ---
    op.add_column(
        "section_drafts",
        sa.Column("traceability_json", sa.JSON(), nullable=True, server_default="[]"),
    )
    op.add_column(
        "section_drafts",
        sa.Column(
            "traceability_stale",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # --- draft_chat_sessions ---
    op.create_table(
        "draft_chat_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "system_id",
            sa.String(36),
            sa.ForeignKey("experimental_systems.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_key", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="claude"),
        sa.Column("provider_session_id", sa.String(255), nullable=True),
        sa.Column("work_dir", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "system_id", "section_key", "provider",
            name="uq_draft_chat_sessions_system_section_provider",
        ),
    )

    # --- draft_chat_messages ---
    op.create_table(
        "draft_chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("draft_chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(50), nullable=False, server_default="completed"),
        sa.Column("turn_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Index(
            "ix_draft_chat_messages_session_turn",
            "session_id", "turn_index",
            unique=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("draft_chat_messages")
    op.drop_table("draft_chat_sessions")
    op.drop_column("section_drafts", "traceability_stale")
    op.drop_column("section_drafts", "traceability_json")
