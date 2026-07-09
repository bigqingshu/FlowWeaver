from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from flowweaver.api.api_models import APIResponseModel
from flowweaver.api.dependencies import get_runtime_store
from flowweaver.api.responses import ok_response
from flowweaver.api.run_lookup import load_loop as _load_loop
from flowweaver.api.run_lookup import load_loop_iteration as _load_loop_iteration
from flowweaver.api.run_lookup import reject_missing_run as _reject_missing_run
from flowweaver.engine.runtime_store import RuntimeStore

router = APIRouter()


@router.get("/{workflow_run_id}/loops", response_model=APIResponseModel)
def list_run_loops(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    status: Annotated[list[str] | None, Query()] = None,
):
    rejection = _reject_missing_run(request, store, workflow_run_id)
    if rejection is not None:
        return rejection
    return ok_response(
        request,
        store.list_loop_runs(workflow_run_id, statuses=status),
    )


@router.get(
    "/{workflow_run_id}/loops/{loop_run_id}",
    response_model=APIResponseModel,
)
def get_run_loop(
    request: Request,
    workflow_run_id: str,
    loop_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    loop, rejection = _load_loop(request, store, workflow_run_id, loop_run_id)
    if rejection is not None:
        return rejection
    return ok_response(request, loop)


@router.get(
    "/{workflow_run_id}/loops/{loop_run_id}/iterations",
    response_model=APIResponseModel,
)
def list_run_loop_iterations(
    request: Request,
    workflow_run_id: str,
    loop_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    status: Annotated[list[str] | None, Query()] = None,
):
    _loop, rejection = _load_loop(request, store, workflow_run_id, loop_run_id)
    if rejection is not None:
        return rejection
    return ok_response(
        request,
        store.list_loop_iteration_runs(loop_run_id, statuses=status),
    )


@router.get(
    "/{workflow_run_id}/loops/{loop_run_id}/iterations/{loop_iteration_id}",
    response_model=APIResponseModel,
)
def get_run_loop_iteration(
    request: Request,
    workflow_run_id: str,
    loop_run_id: str,
    loop_iteration_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    iteration, rejection = _load_loop_iteration(
        request,
        store,
        workflow_run_id,
        loop_run_id,
        loop_iteration_id,
    )
    if rejection is not None:
        return rejection
    return ok_response(request, iteration)


@router.get(
    "/{workflow_run_id}/loops/{loop_run_id}/iterations/{loop_iteration_id}/table-refs",
    response_model=APIResponseModel,
)
def list_run_loop_iteration_table_refs(
    request: Request,
    workflow_run_id: str,
    loop_run_id: str,
    loop_iteration_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    role: str | None = None,
):
    _iteration, rejection = _load_loop_iteration(
        request,
        store,
        workflow_run_id,
        loop_run_id,
        loop_iteration_id,
    )
    if rejection is not None:
        return rejection
    return ok_response(
        request,
        store.list_loop_iteration_table_refs(loop_iteration_id, role=role),
    )
