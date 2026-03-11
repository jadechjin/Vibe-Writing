"""create project and system tables

Revision ID: 001_project_system
Revises:
Create Date: 2026-03-07 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001_project_system"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


PROJECT_STATUS_LENGTH = 32
PROJECT_MEMBER_ROLE_LENGTH = 32
SYSTEM_STATUS_LENGTH = 64


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=PROJECT_STATUS_LENGTH),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("template_asset_id", sa.String(length=255), nullable=True),
        sa.Column("thesis_schema_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"], unique=False)
    op.create_index(op.f("ix_projects_status"), "projects", ["status"], unique=False)

    op.create_table(
        "project_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.String(length=PROJECT_MEMBER_ROLE_LENGTH),
            nullable=False,
            server_default="editor",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )
    op.create_index(
        op.f("ix_project_members_project_id"),
        "project_members",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_members_user_id"),
        "project_members",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "experimental_systems",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("system_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("research_goal", sa.String(), nullable=True),
        sa.Column("samples_subjects", sa.String(), nullable=True),
        sa.Column("variables_controls", sa.String(), nullable=True),
        sa.Column("output_metrics", sa.String(), nullable=True),
        sa.Column("methods_summary", sa.String(), nullable=True),
        sa.Column("system_card_json", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=SYSTEM_STATUS_LENGTH),
            nullable=False,
            server_default="Draft",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "system_no",
            name="uq_experimental_systems_project_system_no",
        ),
    )
    op.create_index(
        op.f("ix_experimental_systems_project_id"),
        "experimental_systems",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_experimental_systems_status"),
        "experimental_systems",
        ["status"],
        unique=False,
    )

    op.create_table(
        "system_sections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("system_id", sa.String(length=36), nullable=False),
        sa.Column("section_key", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["system_id"], ["experimental_systems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "system_id",
            "order_no",
            name="uq_system_sections_system_order_no",
        ),
        sa.UniqueConstraint(
            "system_id",
            "section_key",
            name="uq_system_sections_system_section_key",
        ),
    )
    op.create_index(
        op.f("ix_system_sections_system_id"),
        "system_sections",
        ["system_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_system_sections_system_id"), table_name="system_sections")
    op.drop_table("system_sections")

    op.drop_index(op.f("ix_experimental_systems_status"), table_name="experimental_systems")
    op.drop_index(op.f("ix_experimental_systems_project_id"), table_name="experimental_systems")
    op.drop_table("experimental_systems")

    op.drop_index(op.f("ix_project_members_user_id"), table_name="project_members")
    op.drop_index(op.f("ix_project_members_project_id"), table_name="project_members")
    op.drop_table("project_members")

    op.drop_index(op.f("ix_projects_status"), table_name="projects")
    op.drop_index(op.f("ix_projects_owner_id"), table_name="projects")
    op.drop_table("projects")
