from __future__ import annotations

from datetime import datetime

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.node_executor import CancellableNodeExecutor, NodeExecutor
from flowweaver.protocols.enums import NodeResultStatus, NodeRunStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow_process.executor_pool import NodeTaskExecutionPool


def workflow_cancel_was_requested(
    *,
    store: RuntimeStore,
    workflow_process_id: str,
) -> bool:
    process = store.get_workflow_process(workflow_process_id)
    return process is not None and process.cancel_requested_at is not None


def mark_node_cancel_requested(
    *,
    store: RuntimeStore,
    task: NodeTaskModel,
    executor_id: str,
) -> bool:
    node_run = store.get_node_run(task.node_run_id)
    if node_run is None:
        return False
    if node_run.status == NodeRunStatus.CANCEL_REQUESTED.value:
        return False
    return store.update_node_run_status(
        task.node_run_id,
        NodeRunStatus.CANCEL_REQUESTED,
        executor_id=executor_id,
        expected_state_version=node_run.state_version,
        allowed_source_statuses=[
            NodeRunStatus.RUNNING,
            NodeRunStatus.LONG_RUNNING,
        ],
        owner_process_id=task.workflow_process_id,
        process_generation=task.process_generation,
    ) is not None


def cancel_grace_period_expired(
    cancel_requested_at: datetime,
    *,
    cancel_grace_seconds: float,
) -> bool:
    return (
        utc_now() - cancel_requested_at
    ).total_seconds() >= cancel_grace_seconds


def request_cancel(
    executor: NodeExecutor,
    task: NodeTaskModel,
) -> None:
    if not isinstance(executor, CancellableNodeExecutor):
        return
    try:
        executor.request_cancel(task)
    except Exception:
        pass


def request_cancel_for_in_flight_tasks(
    *,
    store: RuntimeStore,
    execution_pool: NodeTaskExecutionPool,
) -> None:
    for dispatched in execution_pool.in_flight_tasks():
        marked = mark_node_cancel_requested(
            store=store,
            task=dispatched.task,
            executor_id=dispatched.executor_id,
        )
        if marked:
            request_cancel(dispatched.executor, dispatched.task)


def cancelled_task_result(
    task: NodeTaskModel,
    *,
    executor_id: str,
    reason: str = "WORKFLOW_CANCEL_REQUESTED",
) -> NodeTaskResultModel:
    now = utc_now()
    return NodeTaskResultModel(
        task_id=task.task_id,
        node_run_id=task.node_run_id,
        attempt=task.attempt,
        executor_id=executor_id,
        process_generation=task.process_generation,
        status=NodeResultStatus.CANCELLED,
        error={
            "message": "Node task cancelled",
            "reason": reason,
        },
        started_at=now,
        finished_at=now,
    )
