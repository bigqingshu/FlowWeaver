from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from flowweaver.api.api_models import (
    APIResponseModel,
    WorkflowCreateRequest,
    WorkflowUpdateRequest,
    WorkflowValidateRequest,
)
from flowweaver.api.dependencies import (
    check_origin,
    get_node_registry,
    get_runtime_store,
    require_api_token,
)
from flowweaver.api.responses import error_response, ok_response
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.nodes.registry import NodeRegistry
from flowweaver.workflow.validation import validate_workflow_definition

router = APIRouter(
    prefix="/api/v1/workflows",
    tags=["workflows"],
    dependencies=[Depends(require_api_token), Depends(check_origin)],
)


@router.get("", response_model=APIResponseModel)
def list_workflows(
    request: Request,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    return ok_response(request, store.list_workflow_definitions())


@router.post("", status_code=201, response_model=APIResponseModel)
def create_workflow(
    request: Request,
    payload: WorkflowCreateRequest,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    registry: Annotated[NodeRegistry, Depends(get_node_registry)],
):
    validation = validate_workflow_definition(payload.definition, registry)
    if not validation.valid:
        return error_response(
            request,
            error_code="WORKFLOW_VALIDATION_FAILED",
            message="Workflow definition is invalid",
            status_code=422,
            details=validation.model_dump(mode="json"),
        )
    workflow = store.create_workflow_definition(
        name=payload.name,
        definition=payload.definition,
    )
    return ok_response(request, workflow, status_code=201)


@router.post("/validate", response_model=APIResponseModel)
def validate_workflow_draft(
    request: Request,
    payload: WorkflowValidateRequest,
    registry: Annotated[NodeRegistry, Depends(get_node_registry)],
):
    result = validate_workflow_definition(payload.definition, registry)
    return ok_response(request, result.model_dump(mode="json"))


@router.get("/{workflow_id}", response_model=APIResponseModel)
def get_workflow(
    request: Request,
    workflow_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
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


@router.put("/{workflow_id}", response_model=APIResponseModel)
def update_workflow(
    request: Request,
    workflow_id: str,
    payload: WorkflowUpdateRequest,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    registry: Annotated[NodeRegistry, Depends(get_node_registry)],
):
    if payload.definition is not None:
        validation = validate_workflow_definition(payload.definition, registry)
        if not validation.valid:
            return error_response(
                request,
                error_code="WORKFLOW_VALIDATION_FAILED",
                message="Workflow definition is invalid",
                status_code=422,
                details=validation.model_dump(mode="json"),
            )
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


@router.post("/{workflow_id}/validate", response_model=APIResponseModel)
def validate_saved_workflow(
    request: Request,
    workflow_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    registry: Annotated[NodeRegistry, Depends(get_node_registry)],
):
    workflow = store.get_workflow_definition(workflow_id)
    if workflow is None:
        return error_response(
            request,
            error_code="WORKFLOW_NOT_FOUND",
            message="Workflow not found",
            status_code=404,
        )
    result = validate_workflow_definition(workflow.definition, registry)
    return ok_response(request, result.model_dump(mode="json"))


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


@router.delete("/{workflow_id}", response_model=APIResponseModel)
def delete_workflow(
    request: Request,
    workflow_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    if not store.delete_workflow_definition(workflow_id):
        return error_response(
            request,
            error_code="WORKFLOW_NOT_FOUND",
            message="Workflow not found",
            status_code=404,
        )
    return ok_response(request, {"workflow_id": workflow_id, "deleted": True})
