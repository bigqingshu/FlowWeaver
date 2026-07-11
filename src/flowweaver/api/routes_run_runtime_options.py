from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from flowweaver.api.api_models import (
    ActiveNodeTaskRuntimeOptionsVersionView,
    APIResponseModel,
    WorkflowRunRuntimeOptionsEffectiveSummaryView,
    WorkflowRunRuntimeOptionsUpdateRequest,
    WorkflowRunRuntimeOptionsView,
)
from flowweaver.api.dependencies import get_runtime_store
from flowweaver.api.responses import error_response, ok_response
from flowweaver.engine.runtime_models import WorkflowRunRuntimeOptions
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_workflow_run_options_store import (
    WorkflowRunRuntimeOptionsInactiveError,
    WorkflowRunRuntimeOptionsInvalidNodesError,
    WorkflowRunRuntimeOptionsNotFoundError,
    WorkflowRunRuntimeOptionsVersionConflictError,
)
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow.runtime_options import (
    build_runtime_feedback_policy_provider,
)

router = APIRouter()


@router.get(
    "/{workflow_run_id}/runtime-options",
    response_model=APIResponseModel,
)
def get_run_runtime_options(
    request: Request,
    workflow_run_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    state = store.get_workflow_run_runtime_options(workflow_run_id)
    if state is None:
        return _run_not_found(request)
    view = _runtime_options_view(store, state)
    if view is None:
        return _run_not_found(request)
    return ok_response(request, view.model_dump(mode="json"))


@router.put(
    "/{workflow_run_id}/runtime-options",
    response_model=APIResponseModel,
)
def replace_run_runtime_options(
    request: Request,
    workflow_run_id: str,
    payload: WorkflowRunRuntimeOptionsUpdateRequest,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
):
    try:
        state = store.replace_workflow_run_runtime_options(
            workflow_run_id,
            expected_version=payload.expected_version,
            overlay=payload.overlay,
        )
    except WorkflowRunRuntimeOptionsNotFoundError:
        return _run_not_found(request)
    except WorkflowRunRuntimeOptionsVersionConflictError as exc:
        return error_response(
            request,
            error_code="RUNTIME_OPTIONS_VERSION_CONFLICT",
            message="Workflow run runtime options version conflict",
            status_code=409,
            details={"current_version": exc.current_version},
        )
    except WorkflowRunRuntimeOptionsInactiveError as exc:
        return error_response(
            request,
            error_code="RUNTIME_OPTIONS_RUN_NOT_ACTIVE",
            message="Workflow run runtime options are read-only",
            status_code=409,
            details={"status": exc.status},
        )
    except WorkflowRunRuntimeOptionsInvalidNodesError as exc:
        return error_response(
            request,
            error_code="RUNTIME_OPTIONS_INVALID_NODE",
            message="Runtime options contain unknown node instance IDs",
            status_code=422,
            details={"node_instance_ids": list(exc.node_instance_ids)},
        )
    view = _runtime_options_view(store, state)
    if view is None:
        return _run_not_found(request)
    return ok_response(request, view.model_dump(mode="json"))


def _runtime_options_view(
    store: RuntimeStore,
    state: WorkflowRunRuntimeOptions,
) -> WorkflowRunRuntimeOptionsView | None:
    run = store.get_workflow_run(state.workflow_run_id)
    if run is None or run.revision_id is None:
        return None
    revision = store.get_workflow_revision(run.revision_id)
    if revision is None:
        return None
    definition = WorkflowDefinitionModel.model_validate(revision.definition)
    provider = build_runtime_feedback_policy_provider(
        definition,
        overlay=state.overlay,
        version=state.requested_version,
    )
    active_task_versions = store.list_active_node_task_runtime_options_versions(
        state.workflow_run_id
    )
    return WorkflowRunRuntimeOptionsView(
        workflow_run_id=state.workflow_run_id,
        saved_runtime_options=dict(
            revision.definition.get("runtime_options") or {}
        ),
        overlay=state.overlay.model_dump(
            mode="json",
            exclude_none=True,
            exclude_defaults=True,
        ),
        effective_summary=WorkflowRunRuntimeOptionsEffectiveSummaryView(
            workflow=provider.workflow_policy(),
            nodes={
                node.node_instance_id: provider.policy_for_node(
                    node.node_instance_id
                )
                for node in definition.nodes
            },
        ),
        requested_version=state.requested_version,
        applied_version=state.applied_version,
        requested_at=state.requested_at,
        applied_at=state.applied_at,
        active_task_versions=[
            ActiveNodeTaskRuntimeOptionsVersionView(
                task_id=item.task_id,
                node_run_id=item.node_run_id,
                node_instance_id=item.node_instance_id,
                node_run_status=item.node_run_status,
                runtime_options_version=item.runtime_options_version,
            )
            for item in active_task_versions
        ],
    )


def _run_not_found(request: Request):
    return error_response(
        request,
        error_code="WORKFLOW_RUN_NOT_FOUND",
        message="Workflow run not found",
        status_code=404,
    )
