from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from flowweaver.api.responses import error_response, ok_response
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.supervisor import Supervisor
from flowweaver.protocols.enums import WorkflowRunStatus
from flowweaver.workflow.definition import WorkflowDefinitionModel

SUPPORTED_WORKFLOW_RUN_MODES = {"full", "preview_to_node"}
SUPPORTED_WORKFLOW_RUN_TRIGGER_SOURCES = {"manual", "background_manual"}


def start_workflow_run_for_request(
    request: Request,
    *,
    workflow_id: str,
    store: RuntimeStore,
    supervisor: Supervisor,
    run_mode: str = "full",
    trigger_source: str = "manual",
    target_node_instance_id: str | None = None,
    revision_id: str | None = None,
    status_code: int = 201,
) -> JSONResponse:
    workflow = store.get_workflow_definition(workflow_id)
    if workflow is None:
        return error_response(
            request,
            error_code="WORKFLOW_NOT_FOUND",
            message="Workflow not found",
            status_code=404,
        )
    resolved_revision_id = revision_id or workflow.revision_id
    revision = store.get_workflow_revision(resolved_revision_id)
    if revision is None or revision.workflow_id != workflow_id:
        return error_response(
            request,
            error_code="WORKFLOW_REVISION_NOT_FOUND",
            message="Workflow revision not found",
            status_code=404,
            details={
                "workflow_id": workflow_id,
                "revision_id": resolved_revision_id,
            },
        )
    rejection = _validate_workflow_run_request(
        request,
        definition=revision.definition,
        run_mode=run_mode,
        trigger_source=trigger_source,
        target_node_instance_id=target_node_instance_id,
    )
    if rejection is not None:
        return rejection
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        revision_id=revision.revision_id,
        status=WorkflowRunStatus.PENDING,
        run_mode=run_mode,
        trigger_source=trigger_source,
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
        return ok_response(request, failed or current or run, status_code=status_code)
    return ok_response(request, run, status_code=status_code)


def _validate_workflow_run_request(
    request: Request,
    *,
    definition: dict,
    run_mode: str,
    trigger_source: str,
    target_node_instance_id: str | None,
) -> JSONResponse | None:
    if run_mode not in SUPPORTED_WORKFLOW_RUN_MODES:
        return error_response(
            request,
            error_code="WORKFLOW_RUN_MODE_UNSUPPORTED",
            message="Workflow run mode is not supported",
            status_code=422,
            details={"run_mode": run_mode},
        )
    if trigger_source not in SUPPORTED_WORKFLOW_RUN_TRIGGER_SOURCES:
        return error_response(
            request,
            error_code="WORKFLOW_RUN_TRIGGER_SOURCE_UNSUPPORTED",
            message="Workflow run trigger_source is not supported",
            status_code=422,
            details={"trigger_source": trigger_source},
        )
    if run_mode == "full" and target_node_instance_id is not None:
        return error_response(
            request,
            error_code="WORKFLOW_RUN_TARGET_UNSUPPORTED",
            message="Full workflow run does not accept target_node_instance_id",
            status_code=422,
        )
    if run_mode != "preview_to_node":
        return None
    if not target_node_instance_id:
        return error_response(
            request,
            error_code="TARGET_NODE_REQUIRED",
            message="target_node_instance_id is required for preview_to_node",
            status_code=422,
        )
    workflow_definition = WorkflowDefinitionModel.model_validate(definition)
    if any(
        node.enabled and node.node_instance_id == target_node_instance_id
        for node in workflow_definition.nodes
    ):
        return None
    return error_response(
        request,
        error_code="TARGET_NODE_NOT_FOUND",
        message="Target node was not found in workflow definition",
        status_code=404,
        details={"target_node_instance_id": target_node_instance_id},
    )
