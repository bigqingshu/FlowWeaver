from __future__ import annotations

from datetime import datetime, timedelta

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import EventType, NodeRunStatus, WorkflowRunStatus
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.workflow_process.node_task_results import (
    NodeTaskTimeoutResult,
    NodeTaskTimeoutStatus,
)


def mark_timed_out_task(
    *,
    store: RuntimeStore,
    event_sink: RuntimeEventSink,
    task: NodeTaskModel,
    now: datetime | None = None,
) -> NodeTaskTimeoutResult:
    stored_task = store.get_node_task(task.task_id)
    if stored_task is None or stored_task.node_run_id != task.node_run_id:
        return NodeTaskTimeoutResult(NodeTaskTimeoutStatus.REJECTED_INVALID_TASK)
    node_run = store.get_node_run(stored_task.node_run_id)
    if node_run is None or node_run.attempt != stored_task.attempt:
        return NodeTaskTimeoutResult(
            NodeTaskTimeoutStatus.REJECTED_INVALID_TASK,
            node_run_id=stored_task.node_run_id,
        )
    if node_run.status not in {
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
        NodeRunStatus.CANCEL_REQUESTED.value,
    }:
        return NodeTaskTimeoutResult(
            NodeTaskTimeoutStatus.REJECTED_NODE_NOT_RUNNING,
            node_run_id=stored_task.node_run_id,
        )
    workflow_run = store.get_workflow_run(stored_task.workflow_run_id)
    if workflow_run is None or workflow_run.status != WorkflowRunStatus.RUNNING.value:
        return NodeTaskTimeoutResult(
            NodeTaskTimeoutStatus.REJECTED_WORKFLOW_NOT_RUNNING,
            node_run_id=stored_task.node_run_id,
        )
    if node_run.started_at is None:
        return NodeTaskTimeoutResult(
            NodeTaskTimeoutStatus.NOT_TIMED_OUT,
            node_run_id=stored_task.node_run_id,
            detail="missing_started_at",
        )
    checked_at = now or utc_now()
    deadline = node_run.started_at + timedelta(seconds=stored_task.timeout_seconds)
    if checked_at < deadline:
        return NodeTaskTimeoutResult(
            NodeTaskTimeoutStatus.NOT_TIMED_OUT,
            node_run_id=stored_task.node_run_id,
        )
    error = {
        "message": "Node task timed out",
        "task_id": stored_task.task_id,
        "node_instance_id": stored_task.node_instance_id,
        "timeout_seconds": stored_task.timeout_seconds,
        "started_at": node_run.started_at.isoformat(),
        "timed_out_at": checked_at.isoformat(),
    }
    updated = store.update_node_run_status(
        stored_task.node_run_id,
        NodeRunStatus.TIMED_OUT,
        finished_at=checked_at,
        error=error,
        expected_state_version=node_run.state_version,
        allowed_source_statuses=[
            NodeRunStatus.RUNNING,
            NodeRunStatus.LONG_RUNNING,
        ],
        owner_process_id=stored_task.workflow_process_id,
        process_generation=stored_task.process_generation,
    )
    if updated is None:
        return NodeTaskTimeoutResult(
            NodeTaskTimeoutStatus.REJECTED_NODE_NOT_RUNNING,
            node_run_id=stored_task.node_run_id,
        )
    updated_workflow = store.update_workflow_run_status(
        stored_task.workflow_run_id,
        WorkflowRunStatus.FAILED,
        finished_at=checked_at,
        error=error,
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
        owner_process_id=stored_task.workflow_process_id,
        process_generation=stored_task.process_generation,
    )
    event_sink.emit(
        EventModel(
            event_type=EventType.NODE_TIMEOUT,
            workflow_run_id=stored_task.workflow_run_id,
            node_run_id=stored_task.node_run_id,
            payload={
                "process_id": stored_task.workflow_process_id,
                "task_id": stored_task.task_id,
                "executor_id": updated.executor_id,
                "node_instance_id": stored_task.node_instance_id,
                "timeout_seconds": stored_task.timeout_seconds,
            },
        )
    )
    if updated_workflow is not None:
        event_sink.emit(
            EventModel(
                event_type=EventType.WORKFLOW_FAILED,
                workflow_run_id=stored_task.workflow_run_id,
                payload={
                    "process_id": stored_task.workflow_process_id,
                    "task_id": stored_task.task_id,
                    "node_instance_id": stored_task.node_instance_id,
                    "reason": "NODE_TIMEOUT",
                },
            )
        )
    return NodeTaskTimeoutResult(
        NodeTaskTimeoutStatus.TIMED_OUT,
        node_run_id=stored_task.node_run_id,
    )
