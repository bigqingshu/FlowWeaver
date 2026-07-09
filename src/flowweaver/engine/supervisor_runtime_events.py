from __future__ import annotations

import threading
from pathlib import Path

from flowweaver.engine.event_router import EventRouter, RuntimeEvent
from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.ipc_messages import IPCEnvelope


class SupervisorRuntimeEventChannels:
    def __init__(self, event_router: EventRouter | None) -> None:
        self._event_router = event_router
        self._paths: dict[str, Path] = {}
        self._offsets: dict[str, int] = {}
        self._lock = threading.Lock()

    def register(self, process_id: str, path: Path) -> None:
        self._paths[process_id] = path
        self._offsets[process_id] = 0

    def forget(self, process_id: str) -> None:
        self._paths.pop(process_id, None)
        self._offsets.pop(process_id, None)

    def drain_all(self) -> list[RuntimeEvent]:
        events: list[RuntimeEvent] = []
        for process_id in list(self._paths):
            events.extend(self.drain_process(process_id))
        return events

    def drain_process(self, process_id: str) -> list[RuntimeEvent]:
        with self._lock:
            if self._event_router is None:
                return []
            path = self._paths.get(process_id)
            if path is None or not path.exists():
                return []
            offset = self._offsets.get(process_id, 0)
            published: list[RuntimeEvent] = []
            with path.open("r", encoding="utf-8") as stream:
                stream.seek(offset)
                for line in stream:
                    if not line.strip():
                        continue
                    envelope = IPCEnvelope.model_validate_json(line)
                    if envelope.message_type != IPCMessageType.RUNTIME_EVENT:
                        continue
                    event = EventModel.model_validate(envelope.payload)
                    published.append(self._event_router.publish_event(event))
                self._offsets[process_id] = stream.tell()
            return published
