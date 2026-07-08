from __future__ import annotations

from collections.abc import Mapping

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.protocols.enums import (
    EventType,
    NodeResultStatus,
    NodeRunStatus,
    WorkflowRunStatus,
)
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow.definition import (
    FailurePolicyMode,
    RuntimeOptionsWorkflowModel,
)
from flowweaver.workflow.runtime_options import (
    sanitize_node_task_result_for_runtime_options,
)
from flowweaver.workflow_process.control_signal_interpreter import (
    interpret_control_outputs_after_node_success,
)
from flowweaver.workflow_process.controller import advance_after_node_success
from flowweaver.workflow_process.dag import WorkflowDag
from flowweaver.workflow_process.failure_policy_propagation import (
    mark_blocked_descendants_skipped,
)
from flowweaver.workflow_process.loop_iteration_nodes import (
    ensure_loop_iteration_entry_node_run,
)
from flowweaver.workflow_process.loop_iteration_scheduling import (
    advance_loop_iteration_after_node_success,
)
from flowweaver.workflow_process.loop_terminal_state import (
    close_loop_after_node_terminal_result,
)
from flowweaver.workflow_process.node_task_results import (
    NodeTaskApplyResult,
    NodeTaskApplyStatus,
)


def apply_node_task_result_to_runtime(
    *,
    store: RuntimeStore,
    event_sink: RuntimeEventSink,
    dag: WorkflowDag,
    failure_policy_mode: FailurePolicyMode,
    runtime_options_by_node: Mapping[str, RuntimeOptionsWorkflowModel],
    table_provider_registry: TableProviderRegistry | None,
    result: NodeTaskResultModel,
) -> NodeTaskApplyResult:
    existing_result = store.get_node_task_result(
        task_id=result.task_id,
        result_id=result.result_id,
    )
    if existing_result is not None:
        return NodeTaskApplyResult(
            NodeTaskApplyStatus.ALREADY_APPLIED,
            node_run_id=existing_result.node_run_id,
        )
    task = store.get_node_task(result.task_id)
    if task is None or task.node_run_id != result.node_run_id:
        return NodeTaskApplyResult(NodeTaskApplyStatus.REJECTED_INVALID_TASK)
    node_run = store.get_node_run(result.node_run_id)
    if node_run is None:
        return NodeTaskApplyResult(NodeTaskApplyStatus.REJECTED_INVALID_TASK)
    if result.process_generation != task.process_generation:
        return NodeTaskApplyResult(
            NodeTaskApplyStatus.REJECTED_STALE_GENERATION,
            node_run_id=result.node_run_id,
        )
    if result.attempt != task.attempt or result.attempt != node_run.attempt:
        return NodeTaskApplyResult(
            NodeTaskApplyStatus.REJECTED_STALE_ATTEMPT,
            node_run_id=result.node_run_id,
        )
    if node_run.executor_id != result.executor_id:
        return NodeTaskApplyResult(
            NodeTaskApplyStatus.REJECTED_EXECUTOR_MISMATCH,
            node_run_id=result.node_run_id,
        )
    if node_run.status not in {
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
        NodeRunStatus.CANCEL_REQUESTED.value,
    }:
        return NodeTaskApplyResult(
            NodeTaskApplyStatus.REJECTED_NODE_TERMINAL,
            node_run_id=result.node_run_id,
        )
    result = sanitize_node_task_result_for_runtime_options(
        result,
        runtime_options_by_node.get(task.node_instance_id),
    )
    if result.status == NodeResultStatus.SUCCEEDED:
        return _apply_success(
            store=store,
            event_sink=event_sink,
            dag=dag,
            table_provider_registry=table_provider_registry,
            task=task,
            result=result,
            node_run=node_run,
        )
    return _apply_terminal_failure(
        store=store,
        event_sink=event_sink,
        dag=dag,
        failure_policy_mode=failure_policy_mode,
        task=task,
        result=result,
        node_run=node_run,
    )


def _apply_success(
    *,
    store: RuntimeStore,
    event_sink: RuntimeEventSink,
    dag: WorkflowDag,
    table_provider_registry: TableProviderRegistry | None,
    task: NodeTaskModel,
    result: NodeTaskResultModel,
    node_run: NodeRun,
) -> NodeTaskApplyResult:
    updated = store.record_node_task_result_and_update_node_run_status(
        result,
        NodeRunStatus.SUCCEEDED,
        finished_at=result.finished_at,
        expected_state_version=node_run.state_version,
        allowed_source_statuses=[
            NodeRunStatus.RUNNING,
            NodeRunStatus.LONG_RUNNING,
        ],
        owner_process_id=task.workflow_process_id,
        process_generation=task.process_generation,
    )
    if updated is None:
        return _result_already_applied_or_terminal(store, result)
    if table_provider_registry is not None:
        control_result = interpret_control_outputs_after_node_success(
            store,
            table_provider_registry,
            workflow_run_id=task.workflow_run_id,
            completed_node=updated,
            output_refs=result.output_refs,
        )
        if (
            control_result.advance_result is not None
            and control_result.advance_result.next_iteration is not None
        ):
            ensure_loop_iteration_entry_node_run(
                store,
                dag=dag,
                loop_iteration_id=(
                    control_result.advance_result.next_iteration.loop_iteration_id
                ),
                owner_process_id=task.workflow_process_id,
                process_generation=task.process_generation,
            )
    advance_loop_iteration_after_node_success(
        store,
        dag=dag,
        completed_node=updated,
        owner_process_id=task.workflow_process_id,
        process_generation=task.process_generation,
    )
    advance_after_node_success(
        store,
        workflow_run_id=task.workflow_run_id,
        process_id=task.workflow_process_id,
        process_generation=task.process_generation,
        dag=dag,
        completed_node=updated,
        event_sink=event_sink,
    )
    return NodeTaskApplyResult(
        NodeTaskApplyStatus.APPLIED,
        node_run_id=result.node_run_id,
    )


def _apply_terminal_failure(
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
        return _result_already_applied_or_terminal(store, result)
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


def _result_already_applied_or_terminal(
    store: RuntimeStore,
    result: NodeTaskResultModel,
) -> NodeTaskApplyResult:
    existing_result = store.get_node_task_result(
        task_id=result.task_id,
        result_id=result.result_id,
    )
    if existing_result is not None:
        return NodeTaskApplyResult(
            NodeTaskApplyStatus.ALREADY_APPLIED,
            node_run_id=existing_result.node_run_id,
        )
    return NodeTaskApplyResult(
        NodeTaskApplyStatus.REJECTED_NODE_TERMINAL,
        node_run_id=result.node_run_id,
    )
