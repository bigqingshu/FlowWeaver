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


class EventRouter:
    def __init__(self, runtime_store) -> None:
        self._runtime_store = runtime_store
        self._subscribers: set[asyncio.Queue[RuntimeEvent]] = set()

    async def subscribe(self) -> asyncio.Queue[RuntimeEvent]:
        queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[RuntimeEvent]) -> None:
        self._subscribers.discard(queue)

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
        sequence_number = self._runtime_store.append_runtime_event(event)
        runtime_event = RuntimeEvent(sequence_number=sequence_number, event=event)
        for queue in list(self._subscribers):
            queue.put_nowait(runtime_event)
        return runtime_event
