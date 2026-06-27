from __future__ import annotations

from pathlib import Path
from typing import Protocol

from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.ipc_messages import IPCEnvelope


class RuntimeEventSink(Protocol):
    def emit(self, event: EventModel) -> None:
        ...


class DatabaseEventSink:
    def __init__(self, runtime_store) -> None:
        self._runtime_store = runtime_store

    def emit(self, event: EventModel) -> None:
        self._runtime_store.append_runtime_event(event)


class IPCEventSink:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: EventModel) -> None:
        envelope = IPCEnvelope(
            message_type=IPCMessageType.RUNTIME_EVENT,
            workflow_run_id=event.workflow_run_id,
            node_run_id=event.node_run_id,
            payload=event.model_dump(mode="json"),
        )
        with self._path.open("a", encoding="utf-8") as stream:
            stream.write(envelope.model_dump_json())
            stream.write("\n")
