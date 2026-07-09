from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request

from flowweaver.api.api_models import APIResponseModel, WorkflowRunRetryRequest
from flowweaver.api.dependencies import get_runtime_store, get_supervisor
from flowweaver.api.responses import error_response, ok_response
from flowweaver.api.workflow_run_start import start_workflow_run_for_request
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.supervisor import Supervisor

router = APIRouter()


@router.post(
    "/{workflow_run_id}/retry",
    status_code=201,
    response_model=APIResponseModel,
)
def retry_run(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    supervisor: Annotated[Supervisor, Depends(get_supervisor)],
    payload: Annotated[WorkflowRunRetryRequest | None, Body()] = None,
):
    run = store.get_workflow_run(workflow_run_id)
    if run is None:
        return error_response(
            request,
            error_code="WORKFLOW_RUN_NOT_FOUND",
            message="Workflow run not found",
            status_code=404,
        )
    trigger_source = (
        payload.trigger_source
        if payload is not None and payload.trigger_source is not None
        else run.trigger_source
    )
    return start_workflow_run_for_request(
        request,
        workflow_id=run.workflow_id,
        revision_id=run.revision_id,
        store=store,
        supervisor=supervisor,
        run_mode=run.run_mode,
        trigger_source=trigger_source,
        target_node_instance_id=run.target_node_instance_id,
    )


@router.post("/{workflow_run_id}/cancel", response_model=APIResponseModel)
def cancel_run(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    supervisor: Annotated[Supervisor, Depends(get_supervisor)],
):
    run = store.get_workflow_run(workflow_run_id)
    if run is None:
        return error_response(
            request,
            error_code="WORKFLOW_RUN_NOT_FOUND",
            message="Workflow run not found",
            status_code=404,
        )
    process = supervisor.request_workflow_cancel(workflow_run_id)
    if process is None:
        return error_response(
            request,
            error_code="WORKFLOW_PROCESS_NOT_FOUND",
            message="Workflow process not found",
            status_code=404,
        )
    return ok_response(request, process)
