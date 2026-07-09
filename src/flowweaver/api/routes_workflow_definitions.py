from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from flowweaver.api.api_models import (
    APIResponseModel,
    WorkflowCreateRequest,
    WorkflowUpdateRequest,
    WorkflowValidateRequest,
)
from flowweaver.api.dependencies import get_node_registry, get_runtime_store
from flowweaver.api.responses import error_response, ok_response
from flowweaver.engine.runtime_models import WorkflowRevisionConflict
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.nodes.registry import NodeRegistry
from flowweaver.workflow.validation import validate_workflow_definition


def list_workflows(
    request: Request,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    return ok_response(request, store.list_workflow_definitions())


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


def validate_workflow_draft(
    request: Request,
    payload: WorkflowValidateRequest,
    registry: Annotated[NodeRegistry, Depends(get_node_registry)],
):
    result = validate_workflow_definition(payload.definition, registry)
    return ok_response(request, result.model_dump(mode="json"))


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


def update_workflow(
    request: Request,
    workflow_id: str,
    payload: WorkflowUpdateRequest,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    registry: Annotated[NodeRegistry, Depends(get_node_registry)],
):
    if payload.base_revision_id is None:
        return error_response(
            request,
            error_code="BASE_REVISION_REQUIRED",
            message="base_revision_id is required",
            status_code=400,
        )
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
        base_revision_id=payload.base_revision_id,
    )
    if isinstance(workflow, WorkflowRevisionConflict):
        return error_response(
            request,
            error_code="WORKFLOW_REVISION_CONFLICT",
            message="Workflow revision has changed",
            status_code=409,
            details={
                "workflow_id": workflow.workflow_id,
                "expected_revision_id": workflow.expected_revision_id,
                "current_revision_id": workflow.current_revision_id,
            },
        )
    if workflow is None:
        return error_response(
            request,
            error_code="WORKFLOW_NOT_FOUND",
            message="Workflow not found",
            status_code=404,
        )
    return ok_response(request, workflow)


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


def include_workflow_definition_routes(router: APIRouter) -> None:
    router.add_api_route(
        "",
        list_workflows,
        methods=["GET"],
        response_model=APIResponseModel,
    )
    router.add_api_route(
        "",
        create_workflow,
        methods=["POST"],
        status_code=201,
        response_model=APIResponseModel,
    )
    router.add_api_route(
        "/validate",
        validate_workflow_draft,
        methods=["POST"],
        response_model=APIResponseModel,
    )
    router.add_api_route(
        "/{workflow_id}",
        get_workflow,
        methods=["GET"],
        response_model=APIResponseModel,
    )
    router.add_api_route(
        "/{workflow_id}",
        update_workflow,
        methods=["PUT"],
        response_model=APIResponseModel,
    )
    router.add_api_route(
        "/{workflow_id}/validate",
        validate_saved_workflow,
        methods=["POST"],
        response_model=APIResponseModel,
    )
    router.add_api_route(
        "/{workflow_id}",
        delete_workflow,
        methods=["DELETE"],
        response_model=APIResponseModel,
    )
