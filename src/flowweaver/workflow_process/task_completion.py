from __future__ import annotations

from collections.abc import Callable

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import (
    EventType,
    NodeResultStatus,
    NodeRunStatus,
    WorkflowRunStatus,
)
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow_process import process_finalization as finalization
from flowweaver.workflow_process import task_supervision as supervision
from flowweaver.workflow_process.executor_owner import close_executor
from flowweaver.workflow_process.executor_pool import ExecutorTaskCompletion
from flowweaver.workflow_process.node_task_results import (
    NodeTaskApplyResult,
    NodeTaskApplyStatus,
)
from flowweaver.workflow_process.node_tasks import NodeTaskManager

CleanupStagingForNode = Callable[[str, str], None]

_HANDLED_NODE_TASK_APPLY_STATUSES = frozenset(
    {
        NodeTaskApplyStatus.APPLIED,
        NodeTaskApplyStatus.ALREADY_APPLIED,
    }
)
_IGNORED_NODE_TASK_APPLY_STATUSES = frozenset(
    {
        NodeTaskApplyStatus.REJECTED_STALE_ATTEMPT,
        NodeTaskApplyStatus.REJECTED_STALE_GENERATION,
        NodeTaskApplyStatus.REJECTED_NODE_TERMINAL,
    }
)
_cleanup_staging_for_node = supervision.cleanup_staging_for_node_safely
_workflow_run_is_terminal = finalization.workflow_run_is_terminal


def apply_executor_task_completion(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int | None,
    event_sink: RuntimeEventSink,
    task_manager: NodeTaskManager,
    cleanup_staging_for_node: CleanupStagingForNode | None,
    close_executor_after_task: bool,
    completion: ExecutorTaskCompletion,
) -> None:
    dispatched = completion.dispatched_task
    try:
        result = completion.result
        if result is None:
            return
        apply_result = apply_node_task_result(
            store=store,
            workflow_run_id=workflow_run_id,
            workflow_process_id=workflow_process_id,
            process_generation=process_generation,
            event_sink=event_sink,
            task_manager=task_manager,
            task=dispatched.task,
            result=result,
        )
        if (
            result.status != NodeResultStatus.SUCCEEDED
            and apply_result.status not in _IGNORED_NODE_TASK_APPLY_STATUSES
        ):
            _cleanup_staging_for_node(
                cleanup_staging_for_node,
                workflow_run_id=workflow_run_id,
                node_run_id=dispatched.node_run_id,
            )
    finally:
        if close_executor_after_task:
            close_executor(dispatched.executor)


def apply_node_task_result(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int | None,
    event_sink: RuntimeEventSink,
    task_manager: NodeTaskManager,
    task: NodeTaskModel,
    result: NodeTaskResultModel,
) -> NodeTaskApplyResult:
    apply_result = task_manager.apply_result(result)
    if (
        apply_result.status not in _HANDLED_NODE_TASK_APPLY_STATUSES
        and apply_result.status not in _IGNORED_NODE_TASK_APPLY_STATUSES
    ):
        fail_rejected_node_result(
            store=store,
            workflow_run_id=workflow_run_id,
            workflow_process_id=workflow_process_id,
            process_generation=process_generation,
            event_sink=event_sink,
            task=task,
            result=result,
            apply_result=apply_result,
        )
    return apply_result


def fail_rejected_node_result(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int | None,
    event_sink: RuntimeEventSink,
    task: NodeTaskModel,
    result: NodeTaskResultModel,
    apply_result: NodeTaskApplyResult,
) -> None:
    if _workflow_run_is_terminal(store, workflow_run_id):
        return
    error = {
        "message": "Node task result was rejected",
        "apply_status": apply_result.status.value,
        "task_id": task.task_id,
        "result_id": result.result_id,
        "node_instance_id": task.node_instance_id,
    }
    node_run = store.get_node_run(task.node_run_id)
    failed_node = None
    if node_run is not None:
        failed_node = store.update_node_run_status(
            task.node_run_id,
            NodeRunStatus.FAILED,
            finished_at=utc_now(),
            error=error,
            expected_state_version=node_run.state_version,
            allowed_source_statuses=[
                NodeRunStatus.QUEUED,
                NodeRunStatus.RUNNING,
                NodeRunStatus.LONG_RUNNING,
            ],
            owner_process_id=(
                workflow_process_id if process_generation is not None else None
            ),
            process_generation=process_generation,
        )
    failed_run = store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.FAILED,
        finished_at=utc_now(),
        error=error,
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
        owner_process_id=(
            workflow_process_id if process_generation is not None else None
        ),
        process_generation=process_generation,
    )
    if failed_node is not None:
        event_sink.emit(
            EventModel(
                event_type=EventType.NODE_FAILED,
                workflow_run_id=workflow_run_id,
                node_run_id=task.node_run_id,
                payload={
                    "process_id": workflow_process_id,
                    "task_id": task.task_id,
                    "result_id": result.result_id,
                    "apply_status": apply_result.status.value,
                },
            )
        )
    if failed_run is not None:
        event_sink.emit(
            EventModel(
                event_type=EventType.WORKFLOW_FAILED,
                workflow_run_id=workflow_run_id,
                payload={
                    "process_id": workflow_process_id,
                    "task_id": task.task_id,
                    "result_id": result.result_id,
                    "apply_status": apply_result.status.value,
                },
            )
        )
