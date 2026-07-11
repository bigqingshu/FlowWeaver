from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.node_executor.base import RuntimeOptionsUpdatableNodeExecutor
from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.ipc_messages import (
    IPCEnvelope,
    NodeTaskHeartbeatPayload,
    NodeTaskLogPayload,
    NodeTaskProgressPayload,
    NodeTaskRuntimeOptionsAppliedPayload,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.workflow_process.executor_pool import NodeTaskExecutionPool
from flowweaver.workflow_process.node_tasks import NodeTaskManager


@runtime_checkable
class NodeTaskIpcEventAwareExecutor(Protocol):
    executor_id: str

    def set_event_handler(
        self,
        handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None,
    ) -> None:
        ...


def configure_executor_event_handler(
    executor: object,
    *,
    store: RuntimeStore,
    task_manager: NodeTaskManager,
    workflow_process_id: str,
    process_generation: int,
) -> None:
    if not isinstance(executor, NodeTaskIpcEventAwareExecutor):
        return

    def handle_event(task: NodeTaskModel, envelope: IPCEnvelope) -> None:
        store.record_workflow_process_heartbeat(
            workflow_process_id,
            process_generation=process_generation,
        )
        record_node_task_ipc_event(
            task_manager=task_manager,
            executor_id=executor.executor_id,
            task=task,
            envelope=envelope,
        )

    executor.set_event_handler(handle_event)


def record_node_task_ipc_event(
    *,
    task_manager: NodeTaskManager,
    executor_id: str,
    task: NodeTaskModel,
    envelope: IPCEnvelope,
) -> None:
    if envelope.message_type == IPCMessageType.NODE_TASK_HEARTBEAT:
        heartbeat_payload = NodeTaskHeartbeatPayload.model_validate(envelope.payload)
        if heartbeat_payload.task_id != task.task_id:
            return
        task_manager.record_task_heartbeat(
            task,
            executor_id=heartbeat_payload.executor_id,
            attempt=heartbeat_payload.attempt,
        )
        return
    if envelope.message_type == IPCMessageType.NODE_TASK_PROGRESS:
        progress_payload = NodeTaskProgressPayload.model_validate(envelope.payload)
        task_manager.record_task_progress(
            task,
            executor_id=executor_id,
            progress=progress_payload.progress,
            current_stage=progress_payload.current_stage,
            metrics=progress_payload.metrics,
        )
        return
    if envelope.message_type == IPCMessageType.NODE_TASK_RUNTIME_OPTIONS_APPLIED:
        applied_payload = NodeTaskRuntimeOptionsAppliedPayload.model_validate(
            envelope.payload
        )
        if applied_payload.task_id != task.task_id:
            return
        task_manager.record_task_runtime_options_applied(
            task,
            runtime_options_version=applied_payload.runtime_options_version,
        )
        return
    if envelope.message_type == IPCMessageType.NODE_TASK_LOG:
        log_payload = NodeTaskLogPayload.model_validate(envelope.payload)
        if (
            log_payload.task_id != task.task_id
            or log_payload.node_instance_id != task.node_instance_id
        ):
            return
        task_manager.record_task_log(task, payload=log_payload)


def push_runtime_options_to_in_flight_tasks(
    *,
    execution_pool: NodeTaskExecutionPool,
    task_manager: NodeTaskManager,
) -> int:
    updated_count = 0
    for dispatched_task in execution_pool.in_flight_tasks():
        executor = dispatched_task.executor
        if not isinstance(executor, RuntimeOptionsUpdatableNodeExecutor):
            continue
        version, policy = task_manager.runtime_feedback_policy_snapshot_for_node(
            dispatched_task.node_instance_id
        )
        if policy is None or dispatched_task.task.runtime_options_version >= version:
            continue
        try:
            requested = executor.request_runtime_options_update(
                dispatched_task.task,
                runtime_options_version=version,
                runtime_feedback_policy=policy,
            )
        except Exception:
            requested = False
        if requested:
            updated_count += 1
    return updated_count
