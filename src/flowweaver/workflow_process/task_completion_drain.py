from __future__ import annotations

from collections.abc import Callable

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.workflow_process import process_finalization as finalization
from flowweaver.workflow_process.executor_pool import NodeTaskExecutionPool
from flowweaver.workflow_process.node_tasks import NodeTaskManager
from flowweaver.workflow_process.task_completion import (
    apply_executor_task_completion,
)

CleanupStagingForNode = Callable[[str, str], None]

_workflow_run_is_terminal = finalization.workflow_run_is_terminal


def drain_executor_task_completions(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int | None,
    event_sink: RuntimeEventSink,
    task_manager: NodeTaskManager,
    cleanup_staging_for_node: CleanupStagingForNode | None,
    close_executor_after_task: bool,
    execution_pool: NodeTaskExecutionPool,
) -> int:
    completed_count = 0
    while True:
        completion = execution_pool.pop_completed()
        if completion is None:
            return completed_count
        apply_executor_task_completion(
            store=store,
            workflow_run_id=workflow_run_id,
            workflow_process_id=workflow_process_id,
            process_generation=process_generation,
            event_sink=event_sink,
            task_manager=task_manager,
            cleanup_staging_for_node=cleanup_staging_for_node,
            close_executor_after_task=close_executor_after_task,
            completion=completion,
        )
        completed_count += 1
        if _workflow_run_is_terminal(store, workflow_run_id):
            return completed_count
