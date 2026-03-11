from app.common.enums import EventType, TaskStatus
from app.common.events import TaskEvent


def test_task_event_serializes_frontend_contract_shape() -> None:
    event = TaskEvent(
        type=EventType.TASK_CREATED,
        taskId="task-1",
        workflowId="wf-1",
        projectId="proj-1",
        systemId="sys-1",
        status=TaskStatus.QUEUED,
        message="queued",
    )

    payload = event.model_dump(by_alias=True, mode="json")

    assert payload["taskId"] == "task-1"
    assert payload["workflowId"] == "wf-1"
    assert payload["projectId"] == "proj-1"
    assert payload["systemId"] == "sys-1"
    assert "timestamp" in payload
