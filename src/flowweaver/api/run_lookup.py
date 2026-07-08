from __future__ import annotations

from fastapi import Request

from flowweaver.api.responses import error_response
from flowweaver.engine.runtime_store import RuntimeStore


def run_not_found(request: Request):
    return error_response(
        request,
        error_code="WORKFLOW_RUN_NOT_FOUND",
        message="Workflow run not found",
        status_code=404,
    )


def reject_missing_run(
    request: Request,
    store: RuntimeStore,
    workflow_run_id: str,
):
    run = store.get_workflow_run(workflow_run_id)
    if run is None:
        return run_not_found(request)
    return None


def load_loop(
    request: Request,
    store: RuntimeStore,
    workflow_run_id: str,
    loop_run_id: str,
):
    rejection = reject_missing_run(request, store, workflow_run_id)
    if rejection is not None:
        return None, rejection
    loop = store.get_loop_run(loop_run_id)
    if loop is None or loop.workflow_run_id != workflow_run_id:
        return None, error_response(
            request,
            error_code="LOOP_RUN_NOT_FOUND",
            message="Loop run not found",
            status_code=404,
        )
    return loop, None


def load_loop_iteration(
    request: Request,
    store: RuntimeStore,
    workflow_run_id: str,
    loop_run_id: str,
    loop_iteration_id: str,
):
    _loop, rejection = load_loop(request, store, workflow_run_id, loop_run_id)
    if rejection is not None:
        return None, rejection
    iteration = store.get_loop_iteration_run(loop_iteration_id)
    if iteration is None or iteration.loop_run_id != loop_run_id:
        return None, error_response(
            request,
            error_code="LOOP_ITERATION_NOT_FOUND",
            message="Loop iteration not found",
            status_code=404,
        )
    return iteration, None
