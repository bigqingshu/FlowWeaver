from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Request

from flowweaver.api.api_models import APIResponseModel, WorkflowRunRetryRequest
from flowweaver.api.dependencies import (
    check_origin,
    get_runtime_store,
    get_supervisor,
    get_table_provider_registry,
    require_api_token,
)
from flowweaver.api.responses import error_response, ok_response
from flowweaver.api.routes_run_loops import router as run_loops_router
from flowweaver.api.run_lookup import run_not_found as _run_not_found
from flowweaver.api.run_pagination import pagination_rejection
from flowweaver.api.run_review import build_run_review_payload
from flowweaver.api.run_table_cleanup import cleanup_table_refs_for_run
from flowweaver.api.workflow_run_start import start_workflow_run_for_request
from flowweaver.engine.runtime_store import (
    TERMINAL_WORKFLOW_STATUS_VALUES,
    RuntimeStore,
)
from flowweaver.engine.supervisor import Supervisor
from flowweaver.engine.table_provider_registry import TableProviderRegistry

router = APIRouter(
    prefix="/api/v1/runs",
    tags=["runs"],
    dependencies=[Depends(require_api_token), Depends(check_origin)],
)
router.include_router(run_loops_router)
_BACKGROUND_TRIGGER_SOURCE = "background_manual"


@router.get("", response_model=APIResponseModel)
def list_runs(
    request: Request,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    workflow_id: str | None = None,
    status: Annotated[list[str] | None, Query()] = None,
    run_mode: str | None = None,
    trigger_source: str | None = None,
    offset: int = 0,
    limit: int = 100,
):
    rejection = pagination_rejection(request, offset=offset, limit=limit)
    if rejection is not None:
        return rejection
    return ok_response(
        request,
        store.list_workflow_runs(
            workflow_id=workflow_id,
            statuses=status,
            run_mode=run_mode,
            trigger_source=trigger_source,
            offset=offset,
            limit=limit,
        ),
    )


@router.get("/background", response_model=APIResponseModel)
def list_background_runs(
    request: Request,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    workflow_id: str | None = None,
    status: Annotated[list[str] | None, Query()] = None,
    run_mode: str | None = None,
    offset: int = 0,
    limit: int = 100,
):
    rejection = pagination_rejection(request, offset=offset, limit=limit)
    if rejection is not None:
        return rejection
    return ok_response(
        request,
        store.list_workflow_runs(
            workflow_id=workflow_id,
            statuses=status,
            run_mode=run_mode,
            trigger_source=_BACKGROUND_TRIGGER_SOURCE,
            offset=offset,
            limit=limit,
        ),
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


@router.get("/{workflow_run_id}/review", response_model=APIResponseModel)
def get_run_review(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    run = store.get_workflow_run(workflow_run_id)
    if run is None:
        return _run_not_found(request)
    table_refs = store.list_table_refs_by_workflow_run(workflow_run_id)
    return ok_response(
        request,
        build_run_review_payload(
            run=run,
            node_runs=store.list_node_runs(workflow_run_id),
            table_refs=table_refs,
        ),
    )


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


@router.get("/{workflow_run_id}/nodes", response_model=APIResponseModel)
def list_run_nodes(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    run = store.get_workflow_run(workflow_run_id)
    if run is None:
        return _run_not_found(request)
    return ok_response(request, store.list_node_runs(workflow_run_id))


@router.get("/{workflow_run_id}/table-refs", response_model=APIResponseModel)
def list_run_table_refs(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    run = store.get_workflow_run(workflow_run_id)
    if run is None:
        return _run_not_found(request)
    return ok_response(request, store.list_table_refs_by_workflow_run(workflow_run_id))


@router.delete("/{workflow_run_id}/table-refs", response_model=APIResponseModel)
def cleanup_run_table_refs(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    provider_registry: Annotated[
        TableProviderRegistry,
        Depends(get_table_provider_registry),
    ],
):
    run = store.get_workflow_run(workflow_run_id)
    if run is None:
        return _run_not_found(request)
    if run.status not in TERMINAL_WORKFLOW_STATUS_VALUES:
        return error_response(
            request,
            error_code="WORKFLOW_RUN_NOT_TERMINAL",
            message="Workflow run must be terminal before table refs can be cleaned",
            status_code=409,
            details={"workflow_run_id": workflow_run_id, "status": run.status},
        )
    return ok_response(
        request,
        cleanup_table_refs_for_run(
            workflow_run_id=workflow_run_id,
            store=store,
            provider_registry=provider_registry,
        ),
    )
