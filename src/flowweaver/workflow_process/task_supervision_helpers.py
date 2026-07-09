from __future__ import annotations

from collections.abc import Callable
from queue import Empty, Queue

from flowweaver.protocols.node_task import NodeTaskResultModel

CleanupStagingForNode = Callable[[str, str], None]


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
