"""create assets and manifest tables"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002_assets_manifest"
down_revision: str | None = "001_project_system"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("system_id", sa.String(length=36), nullable=False),
        sa.Column("asset_type", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("uploaded_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["system_id"], ["experimental_systems.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assets_project_id", "assets", ["project_id"])
    op.create_index("ix_assets_system_id", "assets", ["system_id"])

    op.create_table(
        "asset_metadata",
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("semantic_description", sa.Text(), nullable=True),
        sa.Column("source_description", sa.Text(), nullable=True),
        sa.Column("instrument_info", sa.Text(), nullable=True),
        sa.Column("sample_ids", sa.JSON(), nullable=True),
        sa.Column("conditions_json", sa.JSON(), nullable=True),
        sa.Column("qc_status", sa.String(length=255), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", name="uq_asset_metadata_asset_id"),
    )

    op.create_table(
        "asset_manifests",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("system_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=255), nullable=False, server_default="draft"),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["system_id"], ["experimental_systems.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "system_id",
            "version",
            name="uq_asset_manifests_project_system_version",
        ),
    )
    op.create_index("ix_asset_manifests_project_id", "asset_manifests", ["project_id"])
    op.create_index("ix_asset_manifests_system_id", "asset_manifests", ["system_id"])


def downgrade() -> None:
    op.drop_index("ix_asset_manifests_system_id", table_name="asset_manifests")
    op.drop_index("ix_asset_manifests_project_id", table_name="asset_manifests")
    op.drop_table("asset_manifests")
    op.drop_table("asset_metadata")
    op.drop_index("ix_assets_system_id", table_name="assets")
    op.drop_index("ix_assets_project_id", table_name="assets")
    op.drop_table("assets")
