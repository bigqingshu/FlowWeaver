from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from flowweaver.common.config import MemoryTableLimits, WorkflowProcessExecutionMode
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.node_executor import NodeExecutor
from flowweaver.plugin_runtime.catalog import PluginCatalog
from flowweaver.protocols.node_task import NodeTaskResultModel
from flowweaver.workflow_process import task_supervision as supervision
from flowweaver.workflow_process.executor_owner import (
    DefaultWorkflowProcessExecutorOwner,
)
from flowweaver.workflow_process.executor_pool import (
    DispatchedNodeTask,
    ImmediateNodeTaskExecutionPool,
    NodeTaskExecutionPool,
    ThreadedNodeTaskExecutionPool,
)
from flowweaver.workflow_process.node_tasks import NodeTaskManager
from flowweaver.workflow_process.task_supervision import (
    RefreshRuntimeOptionsForTask,
)

CleanupStagingForNode = Callable[[str, str], None]


def create_default_workflow_process_executor_owner(
    *,
    store: RuntimeStore,
    runtime_dir: Path,
    memory_table_limits: MemoryTableLimits,
    default_executor_factory: Callable[[], NodeExecutor],
    shared_table_executor_factory: Callable[..., NodeExecutor],
    plugin_catalog: PluginCatalog | None = None,
    plugin_executor_factory: Callable[..., NodeExecutor] | None = None,
) -> DefaultWorkflowProcessExecutorOwner:
    kwargs = {}
    if plugin_executor_factory is not None:
        kwargs["plugin_executor_factory"] = plugin_executor_factory
    return DefaultWorkflowProcessExecutorOwner(
        store=store,
        runtime_dir=runtime_dir,
        memory_table_limits=memory_table_limits,
        default_executor_factory=default_executor_factory,
        shared_table_executor_factory=shared_table_executor_factory,
        plugin_catalog=plugin_catalog,
        **kwargs,
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
    refresh_runtime_options_for_task: RefreshRuntimeOptionsForTask | None = None,
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
            refresh_runtime_options_for_task=refresh_runtime_options_for_task,
        )

    return execute_task


def create_node_task_execution_pool(
    *,
    execution_mode: WorkflowProcessExecutionMode,
    execute_task: Callable[[DispatchedNodeTask], NodeTaskResultModel | None],
) -> NodeTaskExecutionPool:
    if execution_mode == "threaded":
        return ThreadedNodeTaskExecutionPool(execute_task=execute_task)
    return ImmediateNodeTaskExecutionPool(execute_task=execute_task)


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
