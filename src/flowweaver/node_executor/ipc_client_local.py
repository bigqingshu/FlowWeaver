from __future__ import annotations

from flowweaver.node_executor.base import NodeExecutorFactory
from flowweaver.node_executor.ipc_client_messages import (
    INTERMEDIATE_NODE_TASK_MESSAGES,
    cancel_request_envelope,
    missing_result,
    node_task_result_from_response,
    submit_task_envelope,
)
from flowweaver.node_executor.ipc_client_types import NodeTaskIpcEventHandler
from flowweaver.node_executor.process import NodeExecutorProcess
from flowweaver.protocols.ipc_messages import IPCEnvelope
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


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
        self._process = NodeExecutorProcess(
            executor_id=executor_id,
            executor_factory=executor_factory,
        )

    def set_event_handler(self, handler: NodeTaskIpcEventHandler | None) -> None:
        self._event_handler = handler

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        envelope = submit_task_envelope(task)
        for response in self._process.handle_envelope(envelope):
            if response.message_type in INTERMEDIATE_NODE_TASK_MESSAGES:
                self._emit_event(task, response)
                continue
            result = node_task_result_from_response(response)
            if result is not None:
                return result
        return missing_result(task, executor_id=self.executor_id)

    def request_cancel(
        self,
        task: NodeTaskModel,
        *,
        reason: str = "WORKFLOW_CANCEL_REQUESTED",
    ) -> bool:
        envelope = cancel_request_envelope(task, reason=reason)
        self._process.handle_envelope(envelope)
        return True

    def _emit_event(self, task: NodeTaskModel, envelope: IPCEnvelope) -> None:
        if self._event_handler is not None:
            self._event_handler(task, envelope)
