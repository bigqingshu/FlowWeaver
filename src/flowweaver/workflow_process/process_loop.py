from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from flowweaver.common.config import MemoryTableLimits, WorkflowProcessExecutionMode
from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.node_executor import NodeExecutorFactory
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
from flowweaver.workflow_process.executor_pool import NodeTaskExecutionPool
from flowweaver.workflow_process.runtime_logger import WorkflowRuntimeLogger

CleanupStagingForNode = execution_helpers.CleanupStagingForNode


def run_workflow_process_loop(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    heartbeat_interval_seconds: float,
    process_generation: int | None,
    event_sink: RuntimeEventSink,
    runtime_dir: Path,
    memory_table_limits: MemoryTableLimits,
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
        loaded_definition = process_definition.load_workflow_process_definition(
            store=store,
            workflow_run_id=workflow_run_id,
        )
    except process_definition.WorkflowProcessDefinitionError as exc:
        return finalization.fail_workflow_process(
            store,
            workflow_run_id,
            process_id,
            str(exc),
            process_generation=process_generation,
        )
    run = loaded_definition.run
    definition = loaded_definition.definition

    (
        runtime_feedback_policy_provider,
        event_sink,
        runtime_options_poller,
    ) = (
        process_runtime_options.configure_runtime_options_event_sink(
            definition=definition,
            event_sink=event_sink,
            store=store,
            workflow_run_id=workflow_run_id,
            process_id=process_id,
        )
    )

    process_startup.mark_workflow_process_started(
        store=store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        run=run,
        event_sink=event_sink,
    )
    runtime_logger = WorkflowRuntimeLogger(
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        logger_name="flowweaver.workflow_process",
        policy_provider=runtime_feedback_policy_provider,
        event_sink=event_sink,
    )
    runtime_logger.debug(
        "workflow runtime feedback configured",
        context={"runtime_options_version": runtime_feedback_policy_provider.version},
    )
    runtime_options_poller.acknowledge_loaded_version()

    try:
        dag = process_dag.prepare_workflow_process_dag(
            definition=definition,
            run=run,
        )
    except process_dag.WorkflowProcessDagError as exc:
        return finalization.fail_workflow_process(
            store,
            workflow_run_id,
            process_id,
            str(exc),
            process_generation=process_generation,
        )
    if not dag.nodes:
        return finalization.complete_empty_workflow(
            store,
            workflow_run_id,
            process_id,
            process_generation=process_generation,
            event_sink=event_sink,
        )
    runtime_initialization = (
        process_runtime_initialization.initialize_workflow_process_runtime(
            store=store,
            event_sink=event_sink,
            definition=definition,
            workflow_run_id=workflow_run_id,
            process_id=process_id,
            process_generation=process_generation,
            dag=dag,
            runtime_dir=runtime_dir,
            memory_table_limits=memory_table_limits,
            runtime_feedback_policy_provider=runtime_feedback_policy_provider,
            runtime_logger=runtime_logger,
        )
    )
    task_manager = runtime_initialization.task_manager
    if execution_pool is None:
        refresh_runtime_options_for_task = None
        if execution_mode == "immediate":

            def refresh_runtime_options_for_task(task, executor) -> None:
                if runtime_options_poller.poll_if_due():
                    ipc_events.push_runtime_options_to_task(
                        task=task,
                        node_instance_id=task.node_instance_id,
                        executor=executor,
                        task_manager=task_manager,
                    )

        execute_task = execution_helpers.build_node_task_execute(
            store=store,
            workflow_run_id=workflow_run_id,
            process_id=process_id,
            process_generation=process_generation,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            task_manager=task_manager,
            cleanup_staging_for_node=cleanup_staging_for_node,
            cancel_grace_seconds=cancel_grace_seconds,
            refresh_runtime_options_for_task=refresh_runtime_options_for_task,
        )
        execution_pool = execution_helpers.create_node_task_execution_pool(
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
        cancel_requested = process_cancellation.request_workflow_cancel_if_requested(
            store=store,
            process_id=process_id,
            execution_pool=execution_pool,
        )
        if finalization.finalize_if_workflow_run_terminal(store, workflow_run_id):
            return 0
        if runtime_options_poller.poll_if_due():
            ipc_events.push_runtime_options_to_in_flight_tasks(
                execution_pool=execution_pool,
                task_manager=task_manager,
            )
        completed_count = task_dispatch.drain_executor_task_completions(
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
        if finalization.finalize_if_workflow_run_terminal(store, workflow_run_id):
            return 0
        if cancel_requested and process_cancellation.finalize_workflow_cancel_if_idle(
            store=store,
            workflow_run_id=workflow_run_id,
            process_id=process_id,
            process_generation=process_generation,
            execution_pool=execution_pool,
            event_sink=event_sink,
        ):
            return 0
        dispatched_count = 0
        if not cancel_requested:
            dispatched_count = task_dispatch.dispatch_ready_nodes(
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
        if finalization.finalize_if_workflow_run_terminal(store, workflow_run_id):
            return 0
        if finalization.complete_continue_independent_partial_failure_if_finished(
            store=store,
            workflow_run_id=workflow_run_id,
            workflow_process_id=process_id,
            process_generation=process_generation,
            failure_policy_mode=definition.failure_policy.mode,
            dag=dag,
            event_sink=event_sink,
        ):
            finalization.release_unreleased_read_leases_for_terminal_workflow(
                store,
                workflow_run_id,
            )
            return 0
        if completed_count == 0 and dispatched_count == 0:
            sleep_func(heartbeat_interval_seconds)
