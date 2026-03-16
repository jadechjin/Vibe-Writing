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


class AnalysisRunSummary(CamelModel):
    id: str
    status: str
    summary: str | None = None
    confidence: float | None = None
    updated_at: datetime | None = None


class FigurePlanAssetDetail(CamelModel):
    id: str
    file_name: str
    mime_type: str | None = None
    preview_url: str | None = None


class ImageAnalysisItem(CamelModel):
    figure_plan_id: str
    figure_no: str
    title: str
    section_key: str | None = None
    data_question: str | None = None
    evidence_text: str | None = None
    assets: list[FigurePlanAssetDetail] = Field(default_factory=list)
    latest_analysis: AnalysisRunSummary | None = None


class ImageAnalysisListResponse(CamelModel):
    items: list[ImageAnalysisItem] = Field(default_factory=list)
    total: int
    analyzed: int
    pending: int


class AnalysisRunCreateRequest(CamelModel):
    run_type: str = Field(default="default", min_length=1, max_length=100)
    config: dict[str, Any] | None = None


class FigurePlanAnalyzeRequest(CamelModel):
    asset_id: str = Field(min_length=1, max_length=255)
    analysis_type: str = Field(default="comprehensive", min_length=1, max_length=50)

    @field_validator("asset_id", "analysis_type")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


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


class ManifestPlanAsset(CamelModel):
    id: str
    file_name: str
    asset_type: str
    mime_type: str | None = None
    qc_status: str | None = None


class ManifestPlanAnalysis(CamelModel):
    id: str
    status: str
    summary: str | None = None


class ManifestFigurePlanEntry(CamelModel):
    figure_plan_id: str
    figure_no: str
    title: str
    section_key: str | None = None
    data_question: str | None = None
    evidence_text: str | None = None
    assets: list[ManifestPlanAsset] = Field(default_factory=list)
    latest_analysis: ManifestPlanAnalysis | None = None
    completeness: str


class ManifestIssue(CamelModel):
    severity: str
    rule: str
    scope: str
    message: str
    detail: str | None = None
    resolution: str | None = None


class ManifestSummaryStats(CamelModel):
    total_plans: int
    complete_plans: int
    incomplete_plans: int
    total_assets: int
    confirmed_assets: int
    orphan_assets: int
    blocker_count: int
    warning_count: int


class ManifestPreviewResponse(CamelModel):
    system_id: str
    summary: ManifestSummaryStats
    figure_plans: list[ManifestFigurePlanEntry] = Field(default_factory=list)
    orphan_assets: list[ManifestPlanAsset] = Field(default_factory=list)
    issues: list[ManifestIssue] = Field(default_factory=list)
    manifest: ManifestDetail | None = None


__all__ = [
    "AnalysisRunCompleteRequest",
    "AnalysisRunCreateAcceptedResponse",
    "AnalysisRunCreateRequest",
    "AnalysisRunDetail",
    "AnalysisRunSummary",
    "AssetBindRequest",
    "AssetDetail",
    "AssetListItem",
    "AssetMetadataDetail",
    "AssetQCConfirmResponse",
    "AssetUploadRequest",
    "BatchConfirmAssetQCRequest",
    "BatchConfirmAssetQCResponse",
    "FigurePlanAnalyzeRequest",
    "FigurePlanAssetDetail",
    "ImageAnalysisItem",
    "ImageAnalysisListResponse",
    "ManifestConfirmResponse",
    "ManifestCreateAcceptedResponse",
    "ManifestCreateRequest",
    "ManifestDetail",
    "ManifestFigurePlanEntry",
    "ManifestIssue",
    "ManifestPlanAnalysis",
    "ManifestPlanAsset",
    "ManifestPreviewResponse",
    "ManifestSummaryStats",
]
