from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from flowweaver.api.api_models import APIResponseModel
from flowweaver.api.dependencies import get_runtime_store
from flowweaver.api.responses import ok_response
from flowweaver.api.run_lookup import load_loop as _load_loop
from flowweaver.api.run_lookup import load_loop_iteration as _load_loop_iteration
from flowweaver.api.run_lookup import reject_missing_run as _reject_missing_run
from flowweaver.api.run_pagination import pagination_rejection
from flowweaver.api.runtime_loop_responses import (
    loop_iteration_node_run_to_jsonable,
    loop_iteration_table_ref_to_jsonable,
)
from flowweaver.engine.runtime_store import RuntimeStore

router = APIRouter()


@router.get("/{workflow_run_id}/loops", response_model=APIResponseModel)
def list_run_loops(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    status: Annotated[list[str] | None, Query()] = None,
    offset: int = 0,
    limit: int = 50,
):
    rejection = pagination_rejection(request, offset=offset, limit=limit)
    if rejection is not None:
        return rejection
    rejection = _reject_missing_run(request, store, workflow_run_id)
    if rejection is not None:
        return rejection
    return ok_response(
        request,
        store.list_loop_runs(
            workflow_run_id,
            statuses=status,
            offset=offset,
            limit=limit,
        ),
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
    offset: int = 0,
    limit: int = 50,
):
    rejection = pagination_rejection(request, offset=offset, limit=limit)
    if rejection is not None:
        return rejection
    _loop, rejection = _load_loop(request, store, workflow_run_id, loop_run_id)
    if rejection is not None:
        return rejection
    return ok_response(
        request,
        store.list_loop_iteration_runs(
            loop_run_id,
            statuses=status,
            offset=offset,
            limit=limit,
        ),
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
    links = store.list_loop_iteration_table_refs(loop_iteration_id, role=role)
    refs_by_id = {
        table_ref.table_ref_id: table_ref
        for table_ref in store.list_table_refs_by_ids(
            [link.table_ref_id for link in links]
        )
    }
    return ok_response(
        request,
        [
            loop_iteration_table_ref_to_jsonable(
                link,
                refs_by_id.get(link.table_ref_id),
            )
            for link in links
        ],
    )


@router.get(
    "/{workflow_run_id}/loops/{loop_run_id}/iterations/{loop_iteration_id}/nodes",
    response_model=APIResponseModel,
)
def list_run_loop_iteration_nodes(
    request: Request,
    workflow_run_id: str,
    loop_run_id: str,
    loop_iteration_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
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
    links = store.list_loop_iteration_node_runs(loop_iteration_id)
    node_runs_by_id = {
        node_run.node_run_id: node_run
        for node_run in store.list_node_runs_by_ids(
            [link.node_run_id for link in links]
        )
    }
    return ok_response(
        request,
        [
            loop_iteration_node_run_to_jsonable(link, node_runs_by_id[link.node_run_id])
            for link in links
            if link.node_run_id in node_runs_by_id
        ],
    )
