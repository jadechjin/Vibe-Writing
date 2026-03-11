from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.common.schemas import JobHandle


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


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
    created_at: datetime
    updated_at: datetime


class FigurePlanGenerateRequest(CamelModel):
    pass


class FigurePlanConfirmRequest(CamelModel):
    status: Literal["confirmed"] = "confirmed"


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


__all__ = [
    "ClaimApproveRequest",
    "ClaimDetail",
    "ClaimEvidenceLinkCreateRequest",
    "ClaimEvidenceLinkDetail",
    "EvidenceMatrixGenerateAcceptedResponse",
    "FigurePlanConfirmRequest",
    "FigurePlanDetail",
    "FigurePlanGenerateAcceptedResponse",
    "FigurePlanGenerateRequest",
]
