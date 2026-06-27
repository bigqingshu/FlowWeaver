from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from workflow_platform.api.dependencies import get_runtime_store
from workflow_platform.api.responses import error_response, ok_response
from workflow_platform.engine.runtime_store import RuntimeStore

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.get("")
def list_runs(
    request: Request,
    workflow_id: str | None = None,
    status: list[str] | None = Query(default=None),
    store: RuntimeStore = Depends(get_runtime_store),
):
    return ok_response(
        request,
        store.list_workflow_runs(workflow_id=workflow_id, statuses=status),
    )


@router.get("/{workflow_run_id}")
def get_run(
    request: Request,
    workflow_run_id: str,
    store: RuntimeStore = Depends(get_runtime_store),
):
    run = store.get_workflow_run(workflow_run_id)
    if run is None:
        return error_response(
            request,
            error_code="WORKFLOW_RUN_NOT_FOUND",
            message="Workflow run not found",
            status_code=404,
        )
    return ok_response(request, run)
