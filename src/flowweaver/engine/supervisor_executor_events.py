from __future__ import annotations

import subprocess
from collections.abc import MutableMapping

from flowweaver.engine.event_router import EventRouter, RuntimeEvent
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.supervisor_child_processes import terminate_child_process
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


def close_executor_children(
    *,
    children: MutableMapping[str, subprocess.Popen],
    event_router: EventRouter | None,
    runtime_store: RuntimeStore,
    graceful_timeout_seconds: float = 2,
) -> None:
    for executor_id, child in list(children.items()):
        if child.poll() is None:
            terminate_child_process(
                child,
                graceful_timeout_seconds=graceful_timeout_seconds,
            )
        children.pop(executor_id, None)
        publish_executor_exited(
            event_router=event_router,
            runtime_store=runtime_store,
            executor_id=executor_id,
            exit_code=child.returncode if child.returncode is not None else 1,
            pid=child.pid,
        )
