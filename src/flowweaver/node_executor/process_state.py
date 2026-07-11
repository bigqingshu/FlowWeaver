from __future__ import annotations

from collections.abc import Callable, Mapping
from threading import Lock
from typing import Any

from flowweaver.node_executor.cancel_token import CancelToken, NodeExecutionContext
from flowweaver.node_executor.runtime_feedback_gate import (
    NodeTaskRuntimeFeedbackGate,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.runtime_feedback import RuntimeFeedbackLogLevel
from flowweaver.protocols.runtime_logs import sanitize_runtime_log_context


class NodeExecutorProcessState:
    def __init__(
        self,
        *,
        monotonic_time: Callable[[], float] | None = None,
    ) -> None:
        self._active_task_ids: set[str] = set()
        self._active_task_correlations: dict[str, str] = {}
        self._cancel_tokens: dict[str, CancelToken] = {}
        self._execution_contexts: dict[str, NodeExecutionContext] = {}
        self._runtime_feedback_gates: dict[str, NodeTaskRuntimeFeedbackGate] = {}
        self._monotonic_time = monotonic_time
        self._lock = Lock()

    def active_task_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._active_task_ids)

    def begin_task(self, *, task: NodeTaskModel, correlation_id: str) -> None:
        cancel_token = CancelToken()
        feedback_gate = NodeTaskRuntimeFeedbackGate(
            task.runtime_feedback_policy,
            monotonic_time=self._monotonic_time,
        )
        with self._lock:
            self._active_task_ids.add(task.task_id)
            self._active_task_correlations[task.task_id] = correlation_id
            self._cancel_tokens[task.task_id] = cancel_token
            self._execution_contexts[task.task_id] = NodeExecutionContext(cancel_token)
            self._runtime_feedback_gates[task.task_id] = feedback_gate

    def finish_task(self, task_id: str) -> None:
        with self._lock:
            self._active_task_ids.discard(task_id)
            self._active_task_correlations.pop(task_id, None)
            self._cancel_tokens.pop(task_id, None)
            self._execution_contexts.pop(task_id, None)
            self._runtime_feedback_gates.pop(task_id, None)

    def task_correlation_id(self, task_id: str) -> str | None:
        with self._lock:
            return self._active_task_correlations.get(task_id)

    def task_context(self, task_id: str) -> NodeExecutionContext | None:
        with self._lock:
            return self._execution_contexts.get(task_id)

    def prepare_task_progress_metrics(
        self,
        task_id: str,
        metrics: Mapping[str, int | float | str] | None,
    ) -> dict[str, int | float | str] | None:
        with self._lock:
            gate = self._runtime_feedback_gates.get(task_id)
        if gate is None:
            return dict(metrics or {})
        return gate.prepare_progress_metrics(metrics)

    def prepare_task_log_context(
        self,
        task_id: str,
        level: RuntimeFeedbackLogLevel,
        context: Mapping[str, Any] | None,
    ) -> dict[str, Any] | None:
        with self._lock:
            gate = self._runtime_feedback_gates.get(task_id)
        if gate is None:
            return sanitize_runtime_log_context(
                context,
                include_metrics=True,
                payload_byte_limit=0,
                redact_columns=[],
                mask_policy="none",
                capture_error_context=True,
                is_error=level == "ERROR",
            )
        return gate.prepare_log_context(level, context)

    def request_cancel(self, *, task_id: str, reason: str) -> None:
        with self._lock:
            token = self._cancel_tokens.get(task_id)
        if token is not None:
            token.request_cancel(reason=reason)
