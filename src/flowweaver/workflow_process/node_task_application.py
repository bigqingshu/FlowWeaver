from __future__ import annotations

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.protocols.enums import (
    NodeResultStatus,
    NodeRunStatus,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow.definition import FailurePolicyMode
from flowweaver.workflow.runtime_feedback_policy import (
    RuntimeFeedbackPolicyProvider,
)
from flowweaver.workflow.runtime_options import (
    sanitize_node_task_result_for_runtime_options,
)
from flowweaver.workflow_process.control_signal_interpreter import (
    interpret_control_outputs_after_node_success,
)
from flowweaver.workflow_process.controller import advance_after_node_success
from flowweaver.workflow_process.dag import WorkflowDag
from flowweaver.workflow_process.loop_iteration_nodes import (
    ensure_loop_iteration_entry_node_run,
)
from flowweaver.workflow_process.loop_iteration_scheduling import (
    advance_loop_iteration_after_node_success,
)
from flowweaver.workflow_process.node_task_application_results import (
    result_already_applied_or_terminal as _result_already_applied_or_terminal,
)
from flowweaver.workflow_process.node_task_failure_application import (
    apply_terminal_failure as _apply_terminal_failure,
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
    runtime_feedback_policy_provider: RuntimeFeedbackPolicyProvider | None,
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
        (
            runtime_feedback_policy_provider.policy_for_node(task.node_instance_id)
            if runtime_feedback_policy_provider is not None
            else None
        ),
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

