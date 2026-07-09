from __future__ import annotations

from flowweaver.engine.event_router import EventRouter, RuntimeEvent
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import EventType
from flowweaver.protocols.events import EventModel


def publish_executor_exited(
    *,
    event_router: EventRouter | None,
    runtime_store: RuntimeStore,
    executor_id: str,
    exit_code: int,
    pid: int | None,
) -> RuntimeEvent | None:
    event = EventModel(
        event_type=EventType.EXECUTOR_EXITED,
        payload={
            "executor_id": executor_id,
            "exit_code": exit_code,
            "pid": pid,
            "abnormal": exit_code != 0,
        },
    )
    if event_router is not None:
        return event_router.publish_event(event)
    runtime_store.append_runtime_event(event)
    return None
