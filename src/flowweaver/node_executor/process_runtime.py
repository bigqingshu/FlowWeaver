from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flowweaver.node_executor.base import NodeExecutorFactory
from flowweaver.node_executor.builtin_fault import (
    BUILTIN_FAULT_NODE_TYPES,
    BuiltinFaultNodeExecutor,
)
from flowweaver.node_executor.cancel_token import NodeExecutionContext
from flowweaver.node_executor.fake import FakeNodeExecutor
from flowweaver.node_executor.process_envelopes import (
    heartbeat_envelope as _heartbeat_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    ready_envelope as _ready_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    task_accepted_envelope as _task_accepted_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    task_completed_envelope as _task_completed_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    task_failed_envelope as _task_failed_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    task_heartbeat_envelope as _task_heartbeat_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    task_log_envelope as _task_log_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    task_progress_envelope as _task_progress_envelope,
)
from flowweaver.node_executor.process_envelopes import (
    task_runtime_options_applied_envelope as _task_runtime_options_applied_envelope,
)
from flowweaver.node_executor.process_helpers import (
    failed_task_result as _failed_task_result,
)
from flowweaver.node_executor.process_state import NodeExecutorProcessState
from flowweaver.node_executor.runtime_logger import (
    NodeTaskLogger,
    NodeTaskRuntimeLoggerAware,
)
from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.ipc_messages import (
    IPCEnvelope,
    NodeTaskCancelRequestPayload,
    NodeTaskRuntimeOptionsUpdatePayload,
    NodeTaskSubmitPayload,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.runtime_feedback import RuntimeFeedbackLogLevel


class NodeExecutorProcess:
    def __init__(
        self,
        *,
        executor_id: str,
        executor_factory: NodeExecutorFactory | None = None,
        event_writer: Callable[[IPCEnvelope], None] | None = None,
        monotonic_time: Callable[[], float] | None = None,
    ) -> None:
        self.executor_id = executor_id
        self._executor_factory = executor_factory
        self._event_writer = event_writer
        self._state = NodeExecutorProcessState(monotonic_time=monotonic_time)
        self._pending_task_events: list[IPCEnvelope] = []

    def ready_envelope(self) -> IPCEnvelope:
        return _ready_envelope(self.executor_id)

    def heartbeat_envelope(self) -> IPCEnvelope:
        return _heartbeat_envelope(
            self.executor_id,
            active_task_ids=self._state.active_task_ids(),
        )

    def task_heartbeat_envelope(
        self,
        task: NodeTaskModel,
        *,
        correlation_id: str | None = None,
    ) -> IPCEnvelope:
        return _task_heartbeat_envelope(
            self.executor_id,
            task,
            correlation_id=correlation_id
            or self._state.task_correlation_id(task.task_id),
        )

    def task_progress_envelope(
        self,
        task: NodeTaskModel,
        *,
        progress: float | None,
        current_stage: str | None = None,
        metrics: dict[str, int | float | str] | None = None,
        correlation_id: str | None = None,
    ) -> IPCEnvelope | None:
        filtered_metrics = self._state.prepare_task_progress_metrics(
            task.task_id,
            metrics,
        )
        if filtered_metrics is None:
            return None
        return _task_progress_envelope(
            task,
            progress=progress,
            current_stage=current_stage,
            metrics=filtered_metrics,
            correlation_id=correlation_id
            or self._state.task_correlation_id(task.task_id),
        )

    def task_log_envelope(
        self,
        task: NodeTaskModel,
        *,
        level: RuntimeFeedbackLogLevel,
        message: str,
        logger_name: str,
        context: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> IPCEnvelope | None:
        filtered_context = self._state.prepare_task_log_context(
            task.task_id,
            level,
            context,
        )
        if filtered_context is None:
            return None
        return _task_log_envelope(
            task,
            level=level,
            message=message,
            logger_name=logger_name,
            context=filtered_context,
            correlation_id=correlation_id
            or self._state.task_correlation_id(task.task_id),
        )

    def emit_task_heartbeat(
        self,
        task: NodeTaskModel,
        *,
        correlation_id: str | None = None,
    ) -> None:
        self._emit_or_queue_task_event(
            self.task_heartbeat_envelope(task, correlation_id=correlation_id)
        )

    def emit_task_progress(
        self,
        task: NodeTaskModel,
        *,
        progress: float | None,
        current_stage: str | None = None,
        metrics: dict[str, int | float | str] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        envelope = self.task_progress_envelope(
            task,
            progress=progress,
            current_stage=current_stage,
            metrics=metrics,
            correlation_id=correlation_id,
        )
        if envelope is not None:
            self._emit_or_queue_task_event(envelope)

    def emit_task_log(
        self,
        task: NodeTaskModel,
        level: RuntimeFeedbackLogLevel,
        message: str,
        logger_name: str,
        context: dict[str, Any],
    ) -> bool:
        envelope = self.task_log_envelope(
            task,
            level=level,
            message=message,
            logger_name=logger_name,
            context=context,
        )
        if envelope is None:
            return False
        self._emit_or_queue_task_event(envelope)
        return True

    def task_logger(
        self,
        task: NodeTaskModel,
        *,
        logger_name: str,
    ) -> NodeTaskLogger:
        return NodeTaskLogger(
            task=task,
            logger_name=logger_name,
            emit_log=self.emit_task_log,
        )

    def handle_envelope(self, envelope: IPCEnvelope) -> tuple[IPCEnvelope, ...]:
        if envelope.message_type == IPCMessageType.NODE_TASK_RUNTIME_OPTIONS_UPDATE:
            return self._handle_runtime_options_update(envelope)
        if envelope.message_type == IPCMessageType.NODE_TASK_CANCEL_REQUEST:
            return self._handle_cancel_request(envelope)
        if envelope.message_type != IPCMessageType.NODE_TASK_SUBMIT:
            return ()
        task = NodeTaskSubmitPayload.model_validate(envelope.payload)
        executor = self._executor_for_task(task)
        self._state.begin_task(
            task=task,
            correlation_id=envelope.message_id,
        )
        self._pending_task_events = []
        accepted = _task_accepted_envelope(
            self.executor_id,
            task,
            correlation_id=envelope.message_id,
        )
        accepted_events = self._emit_or_return(accepted)
        try:
            self._bind_runtime_logger(executor, task)
            result = executor.execute(task)
            task_events = tuple(self._pending_task_events)
        except Exception as exc:
            task_events = tuple(self._pending_task_events)
            failed = _task_failed_envelope(
                task,
                result=_failed_task_result(
                    task,
                    executor_id=self.executor_id,
                    error=exc,
                ),
                error_type=type(exc).__name__,
                correlation_id=envelope.message_id,
            )
            return (*accepted_events, *task_events, failed)
        finally:
            self._clear_runtime_logger(executor)
            self._state.finish_task(task.task_id)
            self._pending_task_events = []
        completed = _task_completed_envelope(
            task,
            result=result,
            correlation_id=envelope.message_id,
        )
        return (*accepted_events, *task_events, completed)

    def task_is_cancelled(self, task: NodeTaskModel) -> bool:
        context = self.task_context(task)
        return context is not None and context.is_cancelled()

    def task_context(self, task: NodeTaskModel) -> NodeExecutionContext | None:
        return self._state.task_context(task.task_id)

    def mark_runtime_options_response_written(self, task_id: str) -> None:
        self._state.mark_runtime_options_response_written(task_id)

    def _handle_runtime_options_update(
        self,
        envelope: IPCEnvelope,
    ) -> tuple[IPCEnvelope, ...]:
        payload = NodeTaskRuntimeOptionsUpdatePayload.model_validate(envelope.payload)
        applied_version = self._state.apply_task_runtime_feedback_policy(
            payload.task_id,
            runtime_options_version=payload.runtime_options_version,
            runtime_feedback_policy=payload.runtime_feedback_policy,
        )
        if applied_version is None:
            return ()
        return (
            _task_runtime_options_applied_envelope(
                workflow_run_id=envelope.workflow_run_id,
                node_run_id=envelope.node_run_id,
                task_id=payload.task_id,
                runtime_options_version=applied_version,
                correlation_id=envelope.message_id,
            ),
        )

    def _handle_cancel_request(
        self,
        envelope: IPCEnvelope,
    ) -> tuple[IPCEnvelope, ...]:
        payload = NodeTaskCancelRequestPayload.model_validate(envelope.payload)
        self._state.request_cancel(task_id=payload.task_id, reason=payload.reason)
        return ()

    def _emit_or_queue_task_event(self, envelope: IPCEnvelope) -> None:
        if self._event_writer is not None:
            self._event_writer(envelope)
            return
        self._pending_task_events.append(envelope)

    def _emit_or_return(self, envelope: IPCEnvelope) -> tuple[IPCEnvelope, ...]:
        if self._event_writer is not None:
            self._event_writer(envelope)
            return ()
        return (envelope,)

    def _executor_for_task(self, task: NodeTaskModel):
        if self._executor_factory is not None:
            return self._executor_factory(task)
        if task.node_type in BUILTIN_FAULT_NODE_TYPES:
            return BuiltinFaultNodeExecutor(
                executor_id=self.executor_id,
                event_emitter=self,
            )
        return FakeNodeExecutor(executor_id=self.executor_id)

    def _bind_runtime_logger(self, executor: object, task: NodeTaskModel) -> None:
        if not isinstance(executor, NodeTaskRuntimeLoggerAware):
            return
        executor.set_runtime_logger(
            self.task_logger(
                task,
                logger_name=f"flowweaver.nodes.{task.node_type}",
            )
        )

    @staticmethod
    def _clear_runtime_logger(executor: object) -> None:
        if not isinstance(executor, NodeTaskRuntimeLoggerAware):
            return
        try:
            executor.set_runtime_logger(None)
        except Exception:
            pass
