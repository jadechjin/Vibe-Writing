from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.common.events import TaskEvent

logger = logging.getLogger(__name__)

_SENTINEL: TaskEvent | None = None


class TaskBroadcaster:
    """In-process pub/sub hub for TaskEvent distribution.

    Each subscriber gets its own asyncio.Queue so publishers never block
    and slow consumers are independently buffered.
    """

    def __init__(self, max_queue_size: int = 256) -> None:
        self._subscribers: dict[int, asyncio.Queue[TaskEvent | None]] = {}
        self._counter = 0
        self._lock = asyncio.Lock()
        self._max_queue_size = max_queue_size

    async def publish(self, event: TaskEvent) -> None:
        async with self._lock:
            stale: list[int] = []
            for sub_id, queue in self._subscribers.items():
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    stale.append(sub_id)
                    logger.warning("subscriber %d queue full, dropping", sub_id)
            for sub_id in stale:
                del self._subscribers[sub_id]

        if stale:
            logger.info("dropped %d stale subscriber(s)", len(stale))

    async def subscribe(self) -> int:
        async with self._lock:
            self._counter += 1
            sub_id = self._counter
            self._subscribers[sub_id] = asyncio.Queue(
                maxsize=self._max_queue_size,
            )
        return sub_id

    async def unsubscribe(self, sub_id: int) -> None:
        async with self._lock:
            queue = self._subscribers.pop(sub_id, None)
        if queue is not None:
            try:
                queue.put_nowait(_SENTINEL)
            except asyncio.QueueFull:
                pass

    @asynccontextmanager
    async def subscription(self) -> AsyncIterator[AsyncIterator[TaskEvent]]:
        sub_id = await self.subscribe()
        try:
            yield self._iter_events(sub_id)
        finally:
            await self.unsubscribe(sub_id)

    async def _iter_events(self, sub_id: int) -> AsyncIterator[TaskEvent]:
        async with self._lock:
            queue = self._subscribers.get(sub_id)
        if queue is None:
            return
        while True:
            event = await queue.get()
            if event is _SENTINEL:
                return
            yield event

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)
