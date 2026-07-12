from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from flowweaver.api.api_models import APIResponseModel
from flowweaver.api.dependencies import (
    get_runtime_store,
    get_table_provider_registry,
)
from flowweaver.api.responses import error_response, ok_response
from flowweaver.api.run_lookup import run_not_found as _run_not_found
from flowweaver.api.run_pagination import (
    paginated_ok_response,
    pagination_rejection,
)
from flowweaver.api.run_table_cleanup import cleanup_table_refs_for_run
from flowweaver.api.table_ref_responses import (
    table_ref_summary_to_jsonable,
    table_ref_to_jsonable,
)
from flowweaver.engine.runtime_store import (
    TERMINAL_WORKFLOW_STATUS_VALUES,
    RuntimeStore,
)
from flowweaver.engine.table_provider_registry import TableProviderRegistry

router = APIRouter()

_TABLE_TYPES = {
    "current_table",
    "memory_table",
    "runtime_sql_table",
    "external_sql_table",
}


@router.get("/{workflow_run_id}/nodes", response_model=APIResponseModel)
def list_run_nodes(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    status: Annotated[list[str] | None, Query()] = None,
    offset: int = 0,
    limit: int = 100,
    paged: bool = False,
):
    rejection = pagination_rejection(request, offset=offset, limit=limit)
    if rejection is not None:
        return rejection
    run = store.get_workflow_run(workflow_run_id)
    if run is None:
        return _run_not_found(request)
    items = store.list_node_runs(
        workflow_run_id,
        statuses=status,
        offset=offset,
        limit=limit,
    )
    total = store.count_node_runs(workflow_run_id, statuses=status)
    return paginated_ok_response(
        request,
        items=items,
        offset=offset,
        limit=limit,
        total=total,
        paged=paged,
    )


@router.get("/{workflow_run_id}/table-refs", response_model=APIResponseModel)
def list_run_table_refs(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    node_run_id: str | None = None,
    table_type: str | None = None,
    lifecycle: Annotated[list[str] | None, Query()] = None,
    logical_table_id: str | None = None,
    offset: int = 0,
    limit: int = 100,
    paged: bool = False,
):
    rejection = pagination_rejection(request, offset=offset, limit=limit)
    if rejection is not None:
        return rejection
    if table_type is not None and table_type not in _TABLE_TYPES:
        return error_response(
            request,
            error_code="INVALID_TABLE_TYPE",
            message="table_type is not supported",
            status_code=422,
            details={"table_type": table_type},
        )
    run = store.get_workflow_run(workflow_run_id)
    if run is None:
        return _run_not_found(request)
    entries = store.list_table_ref_directory(
        workflow_run_id,
        node_run_id=node_run_id,
        table_type=table_type,
        lifecycle_statuses=lifecycle,
        logical_table_id=logical_table_id,
        offset=offset,
        limit=limit,
    )
    total = store.count_table_ref_directory(
        workflow_run_id,
        node_run_id=node_run_id,
        table_type=table_type,
        lifecycle_statuses=lifecycle,
        logical_table_id=logical_table_id,
    )
    if paged:
        items = [
            table_ref_summary_to_jsonable(
                entry.table_ref,
                source_node_instance_id=entry.source_node_instance_id,
                result_bindings=entry.result_bindings,
            )
            for entry in entries
        ]
    else:
        items = [
            table_ref_to_jsonable(
                entry.table_ref,
                source_node_instance_id=entry.source_node_instance_id,
                result_bindings=entry.result_bindings,
            )
            for entry in entries
        ]
    return paginated_ok_response(
        request,
        items=items,
        offset=offset,
        limit=limit,
        total=total,
        paged=paged,
    )


@router.delete("/{workflow_run_id}/table-refs", response_model=APIResponseModel)
def cleanup_run_table_refs(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    provider_registry: Annotated[
        TableProviderRegistry,
        Depends(get_table_provider_registry),
    ],
    cursor: str | None = None,
    max_refs: Annotated[int, Query(ge=1, le=1000)] = 100,
    time_budget_ms: Annotated[int, Query(ge=1, le=10000)] = 1000,
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
    try:
        result = cleanup_table_refs_for_run(
            workflow_run_id=workflow_run_id,
            store=store,
            provider_registry=provider_registry,
            cursor=cursor,
            max_refs=max_refs,
            time_budget_ms=time_budget_ms,
        )
    except ValueError as exc:
        return error_response(
            request,
            error_code="INVALID_CLEANUP_CURSOR",
            message=str(exc),
            status_code=422,
        )
    return ok_response(request, result)
