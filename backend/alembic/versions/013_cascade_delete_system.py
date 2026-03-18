"""013 add cascade delete to assets and asset_manifests FK

Change ondelete behavior for assets and asset_manifests foreign keys
(both system_id and project_id) plus asset_metadata.asset_id
from RESTRICT to CASCADE, enabling one-click deletion of projects
and experimental systems with all associated data.
"""

from alembic import op

revision = "013_cascade_delete_system"
down_revision = "012_smart_draft"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- assets.system_id: RESTRICT -> CASCADE ---
    op.drop_constraint("assets_system_id_fkey", "assets", type_="foreignkey")
    op.create_foreign_key(
        "assets_system_id_fkey",
        "assets",
        "experimental_systems",
        ["system_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- assets.project_id: RESTRICT -> CASCADE ---
    op.drop_constraint("assets_project_id_fkey", "assets", type_="foreignkey")
    op.create_foreign_key(
        "assets_project_id_fkey",
        "assets",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- asset_manifests.system_id: RESTRICT -> CASCADE ---
    op.drop_constraint("asset_manifests_system_id_fkey", "asset_manifests", type_="foreignkey")
    op.create_foreign_key(
        "asset_manifests_system_id_fkey",
        "asset_manifests",
        "experimental_systems",
        ["system_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- asset_manifests.project_id: RESTRICT -> CASCADE ---
    op.drop_constraint("asset_manifests_project_id_fkey", "asset_manifests", type_="foreignkey")
    op.create_foreign_key(
        "asset_manifests_project_id_fkey",
        "asset_manifests",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- asset_metadata.asset_id: RESTRICT -> CASCADE ---
    op.drop_constraint("asset_metadata_asset_id_fkey", "asset_metadata", type_="foreignkey")
    op.create_foreign_key(
        "asset_metadata_asset_id_fkey",
        "asset_metadata",
        "assets",
        ["asset_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("asset_metadata_asset_id_fkey", "asset_metadata", type_="foreignkey")
    op.create_foreign_key(
        "asset_metadata_asset_id_fkey",
        "asset_metadata",
        "assets",
        ["asset_id"],
        ["id"],
    )

    op.drop_constraint("asset_manifests_project_id_fkey", "asset_manifests", type_="foreignkey")
    op.create_foreign_key(
        "asset_manifests_project_id_fkey",
        "asset_manifests",
        "projects",
        ["project_id"],
        ["id"],
    )

    op.drop_constraint("asset_manifests_system_id_fkey", "asset_manifests", type_="foreignkey")
    op.create_foreign_key(
        "asset_manifests_system_id_fkey",
        "asset_manifests",
        "experimental_systems",
        ["system_id"],
        ["id"],
    )

    op.drop_constraint("assets_project_id_fkey", "assets", type_="foreignkey")
    op.create_foreign_key(
        "assets_project_id_fkey",
        "assets",
        "projects",
        ["project_id"],
        ["id"],
    )

    op.drop_constraint("assets_system_id_fkey", "assets", type_="foreignkey")
    op.create_foreign_key(
        "assets_system_id_fkey",
        "assets",
        "experimental_systems",
        ["system_id"],
        ["id"],
    )
