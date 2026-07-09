from __future__ import annotations

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
