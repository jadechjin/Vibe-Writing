from app.persistence import models as persistence_models
from app.persistence.base import Base

REQUIRED_TABLES = {
    "projects",
    "project_members",
    "experimental_systems",
    "system_sections",
    "assets",
    "asset_metadata",
    "asset_manifests",
    "figure_plans",
    "claims",
    "outlines",
    "section_drafts",
    "workflow_instances",
}


def test_models_package_registers_core_tables_on_import() -> None:
    assert persistence_models.Project.__tablename__ == "projects"
    assert REQUIRED_TABLES.issubset(Base.metadata.tables.keys())
