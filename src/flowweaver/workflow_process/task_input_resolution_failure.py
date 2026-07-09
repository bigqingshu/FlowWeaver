from __future__ import annotations

from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskResultModel
from flowweaver.workflow_process.node_tasks import NodeTaskManager
from flowweaver.workflow_process.ready_queue import ReadyNodeCandidate
from flowweaver.workflow_process.task_dispatch_config import (
    timeout_seconds_from_node_config,
)


def fail_ready_node_input_resolution(
    *,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int,
    candidate: ReadyNodeCandidate,
    task_manager: NodeTaskManager,
) -> None:
    task = task_manager.submit_ready_node(
        workflow_run_id=workflow_run_id,
        workflow_process_id=workflow_process_id,
        process_generation=process_generation,
        node_instance_id=candidate.node_run.node_instance_id,
        node_run_id=candidate.node_run.node_run_id,
        input_refs=list(candidate.input_refs),
        input_slot_bindings=candidate.input_slot_bindings,
        timeout_seconds=timeout_seconds_from_node_config(candidate.dag_node.config),
    )
    if task is None:
        return None
    executor_id = "workflow_process.input_resolver"
    accepted = task_manager.accept_task(
        task_id=task.task_id,
        executor_id=executor_id,
    )
    if accepted is None:
        return None
    issue = candidate.input_resolution_issue
    message = (
        issue.message
        if issue is not None
        else "Input table selector could not be resolved"
    )
    details = issue.details if issue is not None else {}
    task_manager.apply_result(
        NodeTaskResultModel(
            task_id=accepted.task_id,
            node_run_id=accepted.node_run_id,
            attempt=accepted.attempt,
            executor_id=executor_id,
            process_generation=accepted.process_generation,
            status=NodeResultStatus.FAILED,
            error={
                "code": "INPUT_TABLE_RESOLUTION_FAILED",
                "message": message,
                "details": details,
            },
        )
    )
    return None
