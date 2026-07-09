from __future__ import annotations

import subprocess
import time
from collections.abc import Callable, MutableMapping

from flowweaver.engine.runtime_store import RuntimeStore, WorkflowProcess
from flowweaver.engine.supervisor_child_processes import terminate_child_process


def finish_workflow_process(
    runtime_store: RuntimeStore,
    process_id: str,
    *,
    exit_code: int,
    error: dict[str, str] | None = None,
) -> WorkflowProcess | None:
    process = runtime_store.mark_workflow_process_exited(
        process_id,
        exit_code=exit_code,
        error=error,
    )
    if process is not None and exit_code != 0:
        runtime_store.abort_workflow_run_for_process(
            process_id,
            reason="WORKFLOW_PROCESS_EXITED_ABNORMALLY",
        )
    return process


def handle_lost_workflow_process(
    runtime_store: RuntimeStore,
    children: MutableMapping[str, subprocess.Popen],
    process: WorkflowProcess,
    *,
    drain_runtime_events_for_process: Callable[[str], object],
    forget_runtime_event_channel: Callable[[str], None],
) -> None:
    drain_runtime_events_for_process(process.process_id)
    children.pop(process.process_id, None)
    forget_runtime_event_channel(process.process_id)
    runtime_store.abort_workflow_run_for_process(
        process.process_id,
        reason="WORKFLOW_PROCESS_LOST",
    )


def close_workflow_children(
    runtime_store: RuntimeStore,
    children: MutableMapping[str, subprocess.Popen],
    *,
    graceful_timeout_seconds: float,
    drain_runtime_events_for_process: Callable[[str], object],
    forget_runtime_event_channel: Callable[[str], None],
) -> None:
    for process_id, child in list(children.items()):
        forced = False
        if child.poll() is None:
            forced = True
            terminate_child_process(
                child,
                graceful_timeout_seconds=graceful_timeout_seconds,
            )
        drain_runtime_events_for_process(process_id)
        exit_code = child.returncode if child.returncode is not None else 1
        if forced and exit_code == 0:
            exit_code = 1
        children.pop(process_id, None)
        finish_workflow_process(
            runtime_store,
            process_id,
            exit_code=exit_code,
            error=(
                {"message": "Workflow process terminated during supervisor close"}
                if forced
                else None
            ),
        )
        forget_runtime_event_channel(process_id)


def stop_workflow_child(
    runtime_store: RuntimeStore,
    children: MutableMapping[str, subprocess.Popen],
    process: WorkflowProcess,
    child: subprocess.Popen,
    *,
    graceful_timeout_seconds: int,
    terminate_graceful_timeout_seconds: float,
    drain_runtime_events_for_process: Callable[[str], object],
    forget_runtime_event_channel: Callable[[str], None],
) -> None:
    deadline = time.monotonic() + graceful_timeout_seconds
    while time.monotonic() < deadline:
        if child.poll() is not None:
            drain_runtime_events_for_process(process.process_id)
            children.pop(process.process_id, None)
            finish_workflow_process(
                runtime_store,
                process.process_id,
                exit_code=child.returncode or 0,
            )
            forget_runtime_event_channel(process.process_id)
            return
        time.sleep(0.05)
    terminate_child_process(
        child,
        graceful_timeout_seconds=terminate_graceful_timeout_seconds,
    )
    drain_runtime_events_for_process(process.process_id)
    children.pop(process.process_id, None)
    finish_workflow_process(
        runtime_store,
        process.process_id,
        exit_code=child.returncode if child.returncode not in (None, 0) else 1,
        error={"message": "Workflow process terminated after cancel timeout"},
    )
    forget_runtime_event_channel(process.process_id)
