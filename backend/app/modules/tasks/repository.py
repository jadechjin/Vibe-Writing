from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models.workflow import WorkflowEvent, WorkflowInstance


class TaskWorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_instance(self, instance: WorkflowInstance) -> WorkflowInstance:
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def add_event(self, event: WorkflowEvent) -> WorkflowEvent:
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def get_instance(self, workflow_id: str) -> WorkflowInstance | None:
        statement = select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_instance_for_system(
        self,
        *,
        system_id: str,
        workflow_key: str | None = None,
    ) -> WorkflowInstance | None:
        statement: Select[tuple[WorkflowInstance]] = (
            select(WorkflowInstance)
            .where(WorkflowInstance.system_id == system_id)
            .order_by(WorkflowInstance.created_at.desc(), WorkflowInstance.version.desc())
        )
        if workflow_key is not None:
            statement = statement.where(WorkflowInstance.workflow_key == workflow_key)
        result = await self._session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_events(self, workflow_id: str) -> Sequence[WorkflowEvent]:
        statement = (
            select(WorkflowEvent)
            .join(WorkflowInstance, WorkflowInstance.id == WorkflowEvent.instance_id)
            .where(WorkflowInstance.id == workflow_id)
            .order_by(WorkflowEvent.created_at.asc(), WorkflowEvent.id.asc())
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_next_version(
        self,
        *,
        project_id: str,
        system_id: str,
        workflow_key: str,
    ) -> int:
        statement = (
            select(WorkflowInstance.version)
            .where(
                WorkflowInstance.project_id == project_id,
                WorkflowInstance.system_id == system_id,
                WorkflowInstance.workflow_key == workflow_key,
            )
            .order_by(WorkflowInstance.version.desc())
        )
        result = await self._session.execute(statement.limit(1))
        latest_version = result.scalar_one_or_none()
        return (latest_version or 0) + 1


__all__ = ["TaskWorkflowRepository"]
