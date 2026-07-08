from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.protocols.enums import (
    EventType,
    NodeResultStatus,
    NodeRunStatus,
    WorkflowRunStatus,
)
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow.definition import (
    FailurePolicyMode,
    RuntimeOptionsWorkflowModel,
)
from flowweaver.workflow.runtime_options import (
    sanitize_node_task_result_for_runtime_options,
)
from flowweaver.workflow_process.control_signal_interpreter import (
    interpret_control_outputs_after_node_success,
)
from flowweaver.workflow_process.controller import advance_after_node_success
from flowweaver.workflow_process.dag import WorkflowDag
from flowweaver.workflow_process.failure_policy_propagation import (
    mark_blocked_descendants_skipped,
)
from flowweaver.workflow_process.loop_iteration_nodes import (
    ensure_loop_iteration_entry_node_run,
)
from flowweaver.workflow_process.loop_iteration_scheduling import (
    advance_loop_iteration_after_node_success,
)
from flowweaver.workflow_process.loop_terminal_state import (
    close_loop_after_node_terminal_result,
)
from flowweaver.workflow_process.node_task_results import (
    NodeTaskApplyResult as NodeTaskApplyResult,
)
from flowweaver.workflow_process.node_task_results import (
    NodeTaskApplyStatus as NodeTaskApplyStatus,
)
from flowweaver.workflow_process.node_task_results import (
    NodeTaskTimeoutResult as NodeTaskTimeoutResult,
)
from flowweaver.workflow_process.node_task_results import (
    NodeTaskTimeoutStatus as NodeTaskTimeoutStatus,
)
from flowweaver.workflow_process.node_task_timeout import (
    mark_timed_out_task as _mark_timed_out_task,
)


class NodeTaskManager:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        event_sink: RuntimeEventSink,
        dag: WorkflowDag,
        failure_policy_mode: FailurePolicyMode | str | None = None,
        runtime_options_by_node: dict[str, RuntimeOptionsWorkflowModel] | None = None,
        table_provider_registry: TableProviderRegistry | None = None,
    ) -> None:
        self._store = store
        self._event_sink = event_sink
        self._dag = dag
        self._failure_policy_mode = FailurePolicyMode(
            failure_policy_mode or FailurePolicyMode.FAIL_FAST
        )
        self._runtime_options_by_node = dict(runtime_options_by_node or {})
        self._table_provider_registry = table_provider_registry
        self._last_progress_emitted_at: dict[str, datetime] = {}

    @property
    def failure_policy_mode(self) -> FailurePolicyMode:
        return self._failure_policy_mode

    def runtime_options_for_node(
        self,
        node_instance_id: str,
    ) -> RuntimeOptionsWorkflowModel | None:
        return self._runtime_options_by_node.get(node_instance_id)

    def submit_ready_node(
        self,
        *,
        workflow_run_id: str,
        workflow_process_id: str,
        process_generation: int,
        node_instance_id: str,
        node_run_id: str | None = None,
        config: dict[str, Any] | None = None,
        input_refs: list[str] | None = None,
        input_slot_bindings: Mapping[str, str] | None = None,
        timeout_seconds: int = 60,
    ) -> NodeTaskModel | None:
        node = self._dag_node(node_instance_id)
        if node is None:
            return None
        if node_run_id is None:
            node_run = self._store.get_node_run_for_instance(
                workflow_run_id=workflow_run_id,
                node_instance_id=node_instance_id,
            )
        else:
            node_run = self._store.get_node_run(node_run_id)
            if node_run is not None and (
                node_run.workflow_run_id != workflow_run_id
                or node_run.node_instance_id != node_instance_id
            ):
                return None
        if node_run is None:
            return None
        queued = self._store.update_node_run_status(
            node_run.node_run_id,
            NodeRunStatus.QUEUED,
            expected_state_version=node_run.state_version,
            allowed_source_statuses=[NodeRunStatus.READY],
            owner_process_id=workflow_process_id,
            process_generation=process_generation,
        )
        if queued is None:
            return None
        task = NodeTaskModel(
            workflow_run_id=workflow_run_id,
            workflow_process_id=workflow_process_id,
            process_generation=process_generation,
            node_run_id=queued.node_run_id,
            node_instance_id=node.node_instance_id,
            node_type=node.node_type,
            node_version=node.node_version,
            attempt=queued.attempt,
            input_refs=input_refs or [],
            input_slot_bindings=dict(input_slot_bindings or {}),
            config=node.config if config is None else config,
            timeout_seconds=timeout_seconds,
        )
        self._store.create_node_task(task)
        self._event_sink.emit(
            EventModel(
                event_type=EventType.NODE_QUEUED,
                workflow_run_id=workflow_run_id,
                node_run_id=queued.node_run_id,
                payload={
                    "process_id": workflow_process_id,
                    "task_id": task.task_id,
                    "node_instance_id": node_instance_id,
                },
            )
        )
        return task

    def accept_task(
        self,
        *,
        task_id: str,
        executor_id: str,
    ) -> NodeTaskModel | None:
        task = self._store.get_node_task(task_id)
        if task is None:
            return None
        node_run = self._store.get_node_run(task.node_run_id)
        if node_run is None:
            return None
        started_at = utc_now()
        running = self._store.update_node_run_status(
            node_run.node_run_id,
            NodeRunStatus.RUNNING,
            executor_id=executor_id,
            started_at=started_at,
            expected_state_version=node_run.state_version,
            allowed_source_statuses=[NodeRunStatus.QUEUED],
            owner_process_id=task.workflow_process_id,
            process_generation=task.process_generation,
        )
        if running is None:
            return None
        self._event_sink.emit(
            EventModel(
                event_type=EventType.NODE_STARTED,
                workflow_run_id=task.workflow_run_id,
                node_run_id=running.node_run_id,
                payload={
                    "process_id": task.workflow_process_id,
                    "task_id": task.task_id,
                    "executor_id": executor_id,
                    "node_instance_id": task.node_instance_id,
                },
            )
        )
        return task

    def record_task_heartbeat(
        self,
        task: NodeTaskModel,
        *,
        executor_id: str,
        attempt: int,
    ) -> NodeRun | None:
        if attempt != task.attempt:
            return None
        return self._store.update_node_task_runtime_state(
            task,
            executor_id=executor_id,
        )

    def record_task_progress(
        self,
        task: NodeTaskModel,
        *,
        executor_id: str,
        progress: float | None,
        current_stage: str | None,
        metrics: dict[str, int | float | str] | None = None,
    ) -> NodeRun | None:
        runtime_options = self.runtime_options_for_node(task.node_instance_id)
        if (
            runtime_options is not None
            and not runtime_options.telemetry.progress_enabled
        ):
            return self._store.update_node_task_runtime_state(
                task,
                executor_id=executor_id,
            )
        now = utc_now()
        if (
            runtime_options is not None
            and runtime_options.telemetry.progress_interval_seconds > 0
        ):
            previous_progress_at = self._last_progress_emitted_at.get(task.task_id)
            if (
                previous_progress_at is not None
                and now - previous_progress_at
                < timedelta(
                    seconds=runtime_options.telemetry.progress_interval_seconds
                )
            ):
                return self._store.update_node_task_runtime_state(
                    task,
                    executor_id=executor_id,
                    heartbeat_at=now,
                )
        updated = self._store.update_node_task_runtime_state(
            task,
            executor_id=executor_id,
            heartbeat_at=now,
            progress=progress,
            current_stage=current_stage,
        )
        if updated is None:
            return None
        self._last_progress_emitted_at[task.task_id] = now
        self._event_sink.emit(
            EventModel(
                event_type=EventType.NODE_PROGRESS,
                workflow_run_id=task.workflow_run_id,
                node_run_id=task.node_run_id,
                payload={
                    "process_id": task.workflow_process_id,
                    "task_id": task.task_id,
                    "executor_id": executor_id,
                    "node_instance_id": task.node_instance_id,
                    "progress": progress,
                    "current_stage": current_stage,
                    "metrics": metrics or {},
                },
            )
        )
        return updated

    def mark_timed_out_task(
        self,
        task: NodeTaskModel,
        *,
        now: datetime | None = None,
    ) -> NodeTaskTimeoutResult:
        return _mark_timed_out_task(
            store=self._store,
            event_sink=self._event_sink,
            task=task,
            now=now,
        )

    def apply_result(self, result: NodeTaskResultModel) -> NodeTaskApplyResult:
        existing_result = self._store.get_node_task_result(
            task_id=result.task_id,
            result_id=result.result_id,
        )
        if existing_result is not None:
            return NodeTaskApplyResult(
                NodeTaskApplyStatus.ALREADY_APPLIED,
                node_run_id=existing_result.node_run_id,
            )
        task = self._store.get_node_task(result.task_id)
        if task is None or task.node_run_id != result.node_run_id:
            return NodeTaskApplyResult(NodeTaskApplyStatus.REJECTED_INVALID_TASK)
        node_run = self._store.get_node_run(result.node_run_id)
        if node_run is None:
            return NodeTaskApplyResult(NodeTaskApplyStatus.REJECTED_INVALID_TASK)
        if result.process_generation != task.process_generation:
            return NodeTaskApplyResult(
                NodeTaskApplyStatus.REJECTED_STALE_GENERATION,
                node_run_id=result.node_run_id,
            )
        if result.attempt != task.attempt or result.attempt != node_run.attempt:
            return NodeTaskApplyResult(
                NodeTaskApplyStatus.REJECTED_STALE_ATTEMPT,
                node_run_id=result.node_run_id,
            )
        if node_run.executor_id != result.executor_id:
            return NodeTaskApplyResult(
                NodeTaskApplyStatus.REJECTED_EXECUTOR_MISMATCH,
                node_run_id=result.node_run_id,
            )
        if node_run.status not in {
            NodeRunStatus.RUNNING.value,
            NodeRunStatus.LONG_RUNNING.value,
            NodeRunStatus.CANCEL_REQUESTED.value,
        }:
            return NodeTaskApplyResult(
                NodeTaskApplyStatus.REJECTED_NODE_TERMINAL,
                node_run_id=result.node_run_id,
            )
        result = sanitize_node_task_result_for_runtime_options(
            result,
            self.runtime_options_for_node(task.node_instance_id),
        )
        if result.status == NodeResultStatus.SUCCEEDED:
            return self._apply_success(task, result, node_run)
        return self._apply_terminal_failure(task, result, node_run)

    def _apply_success(
        self,
        task: NodeTaskModel,
        result: NodeTaskResultModel,
        node_run: NodeRun,
    ) -> NodeTaskApplyResult:
        updated = self._store.record_node_task_result_and_update_node_run_status(
            result,
            NodeRunStatus.SUCCEEDED,
            finished_at=result.finished_at,
            expected_state_version=node_run.state_version,
            allowed_source_statuses=[
                NodeRunStatus.RUNNING,
                NodeRunStatus.LONG_RUNNING,
            ],
            owner_process_id=task.workflow_process_id,
            process_generation=task.process_generation,
        )
        if updated is None:
            return self._result_already_applied_or_terminal(result)
        if self._table_provider_registry is not None:
            control_result = interpret_control_outputs_after_node_success(
                self._store,
                self._table_provider_registry,
                workflow_run_id=task.workflow_run_id,
                completed_node=updated,
                output_refs=result.output_refs,
            )
            if (
                control_result.advance_result is not None
                and control_result.advance_result.next_iteration is not None
            ):
                ensure_loop_iteration_entry_node_run(
                    self._store,
                    dag=self._dag,
                    loop_iteration_id=(
                        control_result.advance_result.next_iteration.loop_iteration_id
                    ),
                    owner_process_id=task.workflow_process_id,
                    process_generation=task.process_generation,
                )
        advance_loop_iteration_after_node_success(
            self._store,
            dag=self._dag,
            completed_node=updated,
            owner_process_id=task.workflow_process_id,
            process_generation=task.process_generation,
        )
        advance_after_node_success(
            self._store,
            workflow_run_id=task.workflow_run_id,
            process_id=task.workflow_process_id,
            process_generation=task.process_generation,
            dag=self._dag,
            completed_node=updated,
            event_sink=self._event_sink,
        )
        return NodeTaskApplyResult(
            NodeTaskApplyStatus.APPLIED,
            node_run_id=result.node_run_id,
        )

    def _apply_terminal_failure(
        self,
        task: NodeTaskModel,
        result: NodeTaskResultModel,
        node_run: NodeRun,
    ) -> NodeTaskApplyResult:
        node_status = (
            NodeRunStatus.CANCELLED
            if result.status == NodeResultStatus.CANCELLED
            else NodeRunStatus.FAILED
        )
        workflow_status = (
            WorkflowRunStatus.CANCELLED
            if result.status == NodeResultStatus.CANCELLED
            else WorkflowRunStatus.FAILED
        )
        updated = self._store.record_node_task_result_and_update_node_run_status(
            result,
            node_status,
            finished_at=result.finished_at,
            error=result.error,
            expected_state_version=node_run.state_version,
            allowed_source_statuses=[
                NodeRunStatus.RUNNING,
                NodeRunStatus.LONG_RUNNING,
                NodeRunStatus.CANCEL_REQUESTED,
            ],
            owner_process_id=task.workflow_process_id,
            process_generation=task.process_generation,
        )
        if updated is None:
            return self._result_already_applied_or_terminal(result)
        close_loop_after_node_terminal_result(
            self._store,
            node_run_id=updated.node_run_id,
            result_status=result.status,
            error=result.error,
            finished_at=result.finished_at,
        )
        if (
            result.status == NodeResultStatus.FAILED
            and self._failure_policy_mode == FailurePolicyMode.CONTINUE_INDEPENDENT
        ):
            mark_blocked_descendants_skipped(
                store=self._store,
                dag=self._dag,
                workflow_run_id=task.workflow_run_id,
                process_id=task.workflow_process_id,
                process_generation=task.process_generation,
                failed_node=updated,
                finished_at=result.finished_at,
            )
            self._event_sink.emit(
                EventModel(
                    event_type=EventType.NODE_FAILED,
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=result.node_run_id,
                    payload={
                        "process_id": task.workflow_process_id,
                        "task_id": task.task_id,
                        "executor_id": result.executor_id,
                        "status": result.status.value,
                    },
                )
            )
            return NodeTaskApplyResult(
                NodeTaskApplyStatus.APPLIED,
                node_run_id=result.node_run_id,
            )
        updated_workflow = self._store.update_workflow_run_status(
            task.workflow_run_id,
            workflow_status,
            finished_at=utc_now(),
            error=result.error,
            allowed_source_statuses=[WorkflowRunStatus.RUNNING],
            owner_process_id=task.workflow_process_id,
            process_generation=task.process_generation,
        )
        self._event_sink.emit(
            EventModel(
                event_type=(
                    EventType.WORKFLOW_CANCELLED
                    if workflow_status == WorkflowRunStatus.CANCELLED
                    else EventType.NODE_FAILED
                ),
                workflow_run_id=task.workflow_run_id,
                node_run_id=result.node_run_id,
                payload={
                    "process_id": task.workflow_process_id,
                    "task_id": task.task_id,
                    "executor_id": result.executor_id,
                    "status": result.status.value,
                },
            )
        )
        if workflow_status == WorkflowRunStatus.FAILED and updated_workflow is not None:
            self._event_sink.emit(
                EventModel(
                    event_type=EventType.WORKFLOW_FAILED,
                    workflow_run_id=task.workflow_run_id,
                    payload={
                        "process_id": task.workflow_process_id,
                        "task_id": task.task_id,
                    },
                )
            )
        return NodeTaskApplyResult(
            NodeTaskApplyStatus.APPLIED,
            node_run_id=result.node_run_id,
        )

    def _result_already_applied_or_terminal(
        self,
        result: NodeTaskResultModel,
    ) -> NodeTaskApplyResult:
        existing_result = self._store.get_node_task_result(
            task_id=result.task_id,
            result_id=result.result_id,
        )
        if existing_result is not None:
            return NodeTaskApplyResult(
                NodeTaskApplyStatus.ALREADY_APPLIED,
                node_run_id=existing_result.node_run_id,
            )
        return NodeTaskApplyResult(
            NodeTaskApplyStatus.REJECTED_NODE_TERMINAL,
            node_run_id=result.node_run_id,
        )

    def _dag_node(self, node_instance_id: str):
        for node in self._dag.nodes:
            if node.node_instance_id == node_instance_id:
                return node
        return None
