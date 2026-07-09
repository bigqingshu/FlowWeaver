from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from queue import Empty, Queue
from threading import Thread

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.node_executor import NodeExecutor
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow_process.executor_owner import close_executor
from flowweaver.workflow_process.node_task_results import NodeTaskTimeoutStatus
from flowweaver.workflow_process.node_tasks import (
    NodeTaskManager,
)
from flowweaver.workflow_process.process_finalization import workflow_run_is_terminal
from flowweaver.workflow_process.task_cancellation_helpers import (
    cancel_grace_period_expired as cancel_grace_period_expired,
)
from flowweaver.workflow_process.task_cancellation_helpers import (
    cancelled_task_result as cancelled_task_result,
)
from flowweaver.workflow_process.task_cancellation_helpers import (
    mark_node_cancel_requested as mark_node_cancel_requested,
)
from flowweaver.workflow_process.task_cancellation_helpers import (
    request_cancel as request_cancel,
)
from flowweaver.workflow_process.task_cancellation_helpers import (
    request_cancel_for_in_flight_tasks as request_cancel_for_in_flight_tasks,
)
from flowweaver.workflow_process.task_cancellation_helpers import (
    workflow_cancel_was_requested as workflow_cancel_was_requested,
)

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
