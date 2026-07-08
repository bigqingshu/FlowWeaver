from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.node_executor import NodeExecutor
from flowweaver.protocols.node_task import NodeTaskResultModel
from flowweaver.workflow_process import task_supervision as supervision
from flowweaver.workflow_process.executor_owner import (
    DefaultWorkflowProcessExecutorOwner,
)
from flowweaver.workflow_process.executor_pool import DispatchedNodeTask
from flowweaver.workflow_process.node_tasks import NodeTaskManager

CleanupStagingForNode = Callable[[str, str], None]


def create_default_workflow_process_executor_owner(
    *,
    store: RuntimeStore,
    runtime_dir: Path,
    default_executor_factory: Callable[[], NodeExecutor],
    shared_table_executor_factory: Callable[..., NodeExecutor],
) -> DefaultWorkflowProcessExecutorOwner:
    return DefaultWorkflowProcessExecutorOwner(
        store=store,
        runtime_dir=runtime_dir,
        default_executor_factory=default_executor_factory,
        shared_table_executor_factory=shared_table_executor_factory,
    )


def build_node_task_execute(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None,
    heartbeat_interval_seconds: float,
    task_manager: NodeTaskManager,
    cleanup_staging_for_node: CleanupStagingForNode | None,
    cancel_grace_seconds: float,
) -> Callable[[DispatchedNodeTask], NodeTaskResultModel | None]:
    if process_generation is None:
        return lambda _dispatched_task: None

    active_generation = process_generation

    def execute_task(dispatched_task: DispatchedNodeTask) -> NodeTaskResultModel | None:
        return supervision.execute_node_task_with_supervision(
            store=store,
            workflow_run_id=workflow_run_id,
            workflow_process_id=process_id,
            process_generation=active_generation,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            task_manager=task_manager,
            executor=dispatched_task.executor,
            cleanup_staging_for_node=cleanup_staging_for_node,
            cancel_grace_seconds=cancel_grace_seconds,
            task=dispatched_task.task,
        )

    return execute_task


def close_execution_pool(execution_pool: object | None) -> None:
    if execution_pool is None:
        return
    close = getattr(execution_pool, "close", None)
    if not callable(close):
        return
    try:
        close(timeout_seconds=0)
    except TypeError:
        try:
            close()
        except Exception:
            pass
    except Exception:
        pass
