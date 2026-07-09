from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from flowweaver.api.api_models import APIResponseModel
from flowweaver.api.dependencies import (
    get_runtime_store,
    get_table_provider_registry,
)
from flowweaver.api.responses import error_response, ok_response
from flowweaver.api.run_lookup import run_not_found as _run_not_found
from flowweaver.api.run_table_cleanup import cleanup_table_refs_for_run
from flowweaver.engine.runtime_store import (
    TERMINAL_WORKFLOW_STATUS_VALUES,
    RuntimeStore,
)
from flowweaver.engine.table_provider_registry import TableProviderRegistry

router = APIRouter()


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
