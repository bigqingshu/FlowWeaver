from __future__ import annotations

import subprocess
from collections.abc import Callable, MutableMapping

from flowweaver.engine.runtime_store import RuntimeStore, WorkflowProcess


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
