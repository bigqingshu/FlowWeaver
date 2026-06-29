from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from flowweaver.api.api_models import APIResponseModel
from flowweaver.api.dependencies import (
    check_origin,
    get_runtime_store,
    require_api_token,
)
from flowweaver.api.responses import ok_response
from flowweaver.engine.runtime_store import RuntimeStore

router = APIRouter(
    prefix="/api/v1/audit-events",
    tags=["audit-events"],
    dependencies=[Depends(require_api_token), Depends(check_origin)],
)


@router.get("", response_model=APIResponseModel)
def list_audit_events(
    request: Request,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    workflow_run_id: str | None = None,
    node_run_id: str | None = None,
    event_type: str | None = None,
):
    return ok_response(
        request,
        store.list_audit_events(
            workflow_run_id=workflow_run_id,
            node_run_id=node_run_id,
            event_type=event_type,
        ),
    )
