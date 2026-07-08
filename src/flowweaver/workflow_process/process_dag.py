from __future__ import annotations

from flowweaver.engine.runtime_models import WorkflowRun
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.dag import (
    WorkflowDag,
    build_workflow_dag,
    restrict_workflow_dag_to_upstream_closure,
)


class WorkflowProcessDagError(Exception):
    pass


def prepare_workflow_process_dag(
    *,
    definition: WorkflowDefinitionModel,
    run: WorkflowRun,
) -> WorkflowDag:
    dag = build_workflow_dag(definition)
    if run.run_mode != "preview_to_node":
        return dag
    if not run.target_node_instance_id:
        raise WorkflowProcessDagError(
            "target_node_instance_id is required for preview_to_node"
        )
    try:
        return restrict_workflow_dag_to_upstream_closure(
            dag,
            run.target_node_instance_id,
        )
    except ValueError as exc:
        raise WorkflowProcessDagError(str(exc)) from exc
