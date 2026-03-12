from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.schemas import JobHandle


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


class AssetUploadRequest(CamelModel):
    system_id: str = Field(min_length=1, max_length=255)
    asset_type: str = Field(min_length=1, max_length=255)
    file_name: str = Field(min_length=1, max_length=255)
    storage_key: str = Field(min_length=1)
    mime_type: str | None = Field(default=None, max_length=255)
    uploaded_by: str = Field(min_length=1, max_length=255)

    @field_validator("system_id", "asset_type", "file_name", "storage_key", "uploaded_by")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("mime_type")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AssetBindRequest(CamelModel):
    semantic_description: str | None = Field(default=None, max_length=5000)
    source_description: str | None = Field(default=None, max_length=5000)
    instrument_info: str | None = Field(default=None, max_length=5000)
    sample_ids: list[str] | None = None
    conditions_json: dict[str, Any] | None = None
    qc_status: str | None = Field(default=None, max_length=255)
    analysis_run_id: str | None = Field(default=None, max_length=255)

    @field_validator(
        "semantic_description",
        "source_description",
        "instrument_info",
        "analysis_run_id",
    )
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("qc_status")
    @classmethod
    def validate_qc_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in {"pending", "confirmed", "approved"}:
            raise ValueError("must be one of: pending, confirmed, approved")
        return normalized

    @field_validator("sample_ids")
    @classmethod
    def normalize_sample_ids(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = [item.strip() for item in value if item.strip()]
        return normalized or []


class AssetMetadataDetail(CamelModel):
    id: str
    asset_id: str
    semantic_description: str | None = None
    source_description: str | None = None
    instrument_info: str | None = None
    sample_ids: list[str] | None = None
    conditions_json: dict[str, Any] | None = None
    qc_status: str
    created_at: datetime
    updated_at: datetime


class AssetListItem(CamelModel):
    id: str
    project_id: str
    system_id: str
    asset_type: str
    file_name: str
    storage_key: str
    mime_type: str | None = None
    version: int
    uploaded_by: str
    created_at: datetime
    updated_at: datetime


class AssetDetail(AssetListItem):
    metadata_entry: AssetMetadataDetail | None = None


class ManifestDetail(CamelModel):
    id: str
    project_id: str
    system_id: str
    version: int
    status: str
    manifest_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ManifestCreateRequest(CamelModel):
    status: str = Field(default="draft", max_length=50)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"draft", "confirmed", "approved"}:
            raise ValueError("must be one of: draft, confirmed, approved")
        return normalized


class ManifestCreateAcceptedResponse(CamelModel):
    handle: JobHandle


class AnalysisRunDetail(CamelModel):
    id: str
    system_id: str
    asset_id: str | None = None
    run_type: str
    status: str
    input_payload_json: dict[str, Any] = Field(default_factory=dict)
    result_payload_json: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    version: int
    started_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AnalysisRunCreateRequest(CamelModel):
    run_type: str = Field(default="default", min_length=1, max_length=100)
    config: dict[str, Any] | None = None


class AnalysisRunCompleteRequest(CamelModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"succeeded", "failed"}:
            raise ValueError("must be one of: succeeded, failed")
        return normalized

    result_summary: str | None = None


class AnalysisRunCreateAcceptedResponse(CamelModel):
    handle: JobHandle


class ManifestConfirmResponse(CamelModel):
    id: str
    system_id: str
    status: str
    confirmed_at: datetime


class AssetQCConfirmResponse(CamelModel):
    id: str
    asset_id: str
    qc_status: str
    confirmed_at: datetime


class BatchConfirmAssetQCRequest(CamelModel):
    asset_ids: list[str]


class BatchConfirmAssetQCResponse(CamelModel):
    succeeded: list[str]
    failed: list[dict[str, str]]


__all__ = [
    "AnalysisRunCompleteRequest",
    "AnalysisRunCreateAcceptedResponse",
    "AnalysisRunCreateRequest",
    "AnalysisRunDetail",
    "AssetBindRequest",
    "AssetDetail",
    "AssetListItem",
    "AssetMetadataDetail",
    "AssetQCConfirmResponse",
    "AssetUploadRequest",
    "BatchConfirmAssetQCRequest",
    "BatchConfirmAssetQCResponse",
    "ManifestConfirmResponse",
    "ManifestCreateAcceptedResponse",
    "ManifestCreateRequest",
    "ManifestDetail",
]
