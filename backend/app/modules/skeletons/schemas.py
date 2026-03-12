from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SkeletonGenerateRequest(BaseModel):
    source_asset_ids: list[str] = Field(default_factory=list)
    user_intent: str = ""


class SkeletonReviseRequest(BaseModel):
    skeleton_id: str
    feedback: str


class SkeletonPatchRequest(BaseModel):
    skeleton_json: dict[str, Any] | None = None
    change_summary: str | None = None


class SkeletonSummary(BaseModel):
    id: str
    version: int
    status: str
    change_summary: str | None = None
    created_at: datetime


class SkeletonDetail(BaseModel):
    id: str
    system_id: str
    version: int
    skeleton_json: dict[str, Any]
    change_summary: str | None = None
    source_asset_ids: list[str]
    status: str
    confirmed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SkeletonConfirmResponse(BaseModel):
    skeleton: SkeletonDetail
    affected_claims: list[dict[str, str]] = Field(default_factory=list)
