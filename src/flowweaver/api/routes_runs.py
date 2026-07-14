from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from flowweaver.api.api_models import APIResponseModel
from flowweaver.api.dependencies import (
    check_origin,
    get_runtime_store,
    require_api_token,
)
from flowweaver.api.responses import ok_response
from flowweaver.api.routes_run_actions import router as run_actions_router
from flowweaver.api.routes_run_deletion import router as run_deletion_router
from flowweaver.api.routes_run_loops import router as run_loops_router
from flowweaver.api.routes_run_queries import router as run_queries_router
from flowweaver.api.routes_run_runtime_options import (
    router as run_runtime_options_router,
)
from flowweaver.api.routes_run_tables import router as run_tables_router
from flowweaver.api.run_pagination import pagination_rejection
from flowweaver.engine.runtime_store import RuntimeStore

router = APIRouter(
    prefix="/api/v1/runs",
    tags=["runs"],
    dependencies=[Depends(require_api_token), Depends(check_origin)],
)
router.include_router(run_loops_router)
router.include_router(run_actions_router)
router.include_router(run_deletion_router)
router.include_router(run_tables_router)
router.include_router(run_queries_router)
router.include_router(run_runtime_options_router)


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


