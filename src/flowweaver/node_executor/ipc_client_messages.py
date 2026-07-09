from __future__ import annotations

from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.protocols.enums import IPCMessageType, NodeResultStatus
from flowweaver.protocols.ipc_messages import (
    IPCEnvelope,
    NodeTaskCancelRequestPayload,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel

INTERMEDIATE_NODE_TASK_MESSAGES = frozenset(
    {
        IPCMessageType.NODE_TASK_ACCEPTED,
        IPCMessageType.NODE_TASK_HEARTBEAT,
        IPCMessageType.NODE_TASK_PROGRESS,
    }
)


def missing_result(
    task: NodeTaskModel,
    *,
    executor_id: str,
) -> NodeTaskResultModel:
    return ipc_failure_result(
        task,
        executor_id=executor_id,
        error={"message": "Node executor IPC response did not include a result"},
    )


def cancel_request_envelope(
    task: NodeTaskModel,
    *,
    reason: str,
) -> IPCEnvelope:
    return IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_CANCEL_REQUEST,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        payload=NodeTaskCancelRequestPayload(
            task_id=task.task_id,
            reason=reason,
        ).model_dump(mode="json"),
    )


def ipc_failure_result(
    task: NodeTaskModel,
    *,
    executor_id: str,
    error: dict[str, Any],
) -> NodeTaskResultModel:
    now = utc_now()
    return NodeTaskResultModel(
        task_id=task.task_id,
        node_run_id=task.node_run_id,
        attempt=task.attempt,
        executor_id=executor_id,
        process_generation=task.process_generation,
        status=NodeResultStatus.FAILED,
        error=error,
        started_at=now,
        finished_at=now,
    )
