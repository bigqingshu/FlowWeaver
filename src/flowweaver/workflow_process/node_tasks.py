from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.protocols.ipc_messages import NodeTaskLogPayload
from flowweaver.protocols.memory_table_warnings import (
    memory_table_soft_limit_warnings_from_summary,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
)
from flowweaver.workflow.definition import FailurePolicyMode
from flowweaver.workflow.runtime_feedback_policy import (
    RuntimeFeedbackPolicyProvider,
)
from flowweaver.workflow_process.dag import WorkflowDag
from flowweaver.workflow_process.node_task_application import (
    apply_node_task_result_to_runtime as _apply_node_task_result_to_runtime,
)
from flowweaver.workflow_process.node_task_lifecycle import (
    accept_task as _accept_task,
)
from flowweaver.workflow_process.node_task_lifecycle import (
    submit_ready_node as _submit_ready_node,
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
from flowweaver.workflow_process.node_task_telemetry import (
    record_task_heartbeat as _record_task_heartbeat,
)
from flowweaver.workflow_process.node_task_telemetry import (
    record_task_log as _record_task_log,
)
from flowweaver.workflow_process.node_task_telemetry import (
    record_task_progress as _record_task_progress,
)
from flowweaver.workflow_process.node_task_timeout import (
    mark_timed_out_task as _mark_timed_out_task,
)
from flowweaver.workflow_process.runtime_logger import WorkflowRuntimeLogger


class NodeTaskManager:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        event_sink: RuntimeEventSink,
        dag: WorkflowDag,
        failure_policy_mode: FailurePolicyMode | str | None = None,
        runtime_feedback_policy_provider: RuntimeFeedbackPolicyProvider | None = None,
        table_provider_registry: TableProviderRegistry | None = None,
        runtime_logger: WorkflowRuntimeLogger | None = None,
    ) -> None:
        self._store = store
        self._event_sink = event_sink
        self._dag = dag
        self._failure_policy_mode = FailurePolicyMode(
            failure_policy_mode or FailurePolicyMode.FAIL_FAST
        )
        self._runtime_feedback_policy_provider = runtime_feedback_policy_provider
        self._table_provider_registry = table_provider_registry
        self._runtime_logger = runtime_logger
        self._last_progress_emitted_at: dict[str, datetime] = {}
        self._emitted_memory_table_warning_keys: set[tuple[str, str, str]] = set()

    @property
    def failure_policy_mode(self) -> FailurePolicyMode:
        return self._failure_policy_mode

    def runtime_feedback_policy_for_node(
        self,
        node_instance_id: str,
    ) -> ResolvedRuntimeFeedbackPolicyModel | None:
        provider = self._runtime_feedback_policy_provider
        return provider.policy_for_node(node_instance_id) if provider else None

    def runtime_feedback_policy_snapshot_for_node(
        self,
        node_instance_id: str,
    ) -> tuple[int, ResolvedRuntimeFeedbackPolicyModel | None]:
        provider = self._runtime_feedback_policy_provider
        if provider is None:
            return 0, None
        return provider.policy_snapshot_for_node(node_instance_id)

    def runtime_options_version_for_task(self, task_id: str) -> int | None:
        task = self._store.get_node_task(task_id)
        return task.runtime_options_version if task is not None else None

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
        runtime_options_version, runtime_feedback_policy = (
            self.runtime_feedback_policy_snapshot_for_node(node_instance_id)
        )
        return _submit_ready_node(
            store=self._store,
            event_sink=self._event_sink,
            dag=self._dag,
            workflow_run_id=workflow_run_id,
            workflow_process_id=workflow_process_id,
            process_generation=process_generation,
            node_instance_id=node_instance_id,
            node_run_id=node_run_id,
            config=config,
            input_refs=input_refs or [],
            input_slot_bindings=input_slot_bindings,
            runtime_feedback_policy=runtime_feedback_policy,
            runtime_options_version=runtime_options_version,
            timeout_seconds=timeout_seconds,
        )

    def accept_task(
        self,
        *,
        task_id: str,
        executor_id: str,
    ) -> NodeTaskModel | None:
        return _accept_task(
            store=self._store,
            event_sink=self._event_sink,
            task_id=task_id,
            executor_id=executor_id,
        )

    def record_task_heartbeat(
        self,
        task: NodeTaskModel,
        *,
        executor_id: str,
        attempt: int,
    ) -> NodeRun | None:
        return _record_task_heartbeat(
            store=self._store,
            task=task,
            executor_id=executor_id,
            attempt=attempt,
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
        return _record_task_progress(
            store=self._store,
            event_sink=self._event_sink,
            task=task,
            executor_id=executor_id,
            progress=progress,
            current_stage=current_stage,
            metrics=metrics,
            runtime_feedback_policy=self.runtime_feedback_policy_for_node(
                task.node_instance_id
            ),
            last_progress_emitted_at=self._last_progress_emitted_at,
        )

    def record_task_log(
        self,
        task: NodeTaskModel,
        *,
        payload: NodeTaskLogPayload,
    ) -> None:
        _record_task_log(
            event_sink=self._event_sink,
            task=task,
            payload=payload,
        )

    def record_task_runtime_options_applied(
        self,
        task: NodeTaskModel,
        *,
        runtime_options_version: int,
    ) -> bool:
        current_version, current_policy = (
            self.runtime_feedback_policy_snapshot_for_node(
                task.node_instance_id
            )
        )
        if (
            current_policy is None
            or runtime_options_version != current_version
        ):
            return False
        return self._store.update_node_task_runtime_feedback_policy(
            task.task_id,
            runtime_options_version=runtime_options_version,
            runtime_feedback_policy=current_policy,
        )

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
        apply_result = _apply_node_task_result_to_runtime(
            store=self._store,
            event_sink=self._event_sink,
            dag=self._dag,
            failure_policy_mode=self._failure_policy_mode,
            runtime_feedback_policy_provider=self._runtime_feedback_policy_provider,
            table_provider_registry=self._table_provider_registry,
            result=result,
        )
        if apply_result.status == NodeTaskApplyStatus.APPLIED:
            self._emit_memory_table_soft_limit_warnings(result)
        return apply_result

    def _emit_memory_table_soft_limit_warnings(
        self,
        result: NodeTaskResultModel,
    ) -> None:
        logger = self._runtime_logger
        if logger is None:
            return
        task = self._store.get_node_task(result.task_id)
        if task is None:
            return
        output_refs = set(result.output_refs)
        for warning in memory_table_soft_limit_warnings_from_summary(result.summary):
            if warning.table_ref_id not in output_refs:
                continue
            warning_key = (
                task.workflow_run_id,
                warning.warning_code,
                warning.table_ref_id,
            )
            if warning_key in self._emitted_memory_table_warning_keys:
                continue
            try:
                emitted = logger.warn(
                    f"memory table row soft limit exceeded: "
                    f"{warning.logical_table_id}",
                    context={
                        **warning.model_dump(mode="json"),
                        "node_instance_id": task.node_instance_id,
                        "task_id": task.task_id,
                    },
                )
            except Exception:
                continue
            if emitted:
                self._emitted_memory_table_warning_keys.add(warning_key)
