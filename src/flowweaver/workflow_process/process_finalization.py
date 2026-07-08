from __future__ import annotations

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import DatabaseEventSink, RuntimeEventSink
from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.enums import (
    EventType,
    NodeRunStatus,
    WorkflowRunCompletionReason,
    WorkflowRunStatus,
)
from flowweaver.protocols.events import EventModel
from flowweaver.workflow.definition import FailurePolicyMode
from flowweaver.workflow_process.dag import WorkflowDag
from flowweaver.workflow_process.ready_queue import collect_ready_node_candidates

_TERMINAL_WORKFLOW_STATUSES = frozenset(
    {
        WorkflowRunStatus.SUCCEEDED.value,
        WorkflowRunStatus.FAILED.value,
        WorkflowRunStatus.CANCELLED.value,
        WorkflowRunStatus.ABORTED.value,
    }
)
_CONTINUE_INDEPENDENT_IN_PROGRESS_NODE_STATUSES = frozenset(
    {
        NodeRunStatus.QUEUED.value,
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
        NodeRunStatus.CANCEL_REQUESTED.value,
    }
)


def workflow_run_is_terminal(
    store: RuntimeStore,
    workflow_run_id: str,
) -> bool:
    current = store.get_workflow_run(workflow_run_id)
    return current is not None and current.status in _TERMINAL_WORKFLOW_STATUSES


def finalize_if_workflow_run_terminal(
    store: RuntimeStore,
    workflow_run_id: str,
) -> bool:
    if not workflow_run_is_terminal(store, workflow_run_id):
        return False
    release_unreleased_read_leases_for_terminal_workflow(store, workflow_run_id)
    return True


def release_unreleased_read_leases_for_terminal_workflow(
    store: RuntimeStore,
    workflow_run_id: str,
) -> None:
    store.release_unreleased_read_leases_for_workflow_run(workflow_run_id)


def complete_continue_independent_partial_failure_if_finished(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int | None,
    failure_policy_mode: FailurePolicyMode,
    dag: WorkflowDag,
    event_sink: RuntimeEventSink,
) -> bool:
    if failure_policy_mode != FailurePolicyMode.CONTINUE_INDEPENDENT:
        return False
    run = store.get_workflow_run(workflow_run_id)
    if run is None or run.status != WorkflowRunStatus.RUNNING.value:
        return False
    node_runs = store.list_node_runs(workflow_run_id)
    if not any(node.status == NodeRunStatus.FAILED.value for node in node_runs):
        return False
    if any(
        node.status in _CONTINUE_INDEPENDENT_IN_PROGRESS_NODE_STATUSES
        for node in node_runs
    ):
        return False
    if collect_ready_node_candidates(
        store=store,
        workflow_run_id=workflow_run_id,
        dag=dag,
    ):
        return False
    completed = store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.FAILED,
        finished_at=utc_now(),
        completion_reason=WorkflowRunCompletionReason.PARTIAL_FAILURE,
        expected_state_version=run.state_version,
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
        owner_process_id=(
            workflow_process_id if process_generation is not None else None
        ),
        process_generation=process_generation,
    )
    if completed is None:
        return False
    failure_summary = continue_independent_failure_summary(node_runs)
    event_sink.emit(
        EventModel(
            event_type=EventType.WORKFLOW_FAILED,
            workflow_run_id=workflow_run_id,
            payload={
                "process_id": workflow_process_id,
                "completion_reason": (
                    WorkflowRunCompletionReason.PARTIAL_FAILURE.value
                ),
                **failure_summary,
            },
        )
    )
    return True


def continue_independent_failure_summary(
    node_runs: list[NodeRun],
) -> dict[str, list[str]]:
    failed_nodes = [
        node for node in node_runs if node.status == NodeRunStatus.FAILED.value
    ]
    skipped_nodes = [
        node for node in node_runs if node.status == NodeRunStatus.SKIPPED.value
    ]
    failed_nodes.sort(key=lambda node: node.node_instance_id)
    skipped_nodes.sort(key=lambda node: node.node_instance_id)
    return {
        "failed_node_instance_ids": [
            node.node_instance_id for node in failed_nodes
        ],
        "failed_node_run_ids": [node.node_run_id for node in failed_nodes],
        "skipped_node_instance_ids": [
            node.node_instance_id for node in skipped_nodes
        ],
        "skipped_node_run_ids": [node.node_run_id for node in skipped_nodes],
    }


def complete_empty_workflow(
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None = None,
    event_sink: RuntimeEventSink | None = None,
) -> int:
    event_sink = event_sink or DatabaseEventSink(store)
    current = store.get_workflow_run(workflow_run_id)
    store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.SUCCEEDED,
        finished_at=utc_now(),
        expected_state_version=current.state_version if current is not None else None,
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
        owner_process_id=process_id if process_generation is not None else None,
        process_generation=process_generation,
    )
    event_sink.emit(
        EventModel(
            event_type=EventType.WORKFLOW_FINISHED,
            workflow_run_id=workflow_run_id,
            payload={"process_id": process_id, "empty_workflow": True},
        )
    )
    release_unreleased_read_leases_for_terminal_workflow(store, workflow_run_id)
    return 0
