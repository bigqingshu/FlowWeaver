from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from flowweaver.api.api_models import APIResponseModel
from flowweaver.api.dependencies import get_runtime_store
from flowweaver.api.responses import error_response, ok_response
from flowweaver.engine.runtime_store import RuntimeStore

router = APIRouter()


@router.get("/{workflow_id}/revisions", response_model=APIResponseModel)
def list_workflow_revisions(
    request: Request,
    workflow_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    if store.get_workflow_definition(workflow_id) is None:
        return error_response(
            request,
            error_code="WORKFLOW_NOT_FOUND",
            message="Workflow not found",
            status_code=404,
        )
    return ok_response(request, store.list_workflow_revisions(workflow_id))


@router.get(
    "/{workflow_id}/revisions/{revision_id}",
    response_model=APIResponseModel,
)
def get_workflow_revision(
    request: Request,
    workflow_id: str,
    revision_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    revision = store.get_workflow_revision(revision_id)
    if revision is None or revision.workflow_id != workflow_id:
        return error_response(
            request,
            error_code="WORKFLOW_REVISION_NOT_FOUND",
            message="Workflow revision not found",
            status_code=404,
        )
    return ok_response(request, revision)
