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
from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import (
    DatabaseEventSink,
    IPCEventSink,
    RuntimeEventSink,
)
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.table_provider_registry import (
    create_default_table_provider_registry,
)
from flowweaver.node_executor import (
    BuiltinSharedTableNodeExecutor,
    NodeExecutorFactory,
    SubprocessNodeExecutorIpcClient,
)
from flowweaver.protocols.enums import (
    EventType,
    NodeResultStatus,
    NodeRunStatus,
    WorkflowRunStatus,
)
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow.definition import (
    UNAVAILABLE_FAILURE_POLICY_MODES,
    WorkflowDefinitionModel,
    failure_policy_unavailable_message,
)
from flowweaver.workflow.runtime_options import (
    RuntimeOptionsEventSink,
    resolve_runtime_options_by_node,
    resolve_workflow_runtime_options,
)
from flowweaver.workflow_process import ipc_events
from flowweaver.workflow_process import process_finalization as finalization
from flowweaver.workflow_process import task_supervision as supervision
from flowweaver.workflow_process.controller import (
    initialize_node_runs,
    recover_ready_nodes,
)
from flowweaver.workflow_process.dag import (
    WorkflowDag,
    build_workflow_dag,
    restrict_workflow_dag_to_upstream_closure,
)
from flowweaver.workflow_process.executor_owner import (
    DefaultWorkflowProcessExecutorOwner,
    close_executor,
)
from flowweaver.workflow_process.executor_pool import (
    DispatchedNodeTask,
    ExecutorTaskCompletion,
    ImmediateNodeTaskExecutionPool,
    NodeTaskExecutionPool,
    ThreadedNodeTaskExecutionPool,
)
from flowweaver.workflow_process.loop_recovery import (
    recover_serial_loop_runtime_state,
)
from flowweaver.workflow_process.loop_runtime_initialization import (
    initialize_enabled_loop_runtime_state,
)
from flowweaver.workflow_process.loop_terminal_state import (
    cancel_active_loop_runs_for_workflow,
)
from flowweaver.workflow_process.node_tasks import (
    NodeTaskApplyResult,
    NodeTaskApplyStatus,
    NodeTaskManager,
)
from flowweaver.workflow_process.ready_queue import (
    ReadyNodeCandidate,
    collect_ready_node_candidates,
    count_in_flight_node_runs,
)

CleanupStagingForNode = Callable[[str, str], None]
_complete_continue_independent_partial_failure_if_finished = (
    finalization.complete_continue_independent_partial_failure_if_finished
)
_complete_empty_workflow = finalization.complete_empty_workflow
_finalize_if_workflow_run_terminal = finalization.finalize_if_workflow_run_terminal
_release_unreleased_read_leases_for_terminal_workflow = (
    finalization.release_unreleased_read_leases_for_terminal_workflow
)
_workflow_run_is_terminal = finalization.workflow_run_is_terminal
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

_HANDLED_NODE_TASK_APPLY_STATUSES = frozenset(
    {
        NodeTaskApplyStatus.APPLIED,
        NodeTaskApplyStatus.ALREADY_APPLIED,
    }
)
_IGNORED_NODE_TASK_APPLY_STATUSES = frozenset(
    {
        NodeTaskApplyStatus.REJECTED_STALE_ATTEMPT,
        NodeTaskApplyStatus.REJECTED_STALE_GENERATION,
        NodeTaskApplyStatus.REJECTED_NODE_TERMINAL,
    }
)


class _DefaultWorkflowProcessExecutorOwner(DefaultWorkflowProcessExecutorOwner):
    def __init__(self, *, store: RuntimeStore, runtime_dir: Path) -> None:
        super().__init__(
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
    reusable_executor_owner: _DefaultWorkflowProcessExecutorOwner | None = None
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
    run = store.get_workflow_run(workflow_run_id)
    if run is None or run.revision_id is None:
        return _fail(
            store,
            workflow_run_id,
            process_id,
            "Workflow run not found",
            process_generation=process_generation,
        )
    revision = store.get_workflow_revision(run.revision_id)
    if revision is None:
        return _fail(
            store,
            workflow_run_id,
            process_id,
            "Workflow revision not found",
            process_generation=process_generation,
        )

    definition = WorkflowDefinitionModel.model_validate(revision.definition)
    if definition.failure_policy.mode in UNAVAILABLE_FAILURE_POLICY_MODES:
        return _fail(
            store,
            workflow_run_id,
            process_id,
            failure_policy_unavailable_message(definition.failure_policy.mode),
            process_generation=process_generation,
        )

    runtime_options_by_node = resolve_runtime_options_by_node(definition)
    event_sink = RuntimeOptionsEventSink(
        event_sink,
        workflow_options=resolve_workflow_runtime_options(definition),
        runtime_options_by_node=runtime_options_by_node,
    )

    store.record_workflow_process_heartbeat(
        process_id,
        process_generation=process_generation,
    )
    if (
        current_run := store.get_workflow_run(workflow_run_id)
    ) is not None and current_run.status == WorkflowRunStatus.PENDING.value:
        store.update_workflow_run_status(
            workflow_run_id,
            WorkflowRunStatus.RUNNING,
            expected_state_version=current_run.state_version,
            allowed_source_statuses=[WorkflowRunStatus.PENDING],
            owner_process_id=process_id if process_generation is not None else None,
            process_generation=process_generation,
        )
    event_sink.emit(
        EventModel(
            event_type=EventType.WORKFLOW_STARTED,
            workflow_run_id=workflow_run_id,
            payload={
                "process_id": process_id,
                "run_mode": run.run_mode,
                "trigger_source": run.trigger_source,
                "target_node_instance_id": run.target_node_instance_id,
            },
        )
    )

    dag = build_workflow_dag(definition)
    if run.run_mode == "preview_to_node":
        if not run.target_node_instance_id:
            return _fail(
                store,
                workflow_run_id,
                process_id,
                "target_node_instance_id is required for preview_to_node",
                process_generation=process_generation,
            )
        try:
            dag = restrict_workflow_dag_to_upstream_closure(
                dag,
                run.target_node_instance_id,
            )
        except ValueError as exc:
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
    initialize_node_runs(
        store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        dag=dag,
    )
    initialize_enabled_loop_runtime_state(
        store,
        definition=definition,
        workflow_run_id=workflow_run_id,
        dag=dag,
    )
    recover_ready_nodes(
        store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        dag=dag,
    )
    table_provider_registry = create_default_table_provider_registry(runtime_dir)
    recover_serial_loop_runtime_state(
        store,
        table_provider_registry,
        workflow_run_id=workflow_run_id,
        dag=dag,
        process_id=process_id,
        process_generation=process_generation,
    )
    task_manager = NodeTaskManager(
        store=store,
        event_sink=event_sink,
        dag=dag,
        failure_policy_mode=definition.failure_policy.mode,
        runtime_options_by_node=runtime_options_by_node,
        table_provider_registry=table_provider_registry,
    )
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
        if execution_mode == "threaded":
            execution_pool = ThreadedNodeTaskExecutionPool(execute_task=execute_task)
        else:
            execution_pool = ImmediateNodeTaskExecutionPool(execute_task=execute_task)

    while True:
        heartbeat = store.record_workflow_process_heartbeat(
            process_id,
            process_generation=process_generation,
        )
        if heartbeat is None:
            return 1
        process = store.get_workflow_process(process_id)
        if process is not None and process.cancel_requested_at is not None:
            _request_cancel_for_in_flight_tasks(
                store=store,
                execution_pool=execution_pool,
            )
            cancel_active_loop_runs_for_workflow(
                store,
                workflow_run_id=workflow_run_id,
                error={
                    "message": "Workflow run cancelled",
                    "reason": "WORKFLOW_CANCEL_REQUESTED",
                },
            )
            store.update_workflow_run_status(
                workflow_run_id,
                WorkflowRunStatus.CANCELLED,
                finished_at=utc_now(),
                allowed_source_statuses=[WorkflowRunStatus.RUNNING],
                owner_process_id=process_id if process_generation is not None else None,
                process_generation=process_generation,
            )
            event_sink.emit(
                EventModel(
                    event_type=EventType.WORKFLOW_CANCELLED,
                    workflow_run_id=workflow_run_id,
                    payload={"process_id": process_id},
                )
            )
            _release_unreleased_read_leases_for_terminal_workflow(
                store,
                workflow_run_id,
            )
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


def _build_node_task_execute(
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
        return _execute_node_task_with_supervision(
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


def _dispatch_ready_nodes(
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
    max_dispatch_count = _available_ready_dispatch_slots(
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
            _apply_executor_task_completion(
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


def _drain_executor_task_completions(
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
        _apply_executor_task_completion(
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


def _apply_executor_task_completion(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int | None,
    event_sink: RuntimeEventSink,
    task_manager: NodeTaskManager,
    cleanup_staging_for_node: CleanupStagingForNode | None,
    close_executor_after_task: bool,
    completion: ExecutorTaskCompletion,
) -> None:
    dispatched = completion.dispatched_task
    try:
        result = completion.result
        if result is None:
            return
        apply_result = _apply_node_task_result(
            store=store,
            workflow_run_id=workflow_run_id,
            workflow_process_id=workflow_process_id,
            process_generation=process_generation,
            event_sink=event_sink,
            task_manager=task_manager,
            task=dispatched.task,
            result=result,
        )
        if (
            result.status != NodeResultStatus.SUCCEEDED
            and apply_result.status not in _IGNORED_NODE_TASK_APPLY_STATUSES
        ):
            _cleanup_staging_for_node(
                cleanup_staging_for_node,
                workflow_run_id=workflow_run_id,
                node_run_id=dispatched.node_run_id,
            )
    finally:
        if close_executor_after_task:
            close_executor(dispatched.executor)


def dispatch_ready_node_candidate(
    *,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int,
    candidate: ReadyNodeCandidate,
    task_manager: NodeTaskManager,
    executor_factory: NodeExecutorFactory,
    close_executor_on_reject: bool = True,
) -> DispatchedNodeTask | None:
    if candidate.input_resolution_issue is not None:
        _fail_ready_node_input_resolution(
            workflow_run_id=workflow_run_id,
            workflow_process_id=workflow_process_id,
            process_generation=process_generation,
            candidate=candidate,
            task_manager=task_manager,
        )
        return None
    task = task_manager.submit_ready_node(
        workflow_run_id=workflow_run_id,
        workflow_process_id=workflow_process_id,
        process_generation=process_generation,
        node_instance_id=candidate.node_run.node_instance_id,
        node_run_id=candidate.node_run.node_run_id,
        input_refs=list(candidate.input_refs),
        input_slot_bindings=candidate.input_slot_bindings,
        timeout_seconds=_timeout_seconds_from_node_config(candidate.dag_node.config),
    )
    if task is None:
        return None
    executor = executor_factory(task)
    accepted = task_manager.accept_task(
        task_id=task.task_id,
        executor_id=executor.executor_id,
    )
    if accepted is None:
        if close_executor_on_reject:
            close_executor(executor)
        return None
    return DispatchedNodeTask(
        task=accepted,
        executor=executor,
        node_run_id=accepted.node_run_id,
        node_instance_id=accepted.node_instance_id,
        executor_id=executor.executor_id,
    )


def _fail_ready_node_input_resolution(
    *,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int,
    candidate: ReadyNodeCandidate,
    task_manager: NodeTaskManager,
) -> None:
    task = task_manager.submit_ready_node(
        workflow_run_id=workflow_run_id,
        workflow_process_id=workflow_process_id,
        process_generation=process_generation,
        node_instance_id=candidate.node_run.node_instance_id,
        node_run_id=candidate.node_run.node_run_id,
        input_refs=list(candidate.input_refs),
        input_slot_bindings=candidate.input_slot_bindings,
        timeout_seconds=_timeout_seconds_from_node_config(candidate.dag_node.config),
    )
    if task is None:
        return None
    executor_id = "workflow_process.input_resolver"
    accepted = task_manager.accept_task(
        task_id=task.task_id,
        executor_id=executor_id,
    )
    if accepted is None:
        return None
    issue = candidate.input_resolution_issue
    message = (
        issue.message
        if issue is not None
        else "Input table selector could not be resolved"
    )
    details = issue.details if issue is not None else {}
    task_manager.apply_result(
        NodeTaskResultModel(
            task_id=accepted.task_id,
            node_run_id=accepted.node_run_id,
            attempt=accepted.attempt,
            executor_id=executor_id,
            process_generation=accepted.process_generation,
            status=NodeResultStatus.FAILED,
            error={
                "code": "INPUT_TABLE_RESOLUTION_FAILED",
                "message": message,
                "details": details,
            },
        )
    )
    return None


def _available_ready_dispatch_slots(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    max_ready_dispatch_per_cycle: int | None,
    max_concurrent_node_tasks: int | None,
) -> int | None:
    limits: list[int] = []
    if max_ready_dispatch_per_cycle is not None:
        limits.append(max(0, max_ready_dispatch_per_cycle))
    if max_concurrent_node_tasks is not None:
        in_flight_count = count_in_flight_node_runs(
            store=store,
            workflow_run_id=workflow_run_id,
        )
        limits.append(max(0, max_concurrent_node_tasks - in_flight_count))
    if not limits:
        return None
    return min(limits)


def _apply_node_task_result(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int | None,
    event_sink: RuntimeEventSink,
    task_manager: NodeTaskManager,
    task: NodeTaskModel,
    result: NodeTaskResultModel,
) -> NodeTaskApplyResult:
    apply_result = task_manager.apply_result(result)
    if (
        apply_result.status not in _HANDLED_NODE_TASK_APPLY_STATUSES
        and apply_result.status not in _IGNORED_NODE_TASK_APPLY_STATUSES
    ):
        _fail_rejected_node_result(
            store=store,
            workflow_run_id=workflow_run_id,
            workflow_process_id=workflow_process_id,
            process_generation=process_generation,
            event_sink=event_sink,
            task=task,
            result=result,
            apply_result=apply_result,
        )
    return apply_result


def _timeout_seconds_from_node_config(config: dict[str, object]) -> int:
    value = config.get("timeout_seconds")
    if isinstance(value, bool) or not isinstance(value, int):
        return 60
    return max(0, value)


def _close_execution_pool(execution_pool: object | None) -> None:
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


def _fail_rejected_node_result(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    workflow_process_id: str,
    process_generation: int | None,
    event_sink: RuntimeEventSink,
    task: NodeTaskModel,
    result: NodeTaskResultModel,
    apply_result: NodeTaskApplyResult,
) -> None:
    if _workflow_run_is_terminal(store, workflow_run_id):
        return
    error = {
        "message": "Node task result was rejected",
        "apply_status": apply_result.status.value,
        "task_id": task.task_id,
        "result_id": result.result_id,
        "node_instance_id": task.node_instance_id,
    }
    node_run = store.get_node_run(task.node_run_id)
    failed_node = None
    if node_run is not None:
        failed_node = store.update_node_run_status(
            task.node_run_id,
            NodeRunStatus.FAILED,
            finished_at=utc_now(),
            error=error,
            expected_state_version=node_run.state_version,
            allowed_source_statuses=[
                NodeRunStatus.QUEUED,
                NodeRunStatus.RUNNING,
                NodeRunStatus.LONG_RUNNING,
            ],
            owner_process_id=(
                workflow_process_id if process_generation is not None else None
            ),
            process_generation=process_generation,
        )
    failed_run = store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.FAILED,
        finished_at=utc_now(),
        error=error,
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
        owner_process_id=(
            workflow_process_id if process_generation is not None else None
        ),
        process_generation=process_generation,
    )
    if failed_node is not None:
        event_sink.emit(
            EventModel(
                event_type=EventType.NODE_FAILED,
                workflow_run_id=workflow_run_id,
                node_run_id=task.node_run_id,
                payload={
                    "process_id": workflow_process_id,
                    "task_id": task.task_id,
                    "result_id": result.result_id,
                    "apply_status": apply_result.status.value,
                },
            )
        )
    if failed_run is not None:
        event_sink.emit(
            EventModel(
                event_type=EventType.WORKFLOW_FAILED,
                workflow_run_id=workflow_run_id,
                payload={
                    "process_id": workflow_process_id,
                    "task_id": task.task_id,
                    "result_id": result.result_id,
                    "apply_status": apply_result.status.value,
                },
            )
        )


def _fail(
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    message: str,
    process_generation: int | None = None,
) -> int:
    store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.FAILED,
        finished_at=utc_now(),
        error={"message": message},
        allowed_source_statuses=[
            WorkflowRunStatus.PENDING,
            WorkflowRunStatus.RUNNING,
        ],
        owner_process_id=process_id if process_generation is not None else None,
        process_generation=process_generation,
    )
    _release_unreleased_read_leases_for_terminal_workflow(store, workflow_run_id)
    return 1


def _exit() -> NoReturn:
    raise SystemExit(main())


if __name__ == "__main__":
    _exit()
