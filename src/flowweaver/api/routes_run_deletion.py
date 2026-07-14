from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from flowweaver.api.api_models import APIResponseModel
from flowweaver.api.dependencies import get_runtime_store
from flowweaver.api.responses import error_response, ok_response
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_workflow_run_deletion import (
    WorkflowRunDeletionError,
    delete_workflow_run,
)

router = APIRouter()


@router.delete("/{workflow_run_id}", response_model=APIResponseModel)
def delete_run(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    try:
        result = delete_workflow_run(store, workflow_run_id)
    except WorkflowRunDeletionError as exc:
        return error_response(
            request,
            error_code=exc.error_code,
            message=exc.message,
            status_code=404 if exc.error_code == "WORKFLOW_RUN_NOT_FOUND" else 409,
            details=exc.details,
        )
    return ok_response(
        request,
        {
            "workflow_run_id": result.workflow_run_id,
            "deleted": result.deleted,
        },
    )
