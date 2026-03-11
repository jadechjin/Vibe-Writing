from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.common.enums import EventType, TaskStatus
from app.common.events import TaskEvent
from app.main import create_app
from app.api.websocket import _serialize_event
from app.realtime.broadcaster import TaskBroadcaster


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def broadcaster() -> TaskBroadcaster:
    return TaskBroadcaster(max_queue_size=8)


def _make_event(
    event_type: EventType = EventType.TASK_CREATED,
    task_id: str = "t1",
    project_id: str = "p1",
    status: TaskStatus = TaskStatus.QUEUED,
    message: str = "hello",
    **kwargs,
) -> TaskEvent:
    return TaskEvent(
        type=event_type,
        taskId=task_id,
        projectId=project_id,
        status=status,
        message=message,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Unit tests for TaskBroadcaster
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_subscribe_and_publish(broadcaster: TaskBroadcaster) -> None:
    sub_id = await broadcaster.subscribe()
    assert broadcaster.subscriber_count == 1

    event = _make_event()
    await broadcaster.publish(event)

    async with broadcaster._lock:
        queue = broadcaster._subscribers[sub_id]
    received = queue.get_nowait()
    assert received.task_id == "t1"


@pytest.mark.asyncio
async def test_unsubscribe_removes_subscriber(broadcaster: TaskBroadcaster) -> None:
    sub_id = await broadcaster.subscribe()
    assert broadcaster.subscriber_count == 1

    await broadcaster.unsubscribe(sub_id)
    assert broadcaster.subscriber_count == 0


@pytest.mark.asyncio
async def test_unsubscribe_idempotent(broadcaster: TaskBroadcaster) -> None:
    sub_id = await broadcaster.subscribe()
    await broadcaster.unsubscribe(sub_id)
    await broadcaster.unsubscribe(sub_id)
    assert broadcaster.subscriber_count == 0


@pytest.mark.asyncio
async def test_publish_to_multiple_subscribers(broadcaster: TaskBroadcaster) -> None:
    sub1 = await broadcaster.subscribe()
    sub2 = await broadcaster.subscribe()
    assert broadcaster.subscriber_count == 2

    event = _make_event(message="multi")
    await broadcaster.publish(event)

    async with broadcaster._lock:
        q1 = broadcaster._subscribers[sub1]
        q2 = broadcaster._subscribers[sub2]
    assert q1.get_nowait().message == "multi"
    assert q2.get_nowait().message == "multi"


@pytest.mark.asyncio
async def test_full_queue_drops_subscriber(broadcaster: TaskBroadcaster) -> None:
    small = TaskBroadcaster(max_queue_size=2)
    await small.subscribe()

    for i in range(3):
        await small.publish(_make_event(message=f"m{i}"))

    assert small.subscriber_count == 0


@pytest.mark.asyncio
async def test_subscription_context_manager(broadcaster: TaskBroadcaster) -> None:
    async with broadcaster.subscription() as events:
        assert broadcaster.subscriber_count == 1
        await broadcaster.publish(_make_event(message="ctx"))

        received: list[TaskEvent] = []
        try:
            ev = await asyncio.wait_for(events.__anext__(), timeout=1.0)
            received.append(ev)
        except (asyncio.TimeoutError, StopAsyncIteration):
            pass

        assert len(received) == 1
        assert received[0].message == "ctx"

    assert broadcaster.subscriber_count == 0


@pytest.mark.asyncio
async def test_publish_no_subscribers(broadcaster: TaskBroadcaster) -> None:
    await broadcaster.publish(_make_event())


@pytest.mark.asyncio
async def test_multiple_event_types(broadcaster: TaskBroadcaster) -> None:
    sub_id = await broadcaster.subscribe()

    events_to_send = [
        _make_event(event_type=EventType.TASK_CREATED, message="created"),
        _make_event(event_type=EventType.TASK_PROGRESS, status=TaskStatus.RUNNING, message="progress"),
        _make_event(event_type=EventType.TASK_SUCCEEDED, status=TaskStatus.SUCCEEDED, message="done"),
        _make_event(event_type=EventType.TASK_FAILED, status=TaskStatus.FAILED, message="failed"),
    ]

    for ev in events_to_send:
        await broadcaster.publish(ev)

    async with broadcaster._lock:
        queue = broadcaster._subscribers[sub_id]

    received = []
    while not queue.empty():
        received.append(queue.get_nowait())

    assert len(received) == 4
    assert received[0].type == EventType.TASK_CREATED
    assert received[1].type == EventType.TASK_PROGRESS
    assert received[2].type == EventType.TASK_SUCCEEDED
    assert received[3].type == EventType.TASK_FAILED


# ---------------------------------------------------------------------------
# Sentinel / idle-disconnect tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unsubscribe_wakes_blocked_iterator(broadcaster: TaskBroadcaster) -> None:
    """When unsubscribe is called while _iter_events is blocked on queue.get(),
    the sentinel wakes it and the iterator exits promptly."""
    collected: list[TaskEvent] = []

    async def _consume():
        async with broadcaster.subscription() as events:
            async for ev in events:
                collected.append(ev)

    task = asyncio.create_task(_consume())
    await asyncio.sleep(0.05)
    assert broadcaster.subscriber_count == 1

    await broadcaster.publish(_make_event(message="before-disconnect"))
    await asyncio.sleep(0.05)

    task.cancel()
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass

    assert broadcaster.subscriber_count == 0
    assert len(collected) == 1
    assert collected[0].message == "before-disconnect"


@pytest.mark.asyncio
async def test_subscription_cleanup_is_immediate(broadcaster: TaskBroadcaster) -> None:
    """Exiting the subscription context manager cleans up immediately,
    not lazily on next publish."""
    async with broadcaster.subscription() as events:
        assert broadcaster.subscriber_count == 1
        _ = events

    assert broadcaster.subscriber_count == 0
    await broadcaster.publish(_make_event(message="after-cleanup"))
    assert broadcaster.subscriber_count == 0


# ---------------------------------------------------------------------------
# Serialization tests (exclude_none, empty payload)
# ---------------------------------------------------------------------------

def test_serialize_event_excludes_none_fields() -> None:
    event = _make_event()
    data = _serialize_event(event)

    assert "taskId" in data
    assert "projectId" in data
    assert "workflowId" not in data
    assert "systemId" not in data
    assert "progress" not in data
    assert "payload" not in data


def test_serialize_event_keeps_non_empty_payload() -> None:
    event = _make_event(payload={"result_url": "/files/out.pdf"})
    data = _serialize_event(event)

    assert data["payload"] == {"result_url": "/files/out.pdf"}


def test_serialize_event_excludes_empty_payload() -> None:
    event = _make_event(payload={})
    data = _serialize_event(event)

    assert "payload" not in data


def test_serialize_event_keeps_zero_progress() -> None:
    event = _make_event(progress=0)
    data = _serialize_event(event)

    assert data["progress"] == 0


# ---------------------------------------------------------------------------
# Integration test: WebSocket endpoint
# ---------------------------------------------------------------------------

def test_ws_endpoint_registered() -> None:
    app = create_app()
    paths = {route.path for route in app.router.routes}
    assert "/ws/tasks" in paths


def test_ws_connect_and_receive_event() -> None:
    app = create_app()

    with TestClient(app) as client:
        bc = app.state.broadcaster
        with client.websocket_connect("/ws/tasks") as ws:
            event = _make_event(
                event_type=EventType.TASK_CREATED,
                task_id="ws-t1",
                message="ws test",
            )

            async def _publish():
                await bc.publish(event)

            asyncio.get_event_loop().run_until_complete(_publish())

            data = ws.receive_json(mode="text")
            assert data["taskId"] == "ws-t1"
            assert data["type"] == "task.created"
            assert data["message"] == "ws test"
            assert "workflowId" not in data
            assert "payload" not in data
