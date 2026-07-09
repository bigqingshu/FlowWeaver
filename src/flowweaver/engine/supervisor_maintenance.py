from __future__ import annotations

import subprocess
from collections.abc import Callable, MutableMapping
from datetime import timedelta

from flowweaver.common.config import EngineConfig
from flowweaver.common.time import utc_now
from flowweaver.engine.event_router import EventRouter
from flowweaver.engine.runtime_store import RuntimeStore, WorkflowProcess
from flowweaver.engine.supervisor_executor_events import (
    publish_executor_exited as _publish_executor_exited,
)
from flowweaver.engine.supervisor_workflow_processes import (
    handle_lost_workflow_process as _handle_lost_workflow_process,
)


def sweep_exited_workflow_children(
    *,
    children: MutableMapping[str, subprocess.Popen],
    finish_workflow_process: Callable[..., WorkflowProcess | None],
    drain_runtime_events_for_process: Callable[[str], object],
    forget_runtime_event_channel: Callable[[str], None],
) -> list[WorkflowProcess]:
    exited: list[WorkflowProcess] = []
    for process_id, child in list(children.items()):
        exit_code = child.poll()
        if exit_code is None:
            continue
        drain_runtime_events_for_process(process_id)
        children.pop(process_id, None)
        process = finish_workflow_process(process_id, exit_code=exit_code)
        drain_runtime_events_for_process(process_id)
        forget_runtime_event_channel(process_id)
        if process is not None:
            exited.append(process)
    return exited


def sweep_exited_executor_children(
    *,
    children: MutableMapping[str, subprocess.Popen],
    event_router: EventRouter | None,
    runtime_store: RuntimeStore,
) -> list[str]:
    exited: list[str] = []
    for executor_id, child in list(children.items()):
        exit_code = child.poll()
        if exit_code is None:
            continue
        children.pop(executor_id, None)
        _publish_executor_exited(
            event_router=event_router,
            runtime_store=runtime_store,
            executor_id=executor_id,
            exit_code=exit_code,
            pid=child.pid,
        )
        exited.append(executor_id)
    return exited


def mark_lost_workflow_processes(
    *,
    config: EngineConfig,
    runtime_store: RuntimeStore,
    children: MutableMapping[str, subprocess.Popen],
    drain_runtime_events_for_process: Callable[[str], object],
    forget_runtime_event_channel: Callable[[str], None],
) -> list[WorkflowProcess]:
    stale_before = utc_now() - timedelta(
        seconds=config.workflow_process_lost_threshold_seconds
    )
    starting_stale_before = utc_now() - timedelta(
        seconds=config.workflow_process_start_timeout_seconds
    )
    lost = runtime_store.mark_lost_workflow_processes(
        stale_before=stale_before,
        starting_stale_before=starting_stale_before,
    )
    for process in lost:
        _handle_lost_workflow_process(
            runtime_store,
            children,
            process,
            drain_runtime_events_for_process=drain_runtime_events_for_process,
            forget_runtime_event_channel=forget_runtime_event_channel,
        )
    return lost
