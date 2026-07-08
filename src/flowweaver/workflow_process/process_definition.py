from __future__ import annotations

from dataclasses import dataclass

from flowweaver.engine.runtime_models import WorkflowRun
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.workflow.definition import (
    UNAVAILABLE_FAILURE_POLICY_MODES,
    WorkflowDefinitionModel,
    failure_policy_unavailable_message,
)


@dataclass(frozen=True)
class LoadedWorkflowProcessDefinition:
    run: WorkflowRun
    definition: WorkflowDefinitionModel


class WorkflowProcessDefinitionError(Exception):
    pass


def load_workflow_process_definition(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
) -> LoadedWorkflowProcessDefinition:
    run = store.get_workflow_run(workflow_run_id)
    if run is None or run.revision_id is None:
        raise WorkflowProcessDefinitionError("Workflow run not found")
    revision = store.get_workflow_revision(run.revision_id)
    if revision is None:
        raise WorkflowProcessDefinitionError("Workflow revision not found")

    definition = WorkflowDefinitionModel.model_validate(revision.definition)
    if definition.failure_policy.mode in UNAVAILABLE_FAILURE_POLICY_MODES:
        raise WorkflowProcessDefinitionError(
            failure_policy_unavailable_message(definition.failure_policy.mode)
        )
    return LoadedWorkflowProcessDefinition(run=run, definition=definition)
