from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import ReviewDecision
from app.common.schemas import JobHandle


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


class OutlineDetail(CamelModel):
    id: str
    system_id: str
    version: int
    outline_json: dict[str, Any] | list[dict[str, Any]] = Field(default_factory=dict)
    generated_from_claims_json: list[str] = Field(default_factory=list)
    status: str
    bindings: list[OutlineBindingDetail] = Field(default_factory=list)
    staleness_warning: str | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class OutlineGenerateRequest(CamelModel):
    pass


class OutlineConfirmRequest(CamelModel):
    status: Literal["confirmed"] = "confirmed"


class OutlineBindingDetail(CamelModel):
    id: str
    outline_id: str
    section_key: str
    asset_id: str
    binding_note: str | None = None
    created_at: datetime
    updated_at: datetime


class OutlineBindingCreateRequest(CamelModel):
    asset_id: str
    section_key: str
    description: str | None = None


class OutlineGenerateAcceptedResponse(CamelModel):
    handle: JobHandle


class SectionDraftDetail(CamelModel):
    id: str
    system_id: str
    outline_id: str | None = None
    section_key: str
    version: int
    content_md: str
    generated_from_claims_json: list[str] = Field(default_factory=list)
    status: str
    review_comments: list[ReviewCommentDetail] = Field(default_factory=list)
    created_by_agent: str | None = None
    approved_at: datetime | None = None
    frozen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SectionDraftGenerateRequest(CamelModel):
    outline_id: str | None = None
    # HC-13: only consume approved claims — enforced by service layer
    claim_ids: list[str] = Field(default_factory=list)


class SectionDraftApproveRequest(CamelModel):
    status: Literal["approved"] = "approved"


class SectionDraftGenerateAcceptedResponse(CamelModel):
    handle: JobHandle


class ReviewCommentDetail(CamelModel):
    id: str
    draft_id: str
    commenter_id: str
    comment_text: str
    decision: str | None = None
    context_json: dict[str, Any] = Field(default_factory=dict)
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReviewCommentCreateRequest(CamelModel):
    commenter_id: str
    comment_text: str
    decision: ReviewDecision | None = None
    context_json: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "OutlineBindingCreateRequest",
    "OutlineBindingDetail",
    "OutlineConfirmRequest",
    "OutlineDetail",
    "OutlineGenerateAcceptedResponse",
    "OutlineGenerateRequest",
    "ReviewCommentCreateRequest",
    "ReviewCommentDetail",
    "SectionDraftApproveRequest",
    "SectionDraftDetail",
    "SectionDraftGenerateAcceptedResponse",
    "SectionDraftGenerateRequest",
]
