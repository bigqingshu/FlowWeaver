from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from workflow_platform.api.api_models import (
    WorkflowCreateRequest,
    WorkflowUpdateRequest,
)
from workflow_platform.api.dependencies import get_runtime_store
from workflow_platform.api.responses import error_response, ok_response
from workflow_platform.engine.runtime_store import RuntimeStore

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


@router.get("")
def list_workflows(
    request: Request,
    store: RuntimeStore = Depends(get_runtime_store),
):
    return ok_response(request, store.list_workflow_definitions())


@router.post("", status_code=201)
def create_workflow(
    request: Request,
    payload: WorkflowCreateRequest,
    store: RuntimeStore = Depends(get_runtime_store),
):
    workflow = store.create_workflow_definition(
        name=payload.name,
        definition=payload.definition,
    )
    return ok_response(request, workflow, status_code=201)


@router.get("/{workflow_id}")
def get_workflow(
    request: Request,
    workflow_id: str,
    store: RuntimeStore = Depends(get_runtime_store),
):
    workflow = store.get_workflow_definition(workflow_id)
    if workflow is None:
        return error_response(
            request,
            error_code="WORKFLOW_NOT_FOUND",
            message="Workflow not found",
            status_code=404,
        )
    return ok_response(request, workflow)


@router.put("/{workflow_id}")
def update_workflow(
    request: Request,
    workflow_id: str,
    payload: WorkflowUpdateRequest,
    store: RuntimeStore = Depends(get_runtime_store),
):
    workflow = store.update_workflow_definition(
        workflow_id,
        name=payload.name,
        definition=payload.definition,
    )
    if workflow is None:
        return error_response(
            request,
            error_code="WORKFLOW_NOT_FOUND",
            message="Workflow not found",
            status_code=404,
        )
    return ok_response(request, workflow)


@router.delete("/{workflow_id}")
def delete_workflow(
    request: Request,
    workflow_id: str,
    store: RuntimeStore = Depends(get_runtime_store),
):
    if not store.delete_workflow_definition(workflow_id):
        return error_response(
            request,
            error_code="WORKFLOW_NOT_FOUND",
            message="Workflow not found",
            status_code=404,
        )
    return ok_response(request, {"workflow_id": workflow_id, "deleted": True})
