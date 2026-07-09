from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request

from flowweaver.api.api_models import (
    APIResponseModel,
    WorkflowRunBackgroundStartRequest,
    WorkflowRunStartRequest,
)
from flowweaver.api.dependencies import get_runtime_store, get_supervisor
from flowweaver.api.workflow_run_start import start_workflow_run_for_request
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.supervisor import Supervisor

router = APIRouter()


@router.post("/{workflow_id}/runs", status_code=201, response_model=APIResponseModel)
def start_workflow_run(
    request: Request,
    workflow_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    supervisor: Annotated[Supervisor, Depends(get_supervisor)],
    payload: Annotated[WorkflowRunStartRequest | None, Body()] = None,
):
    run_mode = payload.run_mode if payload is not None else "full"
    trigger_source = payload.trigger_source if payload is not None else "manual"
    target_node_instance_id = (
        payload.target_node_instance_id if payload is not None else None
    )
    return start_workflow_run_for_request(
        request,
        workflow_id=workflow_id,
        store=store,
        supervisor=supervisor,
        run_mode=run_mode,
        trigger_source=trigger_source,
        target_node_instance_id=target_node_instance_id,
    )


@router.post(
    "/{workflow_id}/background-runs",
    status_code=201,
    response_model=APIResponseModel,
)
def start_background_workflow_run(
    request: Request,
    workflow_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    supervisor: Annotated[Supervisor, Depends(get_supervisor)],
    payload: Annotated[WorkflowRunBackgroundStartRequest | None, Body()] = None,
):
    run_mode = payload.run_mode if payload is not None else "full"
    target_node_instance_id = (
        payload.target_node_instance_id if payload is not None else None
    )
    return start_workflow_run_for_request(
        request,
        workflow_id=workflow_id,
        store=store,
        supervisor=supervisor,
        run_mode=run_mode,
        trigger_source="background_manual",
        target_node_instance_id=target_node_instance_id,
    )
