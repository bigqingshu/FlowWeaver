from __future__ import annotations

from flowweaver.node_executor import NodeExecutorFactory
from flowweaver.workflow_process.executor_owner import close_executor
from flowweaver.workflow_process.executor_pool import DispatchedNodeTask
from flowweaver.workflow_process.node_tasks import NodeTaskManager
from flowweaver.workflow_process.ready_queue import ReadyNodeCandidate
from flowweaver.workflow_process.task_dispatch_config import (
    timeout_seconds_from_node_config,
)
from flowweaver.workflow_process.task_input_resolution_failure import (
    fail_ready_node_input_resolution,
)


def dispatch_ready_node_candidate(
    *,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int,
    candidate: ReadyNodeCandidate,
    task_manager: NodeTaskManager,
    executor_factory: NodeExecutorFactory,
    close_executor_on_reject: bool = True,
) -> DispatchedNodeTask | None:
    if candidate.input_resolution_issue is not None:
        fail_ready_node_input_resolution(
            workflow_run_id=workflow_run_id,
            workflow_process_id=workflow_process_id,
            process_generation=process_generation,
            candidate=candidate,
            task_manager=task_manager,
        )
        return None
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
    executor = executor_factory(task)
    accepted = task_manager.accept_task(
        task_id=task.task_id,
        executor_id=executor.executor_id,
    )
    if accepted is None:
        if close_executor_on_reject:
            close_executor(executor)
        return None
    return DispatchedNodeTask(
        task=accepted,
        executor=executor,
        node_run_id=accepted.node_run_id,
        node_instance_id=accepted.node_instance_id,
        executor_id=executor.executor_id,
    )
