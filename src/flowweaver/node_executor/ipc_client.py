from __future__ import annotations

from flowweaver.common.time import utc_now
from flowweaver.node_executor.base import NodeExecutorFactory
from flowweaver.node_executor.process import NodeExecutorProcess
from flowweaver.protocols.enums import IPCMessageType, NodeResultStatus
from flowweaver.protocols.ipc_messages import (
    IPCEnvelope,
    NodeTaskCompletedPayload,
    NodeTaskFailedPayload,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


class LocalNodeExecutorIpcClient:
    def __init__(
        self,
        *,
        executor_id: str = "local-node-executor",
        executor_factory: NodeExecutorFactory | None = None,
    ) -> None:
        self.executor_id = executor_id
        self._process = NodeExecutorProcess(
            executor_id=executor_id,
            executor_factory=executor_factory,
        )

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        envelope = IPCEnvelope(
            message_type=IPCMessageType.NODE_TASK_SUBMIT,
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            payload=task.model_dump(mode="json"),
        )
        for response in self._process.handle_envelope(envelope):
            if response.message_type == IPCMessageType.NODE_TASK_COMPLETED:
                return NodeTaskCompletedPayload.model_validate(
                    response.payload
                ).result
            if response.message_type == IPCMessageType.NODE_TASK_FAILED:
                return NodeTaskFailedPayload.model_validate(response.payload).result
        return _missing_result(task, executor_id=self.executor_id)


def _missing_result(
    task: NodeTaskModel,
    *,
    executor_id: str,
) -> NodeTaskResultModel:
    now = utc_now()
    return NodeTaskResultModel(
        task_id=task.task_id,
        node_run_id=task.node_run_id,
        attempt=task.attempt,
        executor_id=executor_id,
        process_generation=task.process_generation,
        status=NodeResultStatus.FAILED,
        error={"message": "Node executor IPC response did not include a result"},
        started_at=now,
        finished_at=now,
    )
