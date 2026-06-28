from __future__ import annotations

import argparse
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
from threading import Thread
from typing import NoReturn, Protocol, runtime_checkable

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import (
    DatabaseEventSink,
    IPCEventSink,
    RuntimeEventSink,
)
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.node_executor import (
    CancellableNodeExecutor,
    NodeExecutor,
    NodeExecutorFactory,
    SubprocessNodeExecutorIpcClient,
)
from flowweaver.protocols.enums import (
    EventType,
    IPCMessageType,
    NodeResultStatus,
    NodeRunStatus,
    WorkflowRunStatus,
)
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.ipc_messages import (
    IPCEnvelope,
    NodeTaskHeartbeatPayload,
    NodeTaskProgressPayload,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.controller import (
    initialize_node_runs,
    recover_ready_nodes,
)
from flowweaver.workflow_process.dag import WorkflowDag, build_workflow_dag
from flowweaver.workflow_process.node_tasks import (
    NodeTaskApplyResult,
    NodeTaskApplyStatus,
    NodeTaskManager,
    NodeTaskTimeoutStatus,
)
from flowweaver.workflow_process.ready_queue import (
    ReadyNodeCandidate,
    collect_ready_node_candidates,
    count_in_flight_node_runs,
)

CleanupStagingForNode = Callable[[str, str], None]

_TERMINAL_WORKFLOW_STATUSES = frozenset(
    {
        WorkflowRunStatus.SUCCEEDED.value,
        WorkflowRunStatus.FAILED.value,
        WorkflowRunStatus.CANCELLED.value,
        WorkflowRunStatus.ABORTED.value,
    }
)
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


@dataclass(frozen=True)
class DispatchedNodeTask:
    task: NodeTaskModel
    executor: NodeExecutor
    node_run_id: str
    node_instance_id: str
    executor_id: str


@runtime_checkable
class _ClosableExecutor(Protocol):
    def close(self) -> None:
        ...


@runtime_checkable
class _NodeTaskIpcEventAwareExecutor(Protocol):
    executor_id: str

    def set_event_handler(
        self,
        handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None,
    ) -> None:
        ...


class _ReusableSubprocessExecutorOwner:
    def __init__(self) -> None:
        self._executor: SubprocessNodeExecutorIpcClient | None = None

    def executor_for_task(
        self,
        _task: NodeTaskModel,
    ) -> SubprocessNodeExecutorIpcClient:
        if self._executor is None or getattr(self._executor, "closed", False):
            self._executor = SubprocessNodeExecutorIpcClient()
        return self._executor

    def close(self) -> None:
        if self._executor is None:
            return
        _close_executor(self._executor)
        self._executor = None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--process-id", required=True)
    parser.add_argument("--process-generation", type=int, required=True)
    parser.add_argument("--heartbeat-interval-seconds", type=float, default=2.0)
    parser.add_argument("--runtime-event-path")
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
    executor_factory: NodeExecutorFactory | None = None,
    cleanup_staging_for_node: CleanupStagingForNode | None = None,
    cancel_grace_seconds: float = 5.0,
    max_ready_dispatch_per_cycle: int | None = None,
    max_concurrent_node_tasks: int | None = None,
    sleep_func: Callable[[float], None] = time.sleep,
) -> int:
    event_sink = event_sink or DatabaseEventSink(store)
    reusable_executor_owner: _ReusableSubprocessExecutorOwner | None = None
    close_executor_after_task = True
    if executor_factory is None:
        reusable_executor_owner = _ReusableSubprocessExecutorOwner()
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
            executor_factory=executor_factory,
            cleanup_staging_for_node=cleanup_staging_for_node,
            close_executor_after_task=close_executor_after_task,
            cancel_grace_seconds=cancel_grace_seconds,
            max_ready_dispatch_per_cycle=max_ready_dispatch_per_cycle,
            max_concurrent_node_tasks=max_concurrent_node_tasks,
            sleep_func=sleep_func,
        )
    finally:
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
    executor_factory: NodeExecutorFactory,
    cleanup_staging_for_node: CleanupStagingForNode | None,
    close_executor_after_task: bool,
    cancel_grace_seconds: float,
    max_ready_dispatch_per_cycle: int | None,
    max_concurrent_node_tasks: int | None,
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
            payload={"process_id": process_id},
        )
    )

    definition = WorkflowDefinitionModel.model_validate(revision.definition)
    dag = build_workflow_dag(definition)
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
    recover_ready_nodes(
        store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        dag=dag,
    )
    task_manager = NodeTaskManager(store=store, event_sink=event_sink, dag=dag)

    while True:
        heartbeat = store.record_workflow_process_heartbeat(
            process_id,
            process_generation=process_generation,
        )
        if heartbeat is None:
            return 1
        process = store.get_workflow_process(process_id)
        if process is not None and process.cancel_requested_at is not None:
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
            return 0
        if _workflow_run_is_terminal(store, workflow_run_id):
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
            event_sink=event_sink,
        )
        if _workflow_run_is_terminal(store, workflow_run_id):
            return 0
        if dispatched_count == 0:
            sleep_func(heartbeat_interval_seconds)


def _workflow_run_is_terminal(
    store: RuntimeStore,
    workflow_run_id: str,
) -> bool:
    current = store.get_workflow_run(workflow_run_id)
    return current is not None and current.status in _TERMINAL_WORKFLOW_STATUSES


def _complete_empty_workflow(
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None = None,
    event_sink: RuntimeEventSink | None = None,
) -> int:
    event_sink = event_sink or DatabaseEventSink(store)
    current = store.get_workflow_run(workflow_run_id)
    store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.SUCCEEDED,
        finished_at=utc_now(),
        expected_state_version=current.state_version if current is not None else None,
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
        owner_process_id=process_id if process_generation is not None else None,
        process_generation=process_generation,
    )
    event_sink.emit(
        EventModel(
            event_type=EventType.WORKFLOW_FINISHED,
            workflow_run_id=workflow_run_id,
            payload={"process_id": process_id, "empty_workflow": True},
        )
    )
    return 0


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
        try:
            result = _execute_node_task_with_supervision(
                store=store,
                workflow_run_id=workflow_run_id,
                workflow_process_id=workflow_process_id,
                process_generation=process_generation,
                heartbeat_interval_seconds=heartbeat_interval_seconds,
                task_manager=task_manager,
                executor=dispatched.executor,
                cleanup_staging_for_node=cleanup_staging_for_node,
                cancel_grace_seconds=cancel_grace_seconds,
                task=dispatched.task,
            )
            if result is not None:
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
            dispatched_count += 1
            if _workflow_run_is_terminal(store, workflow_run_id):
                break
        finally:
            if close_executor_after_task:
                _close_executor(dispatched.executor)
    return dispatched_count


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
    task = task_manager.submit_ready_node(
        workflow_run_id=workflow_run_id,
        workflow_process_id=workflow_process_id,
        process_generation=process_generation,
        node_instance_id=candidate.node_run.node_instance_id,
        input_refs=list(candidate.input_refs),
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
            _close_executor(executor)
        return None
    return DispatchedNodeTask(
        task=accepted,
        executor=executor,
        node_run_id=accepted.node_run_id,
        node_instance_id=accepted.node_instance_id,
        executor_id=executor.executor_id,
    )


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


def _execute_node_task_with_supervision(
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
    poll_seconds = _task_supervision_poll_seconds(heartbeat_interval_seconds)
    while True:
        result = _get_node_task_execution_result(
            results,
            timeout_seconds=poll_seconds,
        )
        if result is not None:
            if _workflow_cancel_was_requested(
                store=store,
                workflow_process_id=workflow_process_id,
            ) or cancel_requested_at is not None:
                if cancel_requested_at is None:
                    cancel_requested_at = utc_now()
                    _mark_node_cancel_requested(
                        store=store,
                        task=task,
                        executor_id=executor.executor_id,
                    )
                    _request_cancel(executor, task)
                if result.status == NodeResultStatus.CANCELLED:
                    return result
                return _cancelled_task_result(
                    task,
                    executor_id=executor.executor_id,
                )
            return result
        if not worker.is_alive():
            result = _get_node_task_execution_result(results, timeout_seconds=0)
            if result is not None:
                return result
            raise RuntimeError("Node executor finished without a task result")
        heartbeat = store.record_workflow_process_heartbeat(
            workflow_process_id,
            process_generation=process_generation,
        )
        if heartbeat is None:
            _close_executor(executor)
            return None
        timeout_result = task_manager.mark_timed_out_task(task)
        if timeout_result.status == NodeTaskTimeoutStatus.TIMED_OUT:
            _close_executor(executor)
            _cleanup_staging_for_node(
                cleanup_staging_for_node,
                workflow_run_id=workflow_run_id,
                node_run_id=task.node_run_id,
            )
            worker.join(timeout=0.2)
            late_result = _get_node_task_execution_result(
                results,
                timeout_seconds=0,
                raise_executor_errors=False,
            )
            if late_result is not None:
                task_manager.apply_result(late_result)
            return None
        if _workflow_run_is_terminal(store, workflow_run_id):
            _close_executor(executor)
            return None
        if _workflow_cancel_was_requested(
            store=store,
            workflow_process_id=workflow_process_id,
        ):
            if cancel_requested_at is None:
                cancel_requested_at = utc_now()
                _mark_node_cancel_requested(
                    store=store,
                    task=task,
                    executor_id=executor.executor_id,
                )
                _request_cancel(executor, task)
            if _cancel_grace_period_expired(
                cancel_requested_at,
                cancel_grace_seconds=cancel_grace_seconds,
            ):
                _close_executor(executor)
                worker.join(timeout=0.2)
                return _cancelled_task_result(
                    task,
                    executor_id=executor.executor_id,
                    reason="WORKFLOW_CANCEL_GRACE_EXPIRED",
                )


def _get_node_task_execution_result(
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


def _task_supervision_poll_seconds(heartbeat_interval_seconds: float) -> float:
    if heartbeat_interval_seconds <= 0:
        return 0.01
    return min(max(heartbeat_interval_seconds, 0.01), 0.1)


def _workflow_cancel_was_requested(
    *,
    store: RuntimeStore,
    workflow_process_id: str,
) -> bool:
    process = store.get_workflow_process(workflow_process_id)
    return process is not None and process.cancel_requested_at is not None


def _mark_node_cancel_requested(
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


def _cancel_grace_period_expired(
    cancel_requested_at: datetime,
    *,
    cancel_grace_seconds: float,
) -> bool:
    return (
        utc_now() - cancel_requested_at
    ).total_seconds() >= cancel_grace_seconds


def _request_cancel(
    executor: NodeExecutor,
    task: NodeTaskModel,
) -> None:
    if not isinstance(executor, CancellableNodeExecutor):
        return
    try:
        executor.request_cancel(task)
    except Exception:
        pass


def _cancelled_task_result(
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


def _cleanup_staging_for_node(
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


def _timeout_seconds_from_node_config(config: dict[str, object]) -> int:
    value = config.get("timeout_seconds")
    if isinstance(value, bool) or not isinstance(value, int):
        return 60
    return max(0, value)


def _configure_executor_event_handler(
    executor: object,
    *,
    store: RuntimeStore,
    task_manager: NodeTaskManager,
    workflow_process_id: str,
    process_generation: int,
) -> None:
    if not isinstance(executor, _NodeTaskIpcEventAwareExecutor):
        return

    def handle_event(task: NodeTaskModel, envelope: IPCEnvelope) -> None:
        store.record_workflow_process_heartbeat(
            workflow_process_id,
            process_generation=process_generation,
        )
        _record_node_task_ipc_event(
            task_manager=task_manager,
            executor_id=executor.executor_id,
            task=task,
            envelope=envelope,
        )

    executor.set_event_handler(handle_event)


def _record_node_task_ipc_event(
    *,
    task_manager: NodeTaskManager,
    executor_id: str,
    task: NodeTaskModel,
    envelope: IPCEnvelope,
) -> None:
    if envelope.message_type == IPCMessageType.NODE_TASK_HEARTBEAT:
        heartbeat_payload = NodeTaskHeartbeatPayload.model_validate(envelope.payload)
        if heartbeat_payload.task_id != task.task_id:
            return
        task_manager.record_task_heartbeat(
            task,
            executor_id=heartbeat_payload.executor_id,
            attempt=heartbeat_payload.attempt,
        )
        return
    if envelope.message_type == IPCMessageType.NODE_TASK_PROGRESS:
        progress_payload = NodeTaskProgressPayload.model_validate(envelope.payload)
        task_manager.record_task_progress(
            task,
            executor_id=executor_id,
            progress=progress_payload.progress,
            current_stage=progress_payload.current_stage,
            metrics=progress_payload.metrics,
        )


def _close_executor(executor: object) -> None:
    if not isinstance(executor, _ClosableExecutor):
        return
    try:
        executor.close()
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
    return 1


def _exit() -> NoReturn:
    raise SystemExit(main())


if __name__ == "__main__":
    _exit()
