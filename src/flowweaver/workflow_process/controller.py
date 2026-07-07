from __future__ import annotations

from dataclasses import dataclass

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import NodeRun, RuntimeStore, WorkflowRun
from flowweaver.protocols.enums import (
    EventType,
    LoopRunStatus,
    NodeRunStatus,
    WorkflowRunStatus,
)
from flowweaver.protocols.events import EventModel
from flowweaver.workflow_process.dag import (
    DagNode,
    WorkflowDag,
    loop_exit_dependencies_for_node,
)

_LOOP_EXIT_READY_STATUSES = frozenset(
    {
        LoopRunStatus.ENDED.value,
        LoopRunStatus.MAX_ITERATIONS_REACHED.value,
    }
)


@dataclass(frozen=True)
class NodeAdvanceResult:
    completed_node: NodeRun | None
    newly_ready_nodes: tuple[NodeRun, ...]
    workflow_completed: WorkflowRun | None


def initialize_node_runs(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None = None,
    dag: WorkflowDag,
) -> tuple[NodeRun, ...]:
    initialized: list[NodeRun] = []
    ready_node_ids = set(dag.ready_node_ids)
    for node in dag.nodes:
        existing = store.get_node_run_for_instance(
            workflow_run_id=workflow_run_id,
            node_instance_id=node.node_instance_id,
        )
        if existing is not None:
            initialized.append(existing)
            continue
        status = (
            NodeRunStatus.READY
            if node.node_instance_id in ready_node_ids
            else NodeRunStatus.WAITING_DEPENDENCY
        )
        node_run = store.create_node_run(
            workflow_run_id=workflow_run_id,
            node_instance_id=node.node_instance_id,
            node_type=node.node_type,
            status=status,
            owner_process_id=process_id if process_generation is not None else None,
            process_generation=process_generation,
        )
        initialized.append(node_run)
    return tuple(initialized)


def recover_ready_nodes(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None = None,
    dag: WorkflowDag,
) -> tuple[NodeRun, ...]:
    node_runs = _node_runs_by_instance(store, workflow_run_id)
    newly_ready: list[NodeRun] = []
    for node in dag.nodes:
        node_run = node_runs.get(node.node_instance_id)
        if (
            node_run is None
            or node_run.status != NodeRunStatus.WAITING_DEPENDENCY.value
        ):
            continue
        if _node_dependencies_are_ready(
            store=store,
            workflow_run_id=workflow_run_id,
            dag=dag,
            node=node,
            node_runs=node_runs,
        ):
            ready = store.update_node_run_status(
                node_run.node_run_id,
                NodeRunStatus.READY,
                expected_state_version=node_run.state_version,
                allowed_source_statuses=[NodeRunStatus.WAITING_DEPENDENCY],
                owner_process_id=process_id if process_generation is not None else None,
                process_generation=process_generation,
            )
            if ready is not None:
                newly_ready.append(ready)
    return tuple(newly_ready)


def apply_node_success(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None = None,
    dag: WorkflowDag,
    node_instance_id: str,
    event_sink: RuntimeEventSink,
) -> NodeAdvanceResult:
    node_run = store.get_node_run_for_instance(
        workflow_run_id=workflow_run_id,
        node_instance_id=node_instance_id,
    )
    if node_run is None:
        return NodeAdvanceResult(None, (), None)
    completed = store.update_node_run_status(
        node_run.node_run_id,
        NodeRunStatus.SUCCEEDED,
        finished_at=utc_now(),
        expected_state_version=node_run.state_version,
        allowed_source_statuses=[
            NodeRunStatus.RUNNING,
            NodeRunStatus.LONG_RUNNING,
        ],
        owner_process_id=process_id if process_generation is not None else None,
        process_generation=process_generation,
    )
    if completed is None:
        return NodeAdvanceResult(None, (), None)
    return advance_after_node_success(
        store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        dag=dag,
        completed_node=completed,
        event_sink=event_sink,
    )


def advance_after_node_success(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None = None,
    dag: WorkflowDag,
    completed_node: NodeRun,
    event_sink: RuntimeEventSink,
) -> NodeAdvanceResult:
    event_sink.emit(
        EventModel(
            event_type=EventType.NODE_FINISHED,
            workflow_run_id=workflow_run_id,
            node_run_id=completed_node.node_run_id,
            payload={
                "process_id": process_id,
                "node_instance_id": completed_node.node_instance_id,
            },
        )
    )
    newly_ready = recover_ready_nodes(
        store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        dag=dag,
    )
    workflow_completed = _complete_workflow_if_all_nodes_succeeded(
        store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        event_sink=event_sink,
    )
    return NodeAdvanceResult(completed_node, newly_ready, workflow_completed)


def _complete_workflow_if_all_nodes_succeeded(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None = None,
    event_sink: RuntimeEventSink,
) -> WorkflowRun | None:
    node_runs = store.list_node_runs(workflow_run_id)
    if not node_runs or any(
        node_run.status != NodeRunStatus.SUCCEEDED.value for node_run in node_runs
    ):
        return None
    run = store.get_workflow_run(workflow_run_id)
    if run is None or run.status == WorkflowRunStatus.SUCCEEDED.value:
        return run
    completed = store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.SUCCEEDED,
        finished_at=utc_now(),
        expected_state_version=run.state_version,
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
        owner_process_id=process_id if process_generation is not None else None,
        process_generation=process_generation,
    )
    if completed is not None:
        event_sink.emit(
            EventModel(
                event_type=EventType.WORKFLOW_FINISHED,
                workflow_run_id=workflow_run_id,
                payload={"process_id": process_id},
            )
        )
    return completed


def _node_runs_by_instance(
    store: RuntimeStore,
    workflow_run_id: str,
) -> dict[str, NodeRun]:
    return {
        node_run.node_instance_id: node_run
        for node_run in store.list_node_runs(workflow_run_id)
    }


def _node_dependencies_are_ready(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    dag: WorkflowDag,
    node: DagNode,
    node_runs: dict[str, NodeRun],
) -> bool:
    return _ordinary_upstreams_are_ready(
        node=node,
        node_runs=node_runs,
    ) and _loop_exit_dependencies_are_ready(
        store=store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id=node.node_instance_id,
    )


def _ordinary_upstreams_are_ready(
    *,
    node: DagNode,
    node_runs: dict[str, NodeRun],
) -> bool:
    return all(
        node_runs.get(upstream_id) is not None
        and node_runs[upstream_id].status == NodeRunStatus.SUCCEEDED.value
        for upstream_id in node.upstream_node_ids
    )


def _loop_exit_dependencies_are_ready(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    dag: WorkflowDag,
    node_instance_id: str,
) -> bool:
    dependencies = loop_exit_dependencies_for_node(dag, node_instance_id)
    if not dependencies:
        return True
    for dependency in dependencies:
        loop = store.get_loop_run_for_workflow_loop(
            workflow_run_id=workflow_run_id,
            loop_id=dependency.loop_id,
        )
        if loop is None or loop.status not in _LOOP_EXIT_READY_STATUSES:
            return False
    return True


def _publish_node_queued(
    event_sink: RuntimeEventSink,
    workflow_run_id: str,
    process_id: str,
    node_run: NodeRun,
) -> None:
    event_sink.emit(
        EventModel(
            event_type=EventType.NODE_QUEUED,
            workflow_run_id=workflow_run_id,
            node_run_id=node_run.node_run_id,
            payload={
                "process_id": process_id,
                "node_instance_id": node_run.node_instance_id,
            },
        )
    )
