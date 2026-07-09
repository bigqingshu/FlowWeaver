from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from flowweaver.api.api_models import APIResponseModel
from flowweaver.api.dependencies import get_runtime_store
from flowweaver.api.responses import error_response, ok_response
from flowweaver.api.run_lookup import run_not_found as _run_not_found
from flowweaver.api.run_pagination import pagination_rejection
from flowweaver.api.run_review import build_run_review_payload
from flowweaver.engine.runtime_store import RuntimeStore

router = APIRouter()
_BACKGROUND_TRIGGER_SOURCE = "background_manual"


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
