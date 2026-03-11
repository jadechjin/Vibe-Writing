from sqlalchemy import UniqueConstraint

from app.persistence.models.asset import Asset, AssetMetadata
from app.persistence.models.manifest import AssetManifest


def test_asset_models_capture_upload_and_qc_fields() -> None:
    asset_columns = Asset.__table__.c
    metadata_columns = AssetMetadata.__table__.c

    assert Asset.__tablename__ == "assets"
    assert asset_columns.project_id.nullable is False
    assert asset_columns.system_id.nullable is False
    assert asset_columns.asset_type.nullable is False
    assert asset_columns.version.default.arg == 1
    assert asset_columns.uploaded_by.nullable is False

    assert AssetMetadata.__tablename__ == "asset_metadata"
    assert metadata_columns.sample_ids.nullable is True
    assert metadata_columns.conditions_json.nullable is True
    assert metadata_columns.qc_status.default.arg == "pending"

    unique_constraints = {
        constraint.name
        for constraint in AssetMetadata.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_asset_metadata_asset_id" in unique_constraints


def test_asset_manifest_is_independent_versioned_entity() -> None:
    manifest_columns = AssetManifest.__table__.c

    assert AssetManifest.__tablename__ == "asset_manifests"
    assert manifest_columns.project_id.nullable is False
    assert manifest_columns.system_id.nullable is False
    assert manifest_columns.version.nullable is False
    assert manifest_columns.status.default.arg == "draft"
    assert manifest_columns.manifest_json.nullable is False

    unique_constraints = {
        constraint.name
        for constraint in AssetManifest.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_asset_manifests_project_system_version" in unique_constraints
