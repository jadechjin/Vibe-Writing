from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


class ProjectCreateRequest(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    owner_id: str = Field(min_length=1, max_length=255)
    template_asset_id: str | None = Field(default=None, max_length=255)
    thesis_schema_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "owner_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("template_asset_id")
    @classmethod
    def normalize_template_asset_id(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class ProjectSystemSummary(CamelModel):
    id: str
    system_no: int
    title: str
    status: str
    section_count: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectListItem(CamelModel):
    id: str
    name: str
    owner_id: str
    status: str
    template_asset_id: str | None = None
    system_count: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectListItem):
    thesis_schema_json: dict[str, Any] = Field(default_factory=dict)
    systems: list[ProjectSystemSummary] = Field(default_factory=list)
