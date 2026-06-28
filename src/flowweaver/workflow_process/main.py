from __future__ import annotations

import argparse
import time
import traceback
from collections.abc import Callable
from typing import NoReturn, Protocol, runtime_checkable

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import (
    DatabaseEventSink,
    IPCEventSink,
    RuntimeEventSink,
)
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.node_executor import (
    NodeExecutorFactory,
    SubprocessNodeExecutorIpcClient,
)
from flowweaver.protocols.enums import EventType, NodeRunStatus, WorkflowRunStatus
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.controller import (
    initialize_node_runs,
    recover_ready_nodes,
)
from flowweaver.workflow_process.dag import build_workflow_dag
from flowweaver.workflow_process.node_tasks import (
    NodeTaskApplyResult,
    NodeTaskApplyStatus,
    NodeTaskManager,
)

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


@runtime_checkable
class _ClosableExecutor(Protocol):
    def close(self) -> None:
        ...


class _ReusableSubprocessExecutorOwner:
    def __init__(self) -> None:
        self._executor: SubprocessNodeExecutorIpcClient | None = None

    def executor_for_task(
        self,
        _task: NodeTaskModel,
    ) -> SubprocessNodeExecutorIpcClient:
        if self._executor is None:
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
            close_executor_after_task=close_executor_after_task,
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
    close_executor_after_task: bool,
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
            task_manager=task_manager,
            executor_factory=executor_factory,
            close_executor_after_task=close_executor_after_task,
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
    task_manager: NodeTaskManager,
    executor_factory: NodeExecutorFactory,
    close_executor_after_task: bool,
    event_sink: RuntimeEventSink,
) -> int:
    if process_generation is None:
        return 0
    dispatched_count = 0
    ready_nodes = [
        node_run
        for node_run in store.list_node_runs(workflow_run_id)
        if node_run.status == NodeRunStatus.READY.value
    ]
    for node_run in ready_nodes:
        task = task_manager.submit_ready_node(
            workflow_run_id=workflow_run_id,
            workflow_process_id=workflow_process_id,
            process_generation=process_generation,
            node_instance_id=node_run.node_instance_id,
        )
        if task is None:
            continue
        executor = executor_factory(task)
        try:
            accepted = task_manager.accept_task(
                task_id=task.task_id,
                executor_id=executor.executor_id,
            )
            if accepted is None:
                continue
            result = executor.execute(accepted)
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
                    task=accepted,
                    result=result,
                    apply_result=apply_result,
                )
            dispatched_count += 1
            if _workflow_run_is_terminal(store, workflow_run_id):
                break
        finally:
            if close_executor_after_task:
                _close_executor(executor)
    return dispatched_count


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
