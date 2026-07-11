from __future__ import annotations

from typing import Any

from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.ipc_messages import (
    ExecutorHeartbeatPayload,
    IPCEnvelope,
    NodeTaskCompletedPayload,
    NodeTaskFailedPayload,
    NodeTaskHeartbeatPayload,
    NodeTaskLogPayload,
    NodeTaskProgressPayload,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.runtime_feedback import RuntimeFeedbackLogLevel


def ready_envelope(executor_id: str) -> IPCEnvelope:
    return IPCEnvelope(
        message_type=IPCMessageType.EXECUTOR_READY,
        payload={"executor_id": executor_id},
    )


def heartbeat_envelope(
    executor_id: str,
    *,
    active_task_ids: list[str],
) -> IPCEnvelope:
    return IPCEnvelope(
        message_type=IPCMessageType.EXECUTOR_HEARTBEAT,
        payload=ExecutorHeartbeatPayload(
            executor_id=executor_id,
            active_task_ids=active_task_ids,
        ).model_dump(mode="json"),
    )


def task_heartbeat_envelope(
    executor_id: str,
    task: NodeTaskModel,
    *,
    correlation_id: str | None,
) -> IPCEnvelope:
    return IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_HEARTBEAT,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        correlation_id=correlation_id,
        payload=NodeTaskHeartbeatPayload(
            executor_id=executor_id,
            task_id=task.task_id,
            attempt=task.attempt,
        ).model_dump(mode="json"),
    )


def task_progress_envelope(
    task: NodeTaskModel,
    *,
    progress: float | None,
    current_stage: str | None,
    metrics: dict[str, int | float | str],
    correlation_id: str | None,
) -> IPCEnvelope:
    return IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_PROGRESS,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        correlation_id=correlation_id,
        payload=NodeTaskProgressPayload(
            progress=progress,
            current_stage=current_stage,
            metrics=metrics,
        ).model_dump(mode="json"),
    )


def task_log_envelope(
    task: NodeTaskModel,
    *,
    level: RuntimeFeedbackLogLevel,
    message: str,
    logger_name: str,
    context: dict[str, Any],
    correlation_id: str | None,
) -> IPCEnvelope:
    return IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_LOG,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        correlation_id=correlation_id,
        payload=NodeTaskLogPayload(
            level=level,
            message=message,
            logger_name=logger_name,
            node_instance_id=task.node_instance_id,
            task_id=task.task_id,
            context=context,
        ).model_dump(mode="json"),
    )


def task_accepted_envelope(
    executor_id: str,
    task: NodeTaskModel,
    *,
    correlation_id: str,
) -> IPCEnvelope:
    return IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_ACCEPTED,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        correlation_id=correlation_id,
        payload={
            "executor_id": executor_id,
            "task_id": task.task_id,
            "node_run_id": task.node_run_id,
        },
    )


def task_failed_envelope(
    task: NodeTaskModel,
    *,
    result: NodeTaskResultModel,
    error_type: str,
    correlation_id: str,
) -> IPCEnvelope:
    return IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_FAILED,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        correlation_id=correlation_id,
        payload=NodeTaskFailedPayload(
            result=result,
            error_type=error_type,
        ).model_dump(mode="json"),
    )


def task_completed_envelope(
    task: NodeTaskModel,
    *,
    result: NodeTaskResultModel,
    correlation_id: str,
) -> IPCEnvelope:
    return IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_COMPLETED,
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        correlation_id=correlation_id,
        payload=NodeTaskCompletedPayload(result=result).model_dump(mode="json"),
    )
