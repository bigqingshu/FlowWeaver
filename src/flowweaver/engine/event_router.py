from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from flowweaver.protocols.enums import EventType
from flowweaver.protocols.events import EventModel


@dataclass(frozen=True)
class RuntimeEvent:
    sequence_number: int
    event: EventModel

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event.event_id,
            "sequence_number": self.sequence_number,
            "event_version": self.event.event_version,
            "event_type": self.event.event_type.value,
            "timestamp": self.event.timestamp.isoformat(),
            "workflow_run_id": self.event.workflow_run_id,
            "node_run_id": self.event.node_run_id,
            "payload": self.event.payload,
        }


@dataclass(frozen=True)
class _EventSubscriber:
    queue: asyncio.Queue[RuntimeEvent]
    loop: asyncio.AbstractEventLoop


class EventRouter:
    def __init__(self, runtime_store) -> None:
        self._runtime_store = runtime_store
        self._subscribers: dict[asyncio.Queue[RuntimeEvent], _EventSubscriber] = {}

    async def subscribe(self) -> asyncio.Queue[RuntimeEvent]:
        queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue()
        self._subscribers[queue] = _EventSubscriber(
            queue=queue,
            loop=asyncio.get_running_loop(),
        )
        return queue

    def unsubscribe(self, queue: asyncio.Queue[RuntimeEvent]) -> None:
        self._subscribers.pop(queue, None)

    async def publish(
        self,
        event_type: EventType,
        *,
        payload: dict[str, Any] | None = None,
        workflow_run_id: str | None = None,
        node_run_id: str | None = None,
    ) -> RuntimeEvent:
        event = EventModel(
            event_type=event_type,
            workflow_run_id=workflow_run_id,
            node_run_id=node_run_id,
            payload=payload or {},
        )
        return self.publish_event(event)

    def publish_event(self, event: EventModel) -> RuntimeEvent:
        sequence_number = self._runtime_store.append_runtime_event(event)
        runtime_event = RuntimeEvent(sequence_number=sequence_number, event=event)
        for subscriber in list(self._subscribers.values()):
            if subscriber.loop.is_closed():
                self.unsubscribe(subscriber.queue)
                continue
            subscriber.loop.call_soon_threadsafe(
                subscriber.queue.put_nowait,
                runtime_event,
            )
        return runtime_event
