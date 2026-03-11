from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import EventType, TaskStatus


class TaskEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: EventType | str
    task_id: str = Field(alias="taskId")
    workflow_id: str | None = Field(default=None, alias="workflowId")
    project_id: str = Field(alias="projectId")
    system_id: str | None = Field(default=None, alias="systemId")
    status: TaskStatus
    progress: int | None = Field(default=None, ge=0, le=100)
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)
