from __future__ import annotations

import argparse
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

from flowweaver.common.config import (
    WorkflowProcessExecutionMode,
    resolve_workflow_process_execution_mode,
    resolve_workflow_process_max_concurrent_node_tasks,
)
from flowweaver.engine.runtime_event_sink import (
    DatabaseEventSink,
    IPCEventSink,
    RuntimeEventSink,
)
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.node_executor import (
    BuiltinSharedTableNodeExecutor,
    NodeExecutorFactory,
    SubprocessNodeExecutorIpcClient,
)
from flowweaver.workflow_process import (
    ipc_events,
    process_cancellation,
    process_dag,
    process_definition,
    process_runtime_initialization,
    process_runtime_options,
    process_startup,
    task_dispatch,
)
from flowweaver.workflow_process import process_execution_helpers as execution_helpers
from flowweaver.workflow_process import process_finalization as finalization
from flowweaver.workflow_process import task_supervision as supervision
from flowweaver.workflow_process.executor_owner import (
    DefaultWorkflowProcessExecutorOwner,
)
from flowweaver.workflow_process.executor_pool import (
    NodeTaskExecutionPool,
)

CleanupStagingForNode = execution_helpers.CleanupStagingForNode
_complete_continue_independent_partial_failure_if_finished = (
    finalization.complete_continue_independent_partial_failure_if_finished
)
_complete_empty_workflow = finalization.complete_empty_workflow
_fail = finalization.fail_workflow_process
_finalize_if_workflow_run_terminal = finalization.finalize_if_workflow_run_terminal
_release_unreleased_read_leases_for_terminal_workflow = (
    finalization.release_unreleased_read_leases_for_terminal_workflow
)
_workflow_run_is_terminal = finalization.workflow_run_is_terminal
_cancel_workflow_process_if_requested = (
    process_cancellation.cancel_workflow_process_if_requested
)
_load_workflow_process_definition = (
    process_definition.load_workflow_process_definition
)
_prepare_workflow_process_dag = process_dag.prepare_workflow_process_dag
_configure_runtime_options_event_sink = (
    process_runtime_options.configure_runtime_options_event_sink
)
_initialize_workflow_process_runtime = (
    process_runtime_initialization.initialize_workflow_process_runtime
)
_mark_workflow_process_started = process_startup.mark_workflow_process_started
_cancel_grace_period_expired = supervision.cancel_grace_period_expired
_cancelled_task_result = supervision.cancelled_task_result
_cleanup_staging_for_node = supervision.cleanup_staging_for_node_safely
_execute_node_task_with_supervision = supervision.execute_node_task_with_supervision
_get_node_task_execution_result = supervision.get_node_task_execution_result
_mark_node_cancel_requested = supervision.mark_node_cancel_requested
_request_cancel = supervision.request_cancel
_request_cancel_for_in_flight_tasks = supervision.request_cancel_for_in_flight_tasks
_task_supervision_poll_seconds = supervision.task_supervision_poll_seconds
_workflow_cancel_was_requested = supervision.workflow_cancel_was_requested
_configure_executor_event_handler = ipc_events.configure_executor_event_handler
_record_node_task_ipc_event = ipc_events.record_node_task_ipc_event

_dispatch_ready_nodes = task_dispatch.dispatch_ready_nodes
_drain_executor_task_completions = task_dispatch.drain_executor_task_completions
_apply_executor_task_completion = task_dispatch.apply_executor_task_completion
dispatch_ready_node_candidate = task_dispatch.dispatch_ready_node_candidate
_fail_ready_node_input_resolution = task_dispatch.fail_ready_node_input_resolution
_available_ready_dispatch_slots = task_dispatch.available_ready_dispatch_slots
_apply_node_task_result = task_dispatch.apply_node_task_result
_timeout_seconds_from_node_config = task_dispatch.timeout_seconds_from_node_config
_fail_rejected_node_result = task_dispatch.fail_rejected_node_result
_build_node_task_execute = execution_helpers.build_node_task_execute
_create_node_task_execution_pool = execution_helpers.create_node_task_execution_pool
_close_execution_pool = execution_helpers.close_execution_pool


def _DefaultWorkflowProcessExecutorOwner(
    *, store: RuntimeStore, runtime_dir: Path
) -> DefaultWorkflowProcessExecutorOwner:
    return execution_helpers.create_default_workflow_process_executor_owner(
        store=store,
        runtime_dir=runtime_dir,
        default_executor_factory=SubprocessNodeExecutorIpcClient,
        shared_table_executor_factory=BuiltinSharedTableNodeExecutor,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--process-id", required=True)
    parser.add_argument("--process-generation", type=int, required=True)
    parser.add_argument("--heartbeat-interval-seconds", type=float, default=2.0)
    parser.add_argument("--runtime-event-path")
    parser.add_argument("--runtime-dir")
    parser.add_argument("--execution-mode")
    parser.add_argument("--max-concurrent-node-tasks")
    args = parser.parse_args(argv)
    store = RuntimeStore(args.database_url)
    try:
        event_sink: RuntimeEventSink = (
            IPCEventSink(args.runtime_event_path)
            if args.runtime_event_path
            else DatabaseEventSink(store)
        )
        return run_workflow_process(
            store=store,
            workflow_run_id=args.workflow_run_id,
            process_id=args.process_id,
            process_generation=args.process_generation,
            heartbeat_interval_seconds=args.heartbeat_interval_seconds,
            event_sink=event_sink,
            runtime_dir=args.runtime_dir,
            execution_mode=args.execution_mode,
            max_concurrent_node_tasks=args.max_concurrent_node_tasks,
        )
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        store.dispose()


def run_workflow_process(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    heartbeat_interval_seconds: float,
    process_generation: int | None = None,
    event_sink: RuntimeEventSink | None = None,
    runtime_dir: Path | str | None = None,
    executor_factory: NodeExecutorFactory | None = None,
    cleanup_staging_for_node: CleanupStagingForNode | None = None,
    cancel_grace_seconds: float = 5.0,
    max_ready_dispatch_per_cycle: int | None = None,
    max_concurrent_node_tasks: int | str | None = None,
    execution_mode: WorkflowProcessExecutionMode | str | None = None,
    execution_pool: NodeTaskExecutionPool | None = None,
    sleep_func: Callable[[float], None] = time.sleep,
) -> int:
    event_sink = event_sink or DatabaseEventSink(store)
    resolved_execution_mode = resolve_workflow_process_execution_mode(execution_mode)
    resolved_max_concurrent_node_tasks = (
        resolve_workflow_process_max_concurrent_node_tasks(max_concurrent_node_tasks)
    )
    resolved_runtime_dir = Path(runtime_dir or Path("runtime") / "workflow_runs")
    reusable_executor_owner: DefaultWorkflowProcessExecutorOwner | None = None
    close_executor_after_task = True
    if executor_factory is None:
        reusable_executor_owner = _DefaultWorkflowProcessExecutorOwner(
            store=store,
            runtime_dir=resolved_runtime_dir,
        )
        executor_factory = reusable_executor_owner.executor_for_task
        close_executor_after_task = False
    try:
        return _run_workflow_process_loop(
            store=store,
            workflow_run_id=workflow_run_id,
            process_id=process_id,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            process_generation=process_generation,
            event_sink=event_sink,
            runtime_dir=resolved_runtime_dir,
            executor_factory=executor_factory,
            cleanup_staging_for_node=cleanup_staging_for_node,
            close_executor_after_task=close_executor_after_task,
            cancel_grace_seconds=cancel_grace_seconds,
            max_ready_dispatch_per_cycle=max_ready_dispatch_per_cycle,
            max_concurrent_node_tasks=resolved_max_concurrent_node_tasks,
            execution_mode=resolved_execution_mode,
            execution_pool=execution_pool,
            sleep_func=sleep_func,
        )
    finally:
        _close_execution_pool(execution_pool)
        if reusable_executor_owner is not None:
            reusable_executor_owner.close()


def _run_workflow_process_loop(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    heartbeat_interval_seconds: float,
    process_generation: int | None,
    event_sink: RuntimeEventSink,
    runtime_dir: Path,
    executor_factory: NodeExecutorFactory,
    cleanup_staging_for_node: CleanupStagingForNode | None,
    close_executor_after_task: bool,
    cancel_grace_seconds: float,
    max_ready_dispatch_per_cycle: int | None,
    max_concurrent_node_tasks: int | None,
    execution_mode: WorkflowProcessExecutionMode,
    execution_pool: NodeTaskExecutionPool | None,
    sleep_func: Callable[[float], None],
) -> int:
    if (
        process_generation is not None
        and not store.workflow_run_is_owned_by(
            workflow_run_id=workflow_run_id,
            process_id=process_id,
            process_generation=process_generation,
        )
    ):
        return 1
    try:
        loaded_definition = _load_workflow_process_definition(
            store=store,
            workflow_run_id=workflow_run_id,
        )
    except process_definition.WorkflowProcessDefinitionError as exc:
        return _fail(
            store,
            workflow_run_id,
            process_id,
            str(exc),
            process_generation=process_generation,
        )
    run = loaded_definition.run
    definition = loaded_definition.definition

    runtime_options_by_node, event_sink = _configure_runtime_options_event_sink(
        definition=definition,
        event_sink=event_sink,
    )

    _mark_workflow_process_started(
        store=store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        run=run,
        event_sink=event_sink,
    )

    try:
        dag = _prepare_workflow_process_dag(
            definition=definition,
            run=run,
        )
    except process_dag.WorkflowProcessDagError as exc:
        return _fail(
            store,
            workflow_run_id,
            process_id,
            str(exc),
            process_generation=process_generation,
        )
    if not dag.nodes:
        return _complete_empty_workflow(
            store,
            workflow_run_id,
            process_id,
            process_generation=process_generation,
            event_sink=event_sink,
        )
    runtime_initialization = _initialize_workflow_process_runtime(
        store=store,
        event_sink=event_sink,
        definition=definition,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        dag=dag,
        runtime_dir=runtime_dir,
        runtime_options_by_node=runtime_options_by_node,
    )
    task_manager = runtime_initialization.task_manager
    if execution_pool is None:
        execute_task = _build_node_task_execute(
            store=store,
            workflow_run_id=workflow_run_id,
            process_id=process_id,
            process_generation=process_generation,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            task_manager=task_manager,
            cleanup_staging_for_node=cleanup_staging_for_node,
            cancel_grace_seconds=cancel_grace_seconds,
        )
        execution_pool = _create_node_task_execution_pool(
            execution_mode=execution_mode,
            execute_task=execute_task,
        )

    while True:
        heartbeat = store.record_workflow_process_heartbeat(
            process_id,
            process_generation=process_generation,
        )
        if heartbeat is None:
            return 1
        if _cancel_workflow_process_if_requested(
            store=store,
            workflow_run_id=workflow_run_id,
            process_id=process_id,
            process_generation=process_generation,
            execution_pool=execution_pool,
            event_sink=event_sink,
        ):
            return 0
        if _finalize_if_workflow_run_terminal(store, workflow_run_id):
            return 0
        completed_count = _drain_executor_task_completions(
            store=store,
            workflow_run_id=workflow_run_id,
            workflow_process_id=process_id,
            process_generation=process_generation,
            event_sink=event_sink,
            task_manager=task_manager,
            cleanup_staging_for_node=cleanup_staging_for_node,
            close_executor_after_task=close_executor_after_task,
            execution_pool=execution_pool,
        )
        if _finalize_if_workflow_run_terminal(store, workflow_run_id):
            return 0
        dispatched_count = _dispatch_ready_nodes(
            store=store,
            workflow_run_id=workflow_run_id,
            workflow_process_id=process_id,
            process_generation=process_generation,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            dag=dag,
            task_manager=task_manager,
            executor_factory=executor_factory,
            cleanup_staging_for_node=cleanup_staging_for_node,
            close_executor_after_task=close_executor_after_task,
            cancel_grace_seconds=cancel_grace_seconds,
            max_ready_dispatch_per_cycle=max_ready_dispatch_per_cycle,
            max_concurrent_node_tasks=max_concurrent_node_tasks,
            execution_pool=execution_pool,
            event_sink=event_sink,
        )
        if _finalize_if_workflow_run_terminal(store, workflow_run_id):
            return 0
        if _complete_continue_independent_partial_failure_if_finished(
            store=store,
            workflow_run_id=workflow_run_id,
            workflow_process_id=process_id,
            process_generation=process_generation,
            failure_policy_mode=definition.failure_policy.mode,
            dag=dag,
            event_sink=event_sink,
        ):
            _release_unreleased_read_leases_for_terminal_workflow(
                store,
                workflow_run_id,
            )
            return 0
        if completed_count == 0 and dispatched_count == 0:
            sleep_func(heartbeat_interval_seconds)


def _exit() -> NoReturn:
    raise SystemExit(main())


if __name__ == "__main__":
    _exit()
