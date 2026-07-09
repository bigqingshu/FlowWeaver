from __future__ import annotations

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.enums import (
    EventType,
    NodeResultStatus,
    NodeRunStatus,
    WorkflowRunStatus,
)
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow.definition import FailurePolicyMode
from flowweaver.workflow_process.dag import WorkflowDag
from flowweaver.workflow_process.failure_policy_propagation import (
    mark_blocked_descendants_skipped,
)
from flowweaver.workflow_process.loop_terminal_state import (
    close_loop_after_node_terminal_result,
)
from flowweaver.workflow_process.node_task_application_results import (
    result_already_applied_or_terminal,
)
from flowweaver.workflow_process.node_task_results import (
    NodeTaskApplyResult,
    NodeTaskApplyStatus,
)


def apply_terminal_failure(
    *,
    store: RuntimeStore,
    event_sink: RuntimeEventSink,
    dag: WorkflowDag,
    failure_policy_mode: FailurePolicyMode,
    task: NodeTaskModel,
    result: NodeTaskResultModel,
    node_run: NodeRun,
) -> NodeTaskApplyResult:
    node_status = (
        NodeRunStatus.CANCELLED
        if result.status == NodeResultStatus.CANCELLED
        else NodeRunStatus.FAILED
    )
    workflow_status = (
        WorkflowRunStatus.CANCELLED
        if result.status == NodeResultStatus.CANCELLED
        else WorkflowRunStatus.FAILED
    )
    updated = store.record_node_task_result_and_update_node_run_status(
        result,
        node_status,
        finished_at=result.finished_at,
        error=result.error,
        expected_state_version=node_run.state_version,
        allowed_source_statuses=[
            NodeRunStatus.RUNNING,
            NodeRunStatus.LONG_RUNNING,
            NodeRunStatus.CANCEL_REQUESTED,
        ],
        owner_process_id=task.workflow_process_id,
        process_generation=task.process_generation,
    )
    if updated is None:
        return result_already_applied_or_terminal(store, result)
    close_loop_after_node_terminal_result(
        store,
        node_run_id=updated.node_run_id,
        result_status=result.status,
        error=result.error,
        finished_at=result.finished_at,
    )
    if (
        result.status == NodeResultStatus.FAILED
        and failure_policy_mode == FailurePolicyMode.CONTINUE_INDEPENDENT
    ):
        mark_blocked_descendants_skipped(
            store=store,
            dag=dag,
            workflow_run_id=task.workflow_run_id,
            process_id=task.workflow_process_id,
            process_generation=task.process_generation,
            failed_node=updated,
            finished_at=result.finished_at,
        )
        event_sink.emit(
            EventModel(
                event_type=EventType.NODE_FAILED,
                workflow_run_id=task.workflow_run_id,
                node_run_id=result.node_run_id,
                payload={
                    "process_id": task.workflow_process_id,
                    "task_id": task.task_id,
                    "executor_id": result.executor_id,
                    "status": result.status.value,
                },
            )
        )
        return NodeTaskApplyResult(
            NodeTaskApplyStatus.APPLIED,
            node_run_id=result.node_run_id,
        )
    updated_workflow = store.update_workflow_run_status(
        task.workflow_run_id,
        workflow_status,
        finished_at=utc_now(),
        error=result.error,
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
        owner_process_id=task.workflow_process_id,
        process_generation=task.process_generation,
    )
    event_sink.emit(
        EventModel(
            event_type=(
                EventType.WORKFLOW_CANCELLED
                if workflow_status == WorkflowRunStatus.CANCELLED
                else EventType.NODE_FAILED
            ),
            workflow_run_id=task.workflow_run_id,
            node_run_id=result.node_run_id,
            payload={
                "process_id": task.workflow_process_id,
                "task_id": task.task_id,
                "executor_id": result.executor_id,
                "status": result.status.value,
            },
        )
    )
    if workflow_status == WorkflowRunStatus.FAILED and updated_workflow is not None:
        event_sink.emit(
            EventModel(
                event_type=EventType.WORKFLOW_FAILED,
                workflow_run_id=task.workflow_run_id,
                payload={
                    "process_id": task.workflow_process_id,
                    "task_id": task.task_id,
                },
            )
        )
    return NodeTaskApplyResult(
        NodeTaskApplyStatus.APPLIED,
        node_run_id=result.node_run_id,
    )
