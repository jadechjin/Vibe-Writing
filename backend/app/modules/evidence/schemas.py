from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.common.schemas import JobHandle


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class FigurePlanDetail(CamelModel):
    id: str
    system_id: str
    figure_no: str
    title: str
    claim_text: str
    data_needed_json: list[dict[str, Any]] | dict[str, Any] = Field(default_factory=list)
    method_json: dict[str, Any] = Field(default_factory=dict)
    acceptance_criteria_json: list[dict[str, Any]] | dict[str, Any] = Field(default_factory=list)
    status: str
    version: int
    section_key: str | None = None
    skeleton_version: int | None = None
    brief_text: str | None = None
    brief_confirmed_at: datetime | None = None
    data_question: str | None = None
    evidence_text: str | None = None
    created_at: datetime
    updated_at: datetime


class FigurePlanGenerateRequest(CamelModel):
    pass


class FigurePlanConfirmRequest(CamelModel):
    status: Literal["confirmed"] = "confirmed"


class FigurePlanUpdateBriefRequest(CamelModel):
    brief_text: str


class FigurePlanPatchRequest(CamelModel):
    figure_no: str | None = None
    title: str | None = None
    claim_text: str | None = None
    section_key: str | None = None
    data_needed_json: list[dict[str, Any]] | dict[str, Any] | None = None
    method_json: dict[str, Any] | None = None
    acceptance_criteria_json: list[dict[str, Any]] | dict[str, Any] | None = None
    brief_text: str | None = None
    data_question: str | None = None
    evidence_text: str | None = None


class FigurePlanStatusTransitionRequest(CamelModel):
    status: str


class FigurePlanGenerateAcceptedResponse(CamelModel):
    handle: JobHandle


# ---------------------------------------------------------------------------
# Claim & ClaimEvidenceLink schemas (Task 9 – G4)
# ---------------------------------------------------------------------------


class ClaimDetail(CamelModel):
    id: str
    system_id: str
    claim_id: str
    statement: str
    section_ref: str
    confidence_level: str
    status: str
    version: int
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ClaimEvidenceLinkDetail(CamelModel):
    id: str
    claim_record_id: str
    asset_id: str
    analysis_run_id: str | None = None
    statistical_support: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ClaimApproveRequest(CamelModel):
    status: Literal["approved"] = "approved"


class ClaimEvidenceLinkCreateRequest(CamelModel):
    asset_id: str
    analysis_run_id: str | None = None
    statistical_support: dict[str, Any] = Field(default_factory=dict)


class EvidenceMatrixGenerateAcceptedResponse(CamelModel):
    handle: JobHandle


class BatchApproveClaimsRequest(CamelModel):
    claim_ids: list[str]


class BatchApproveClaimsResponse(CamelModel):
    succeeded: list[str]
    failed: list[dict[str, str]]


# ---------------------------------------------------------------------------
# FigurePlanAsset schemas (G1 – image upload)
# ---------------------------------------------------------------------------


class FigurePlanAssetDetail(CamelModel):
    id: str
    figure_plan_id: str
    asset_id: str
    role: str
    position: int
    file_name: str
    mime_type: str | None = None
    preview_url: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# FigurePlanChat schemas (G1 – agent chat)
# ---------------------------------------------------------------------------


class ChatProvider(str, Enum):
    claude = "claude"
    codex = "codex"
    gemini = "gemini"


class ChatMessageDetail(CamelModel):
    id: str
    session_id: str
    role: str
    content: str
    status: str
    turn_index: int
    error_text: str | None = None
    created_at: datetime


class ChatMessageCreateRequest(CamelModel):
    provider: ChatProvider
    content: str
    scope: str = Field(default="planning", min_length=1, max_length=50)


class ChatImageUploadResponse(CamelModel):
    local_path: str
    file_name: str
    preview_url: str | None = None


__all__ = [
    "BatchApproveClaimsRequest",
    "BatchApproveClaimsResponse",
    "ChatImageUploadResponse",
    "ChatMessageCreateRequest",
    "ChatMessageDetail",
    "ChatProvider",
    "ClaimApproveRequest",
    "ClaimDetail",
    "ClaimEvidenceLinkCreateRequest",
    "ClaimEvidenceLinkDetail",
    "EvidenceMatrixGenerateAcceptedResponse",
    "FigurePlanAssetDetail",
    "FigurePlanConfirmRequest",
    "FigurePlanDetail",
    "FigurePlanGenerateAcceptedResponse",
    "FigurePlanGenerateRequest",
    "FigurePlanPatchRequest",
    "FigurePlanStatusTransitionRequest",
    "FigurePlanUpdateBriefRequest",
]
