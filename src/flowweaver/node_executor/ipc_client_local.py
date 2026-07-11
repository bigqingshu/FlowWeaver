from __future__ import annotations

from threading import Lock

from flowweaver.node_executor.base import NodeExecutorFactory
from flowweaver.node_executor.ipc_client_messages import (
    INTERMEDIATE_NODE_TASK_MESSAGES,
    cancel_request_envelope,
    missing_result,
    node_task_result_from_response,
    runtime_options_update_envelope,
    submit_task_envelope,
)
from flowweaver.node_executor.ipc_client_types import NodeTaskIpcEventHandler
from flowweaver.node_executor.process import NodeExecutorProcess
from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.ipc_messages import IPCEnvelope
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
)


class LocalNodeExecutorIpcClient:
    def __init__(
        self,
        *,
        executor_id: str = "local-node-executor",
        executor_factory: NodeExecutorFactory | None = None,
        event_handler: NodeTaskIpcEventHandler | None = None,
    ) -> None:
        self.executor_id = executor_id
        self._event_handler = event_handler
        self._active_tasks: dict[str, NodeTaskModel] = {}
        self._active_tasks_lock = Lock()
        self._process = NodeExecutorProcess(
            executor_id=executor_id,
            executor_factory=executor_factory,
            event_writer=self._emit_process_event,
        )

    def set_event_handler(self, handler: NodeTaskIpcEventHandler | None) -> None:
        self._event_handler = handler

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        envelope = submit_task_envelope(task)
        with self._active_tasks_lock:
            self._active_tasks[task.task_id] = task
        try:
            for response in self._process.handle_envelope(envelope):
                if response.message_type in INTERMEDIATE_NODE_TASK_MESSAGES:
                    self._emit_event(task, response)
                    continue
                result = node_task_result_from_response(response)
                if result is not None:
                    return result
            return missing_result(task, executor_id=self.executor_id)
        finally:
            with self._active_tasks_lock:
                self._active_tasks.pop(task.task_id, None)

    def request_cancel(
        self,
        task: NodeTaskModel,
        *,
        reason: str = "WORKFLOW_CANCEL_REQUESTED",
    ) -> bool:
        envelope = cancel_request_envelope(task, reason=reason)
        self._process.handle_envelope(envelope)
        return True

    def request_runtime_options_update(
        self,
        task: NodeTaskModel,
        *,
        runtime_options_version: int,
        runtime_feedback_policy: ResolvedRuntimeFeedbackPolicyModel,
    ) -> bool:
        envelope = runtime_options_update_envelope(
            task,
            runtime_options_version=runtime_options_version,
            runtime_feedback_policy=runtime_feedback_policy,
        )
        responses = self._process.handle_envelope(envelope)
        applied = False
        for response in responses:
            if (
                response.message_type
                != IPCMessageType.NODE_TASK_RUNTIME_OPTIONS_APPLIED
            ):
                continue
            try:
                self._emit_event(task, response)
                applied = True
            finally:
                self._process.mark_runtime_options_response_written(task.task_id)
        return applied

    def _emit_event(self, task: NodeTaskModel, envelope: IPCEnvelope) -> None:
        if self._event_handler is not None:
            self._event_handler(task, envelope)

    def _emit_process_event(self, envelope: IPCEnvelope) -> None:
        task_id = envelope.payload.get("task_id")
        with self._active_tasks_lock:
            task = (
                self._active_tasks.get(task_id)
                if isinstance(task_id, str)
                else next(
                    (
                        candidate
                        for candidate in self._active_tasks.values()
                        if candidate.node_run_id == envelope.node_run_id
                    ),
                    None,
                )
            )
        if task is not None:
            self._emit_event(task, envelope)
