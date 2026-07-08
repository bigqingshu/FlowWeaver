from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import EventType, NodeRunStatus
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.workflow_process.dag import WorkflowDag


def submit_ready_node(
    *,
    store: RuntimeStore,
    event_sink: RuntimeEventSink,
    dag: WorkflowDag,
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
    node = _dag_node(dag, node_instance_id)
    if node is None:
        return None
    if node_run_id is None:
        node_run = store.get_node_run_for_instance(
            workflow_run_id=workflow_run_id,
            node_instance_id=node_instance_id,
        )
    else:
        node_run = store.get_node_run(node_run_id)
        if node_run is not None and (
            node_run.workflow_run_id != workflow_run_id
            or node_run.node_instance_id != node_instance_id
        ):
            return None
    if node_run is None:
        return None
    queued = store.update_node_run_status(
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
    store.create_node_task(task)
    event_sink.emit(
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
    *,
    store: RuntimeStore,
    event_sink: RuntimeEventSink,
    task_id: str,
    executor_id: str,
) -> NodeTaskModel | None:
    task = store.get_node_task(task_id)
    if task is None:
        return None
    node_run = store.get_node_run(task.node_run_id)
    if node_run is None:
        return None
    started_at = utc_now()
    running = store.update_node_run_status(
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
    event_sink.emit(
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


def _dag_node(dag: WorkflowDag, node_instance_id: str):
    for node in dag.nodes:
        if node.node_instance_id == node_instance_id:
            return node
    return None
