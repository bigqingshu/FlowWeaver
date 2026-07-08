from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from queue import Empty, Queue
from threading import Thread

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.node_executor import CancellableNodeExecutor, NodeExecutor
from flowweaver.protocols.enums import NodeResultStatus, NodeRunStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow_process.executor_owner import close_executor
from flowweaver.workflow_process.executor_pool import NodeTaskExecutionPool
from flowweaver.workflow_process.node_task_results import NodeTaskTimeoutStatus
from flowweaver.workflow_process.node_tasks import (
    NodeTaskManager,
)
from flowweaver.workflow_process.process_finalization import workflow_run_is_terminal

CleanupStagingForNode = Callable[[str, str], None]


def execute_node_task_with_supervision(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int,
    heartbeat_interval_seconds: float,
    task_manager: NodeTaskManager,
    executor: NodeExecutor,
    cleanup_staging_for_node: CleanupStagingForNode | None,
    cancel_grace_seconds: float,
    task: NodeTaskModel,
) -> NodeTaskResultModel | None:
    results: Queue[NodeTaskResultModel | Exception] = Queue(maxsize=1)
    cancel_requested_at: datetime | None = None

    def run_executor() -> None:
        try:
            results.put(executor.execute(task))
        except Exception as exc:
            results.put(exc)

    worker = Thread(
        target=run_executor,
        name=f"flowweaver-node-task-{task.task_id}",
        daemon=True,
    )
    worker.start()
    poll_seconds = task_supervision_poll_seconds(heartbeat_interval_seconds)
    while True:
        result = get_node_task_execution_result(
            results,
            timeout_seconds=poll_seconds,
        )
        if result is not None:
            if (
                workflow_cancel_was_requested(
                    store=store,
                    workflow_process_id=workflow_process_id,
                )
                or cancel_requested_at is not None
            ):
                if cancel_requested_at is None:
                    cancel_requested_at = utc_now()
                    mark_node_cancel_requested(
                        store=store,
                        task=task,
                        executor_id=executor.executor_id,
                    )
                    request_cancel(executor, task)
                if result.status == NodeResultStatus.CANCELLED:
                    return result
                return cancelled_task_result(
                    task,
                    executor_id=executor.executor_id,
                )
            return result
        if not worker.is_alive():
            result = get_node_task_execution_result(results, timeout_seconds=0)
            if result is not None:
                return result
            raise RuntimeError("Node executor finished without a task result")
        heartbeat = store.record_workflow_process_heartbeat(
            workflow_process_id,
            process_generation=process_generation,
        )
        if heartbeat is None:
            close_executor(executor)
            return None
        timeout_result = task_manager.mark_timed_out_task(task)
        if timeout_result.status == NodeTaskTimeoutStatus.TIMED_OUT:
            close_executor(executor)
            cleanup_staging_for_node_safely(
                cleanup_staging_for_node,
                workflow_run_id=workflow_run_id,
                node_run_id=task.node_run_id,
            )
            worker.join(timeout=0.2)
            late_result = get_node_task_execution_result(
                results,
                timeout_seconds=0,
                raise_executor_errors=False,
            )
            if late_result is not None:
                task_manager.apply_result(late_result)
            return None
        if workflow_run_is_terminal(store, workflow_run_id):
            close_executor(executor)
            return None
        if workflow_cancel_was_requested(
            store=store,
            workflow_process_id=workflow_process_id,
        ):
            if cancel_requested_at is None:
                cancel_requested_at = utc_now()
                mark_node_cancel_requested(
                    store=store,
                    task=task,
                    executor_id=executor.executor_id,
                )
                request_cancel(executor, task)
            if cancel_grace_period_expired(
                cancel_requested_at,
                cancel_grace_seconds=cancel_grace_seconds,
            ):
                close_executor(executor)
                worker.join(timeout=0.2)
                return cancelled_task_result(
                    task,
                    executor_id=executor.executor_id,
                    reason="WORKFLOW_CANCEL_GRACE_EXPIRED",
                )


def get_node_task_execution_result(
    results: Queue[NodeTaskResultModel | Exception],
    *,
    timeout_seconds: float,
    raise_executor_errors: bool = True,
) -> NodeTaskResultModel | None:
    try:
        item = (
            results.get(timeout=timeout_seconds)
            if timeout_seconds > 0
            else results.get_nowait()
        )
    except Empty:
        return None
    if isinstance(item, Exception):
        if raise_executor_errors:
            raise item
        return None
    return item


def task_supervision_poll_seconds(heartbeat_interval_seconds: float) -> float:
    if heartbeat_interval_seconds <= 0:
        return 0.01
    return min(max(heartbeat_interval_seconds, 0.01), 0.1)


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
) -> None:
    node_run = store.get_node_run(task.node_run_id)
    if node_run is None:
        return
    if node_run.status == NodeRunStatus.CANCEL_REQUESTED.value:
        return
    store.update_node_run_status(
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
    )


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
        mark_node_cancel_requested(
            store=store,
            task=dispatched.task,
            executor_id=dispatched.executor_id,
        )
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


def cleanup_staging_for_node_safely(
    cleanup_staging_for_node: CleanupStagingForNode | None,
    *,
    workflow_run_id: str,
    node_run_id: str,
) -> None:
    if cleanup_staging_for_node is None:
        return
    try:
        cleanup_staging_for_node(workflow_run_id, node_run_id)
    except Exception:
        pass
