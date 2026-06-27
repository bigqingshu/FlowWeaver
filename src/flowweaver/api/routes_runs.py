from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from flowweaver.api.api_models import APIResponseModel
from flowweaver.api.dependencies import (
    check_origin,
    get_runtime_store,
    require_api_token,
)
from flowweaver.api.responses import error_response, ok_response
from flowweaver.engine.runtime_store import RuntimeStore

router = APIRouter(
    prefix="/api/v1/runs",
    tags=["runs"],
    dependencies=[Depends(require_api_token), Depends(check_origin)],
)


@router.get("", response_model=APIResponseModel)
def list_runs(
    request: Request,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    workflow_id: str | None = None,
    status: Annotated[list[str] | None, Query()] = None,
):
    return ok_response(
        request,
        store.list_workflow_runs(workflow_id=workflow_id, statuses=status),
    )


@router.get("/{workflow_run_id}", response_model=APIResponseModel)
def get_run(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
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
