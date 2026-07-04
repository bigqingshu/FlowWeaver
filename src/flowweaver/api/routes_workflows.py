from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request

from flowweaver.api.api_models import (
    APIResponseModel,
    WorkflowCreateRequest,
    WorkflowRunStartRequest,
    WorkflowUpdateRequest,
    WorkflowValidateRequest,
)
from flowweaver.api.dependencies import (
    check_origin,
    get_node_registry,
    get_runtime_store,
    get_supervisor,
    require_api_token,
)
from flowweaver.api.responses import error_response, ok_response
from flowweaver.engine.runtime_store import RuntimeStore, WorkflowRevisionConflict
from flowweaver.engine.supervisor import Supervisor
from flowweaver.nodes.registry import NodeRegistry
from flowweaver.protocols.enums import WorkflowRunStatus
from flowweaver.workflow.definition import WorkflowDefinitionModel
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


@router.post("/{workflow_id}/runs", status_code=201, response_model=APIResponseModel)
def start_workflow_run(
    request: Request,
    workflow_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    supervisor: Annotated[Supervisor, Depends(get_supervisor)],
    payload: Annotated[WorkflowRunStartRequest | None, Body()] = None,
):
    workflow = store.get_workflow_definition(workflow_id)
    if workflow is None:
        return error_response(
            request,
            error_code="WORKFLOW_NOT_FOUND",
            message="Workflow not found",
            status_code=404,
        )
    run_mode = payload.run_mode if payload is not None else "full"
    target_node_instance_id = (
        payload.target_node_instance_id if payload is not None else None
    )
    if run_mode not in {"full", "preview_to_node"}:
        return error_response(
            request,
            error_code="WORKFLOW_RUN_MODE_UNSUPPORTED",
            message="Workflow run mode is not supported",
            status_code=422,
            details={"run_mode": run_mode},
        )
    if run_mode == "full" and target_node_instance_id is not None:
        return error_response(
            request,
            error_code="WORKFLOW_RUN_TARGET_UNSUPPORTED",
            message="Full workflow run does not accept target_node_instance_id",
            status_code=422,
        )
    if run_mode == "preview_to_node":
        if not target_node_instance_id:
            return error_response(
                request,
                error_code="TARGET_NODE_REQUIRED",
                message="target_node_instance_id is required for preview_to_node",
                status_code=422,
            )
        definition = WorkflowDefinitionModel.model_validate(workflow.definition)
        if not any(
            node.enabled and node.node_instance_id == target_node_instance_id
            for node in definition.nodes
        ):
            return error_response(
                request,
                error_code="TARGET_NODE_NOT_FOUND",
                message="Target node was not found in workflow definition",
                status_code=404,
                details={"target_node_instance_id": target_node_instance_id},
            )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        revision_id=workflow.revision_id,
        status=WorkflowRunStatus.PENDING,
        run_mode=run_mode,
        target_node_instance_id=target_node_instance_id,
    )
    try:
        supervisor.start_workflow_process(run.workflow_run_id)
    except Exception as exc:
        current = store.get_workflow_run(run.workflow_run_id)
        failed = store.update_workflow_run_status(
            run.workflow_run_id,
            WorkflowRunStatus.FAILED,
            error={"message": str(exc)},
            expected_state_version=current.state_version if current else None,
            allowed_source_statuses=[
                WorkflowRunStatus.PENDING,
                WorkflowRunStatus.RUNNING,
            ],
        )
        return ok_response(request, failed or current or run, status_code=201)
    return ok_response(request, run, status_code=201)


@router.put("/{workflow_id}", response_model=APIResponseModel)
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
