from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.realtime.broadcaster import TaskBroadcaster

logger = logging.getLogger(__name__)

websocket_router = APIRouter()


def get_broadcaster(request: Request) -> TaskBroadcaster:
    broadcaster: TaskBroadcaster | None = getattr(request.app.state, "broadcaster", None)
    if broadcaster is None:
        raise RuntimeError("No broadcaster available; app lifespan may not have started")
    return broadcaster


def _serialize_event(event: Any) -> dict[str, Any]:
    data = event.model_dump(by_alias=True, mode="json", exclude_none=True)
    if not data.get("payload"):
        data.pop("payload", None)
    return data


@websocket_router.websocket("/ws/tasks")
async def tasks_websocket(websocket: WebSocket) -> None:
    broadcaster: TaskBroadcaster | None = getattr(websocket.app.state, "broadcaster", None)
    if broadcaster is None:
        await websocket.close(code=1011, reason="broadcaster unavailable")
        return

    await websocket.accept()

    async with broadcaster.subscription() as events:
        try:
            async for event in events:
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                await websocket.send_json(_serialize_event(event))
        except WebSocketDisconnect:
            logger.debug("client disconnected from /ws/tasks")
        except Exception:
            logger.exception("unexpected error on /ws/tasks")
        finally:
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except Exception:
                    pass
