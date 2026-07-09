from __future__ import annotations

from collections.abc import Callable

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.node_executor import NodeExecutorFactory
from flowweaver.workflow_process import ipc_events
from flowweaver.workflow_process import process_finalization as finalization
from flowweaver.workflow_process.dag import WorkflowDag
from flowweaver.workflow_process.executor_owner import close_executor
from flowweaver.workflow_process.executor_pool import NodeTaskExecutionPool
from flowweaver.workflow_process.node_tasks import (
    NodeTaskManager,
)
from flowweaver.workflow_process.ready_queue import (
    collect_ready_node_candidates,
)
from flowweaver.workflow_process.task_candidate_dispatch import (
    dispatch_ready_node_candidate as dispatch_ready_node_candidate,
)
from flowweaver.workflow_process.task_completion import (
    apply_executor_task_completion,
)
from flowweaver.workflow_process.task_completion import (
    apply_node_task_result as apply_node_task_result,
)
from flowweaver.workflow_process.task_completion import (
    fail_rejected_node_result as fail_rejected_node_result,
)
from flowweaver.workflow_process.task_completion_drain import (
    drain_executor_task_completions as drain_executor_task_completions,
)
from flowweaver.workflow_process.task_dispatch_config import (
    timeout_seconds_from_node_config as timeout_seconds_from_node_config,
)
from flowweaver.workflow_process.task_dispatch_limits import (
    available_ready_dispatch_slots as available_ready_dispatch_slots,
)
from flowweaver.workflow_process.task_input_resolution_failure import (
    fail_ready_node_input_resolution as fail_ready_node_input_resolution,
)

CleanupStagingForNode = Callable[[str, str], None]

_configure_executor_event_handler = ipc_events.configure_executor_event_handler
_workflow_run_is_terminal = finalization.workflow_run_is_terminal


def dispatch_ready_nodes(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int | None,
    heartbeat_interval_seconds: float,
    dag: WorkflowDag,
    task_manager: NodeTaskManager,
    executor_factory: NodeExecutorFactory,
    cleanup_staging_for_node: CleanupStagingForNode | None,
    close_executor_after_task: bool,
    cancel_grace_seconds: float,
    max_ready_dispatch_per_cycle: int | None,
    max_concurrent_node_tasks: int | None,
    execution_pool: NodeTaskExecutionPool,
    event_sink: RuntimeEventSink,
) -> int:
    if process_generation is None:
        return 0
    dispatched_count = 0
    max_dispatch_count = available_ready_dispatch_slots(
        store=store,
        workflow_run_id=workflow_run_id,
        max_ready_dispatch_per_cycle=max_ready_dispatch_per_cycle,
        max_concurrent_node_tasks=max_concurrent_node_tasks,
    )
    if max_dispatch_count == 0:
        return 0
    ready_candidates = collect_ready_node_candidates(
        store=store,
        workflow_run_id=workflow_run_id,
        dag=dag,
    )
    for candidate in ready_candidates:
        if max_dispatch_count is not None and dispatched_count >= max_dispatch_count:
            break
        dispatched = dispatch_ready_node_candidate(
            workflow_run_id=workflow_run_id,
            workflow_process_id=workflow_process_id,
            process_generation=process_generation,
            candidate=candidate,
            task_manager=task_manager,
            executor_factory=executor_factory,
            close_executor_on_reject=close_executor_after_task,
        )
        if dispatched is None:
            continue
        _configure_executor_event_handler(
            dispatched.executor,
            store=store,
            workflow_process_id=workflow_process_id,
            task_manager=task_manager,
            process_generation=process_generation,
        )
        if not execution_pool.submit(dispatched):
            if close_executor_after_task:
                close_executor(dispatched.executor)
            continue
        completion = execution_pool.pop_completed()
        if completion is not None:
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
        dispatched_count += 1
        if _workflow_run_is_terminal(store, workflow_run_id):
            break
    return dispatched_count


