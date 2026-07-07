from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.enums import NodeRunStatus
from flowweaver.workflow_process.dag import DagNode, WorkflowDag


class LoopIterationEntryNodeStatus(str, Enum):
    CREATED = "CREATED"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    LOOP_ITERATION_NOT_FOUND = "LOOP_ITERATION_NOT_FOUND"
    LOOP_NOT_FOUND = "LOOP_NOT_FOUND"
    ENTRY_NODE_NOT_FOUND = "ENTRY_NODE_NOT_FOUND"
    LINK_FAILED = "LINK_FAILED"


@dataclass(frozen=True)
class LoopIterationEntryNodeResult:
    status: LoopIterationEntryNodeStatus
    node_run: NodeRun | None = None
    detail: str | None = None


def ensure_loop_iteration_entry_node_run(
    store: RuntimeStore,
    *,
    dag: WorkflowDag,
    loop_iteration_id: str,
    owner_process_id: str | None = None,
    process_generation: int | None = None,
) -> LoopIterationEntryNodeResult:
    iteration = store.get_loop_iteration_run(loop_iteration_id)
    if iteration is None:
        return LoopIterationEntryNodeResult(
            LoopIterationEntryNodeStatus.LOOP_ITERATION_NOT_FOUND,
            detail=loop_iteration_id,
        )
    loop = store.get_loop_run(iteration.loop_run_id)
    if loop is None:
        return LoopIterationEntryNodeResult(
            LoopIterationEntryNodeStatus.LOOP_NOT_FOUND,
            detail=iteration.loop_run_id,
        )
    existing = _existing_entry_node_run(
        store,
        loop_iteration_id=loop_iteration_id,
        node_instance_id=loop.start_node_instance_id,
    )
    if existing is not None:
        return LoopIterationEntryNodeResult(
            LoopIterationEntryNodeStatus.ALREADY_EXISTS,
            node_run=existing,
        )
    dag_node = _dag_node_by_id(dag, loop.start_node_instance_id)
    if dag_node is None:
        return LoopIterationEntryNodeResult(
            LoopIterationEntryNodeStatus.ENTRY_NODE_NOT_FOUND,
            detail=loop.start_node_instance_id,
        )
    node_run = store.create_node_run(
        workflow_run_id=loop.workflow_run_id,
        node_instance_id=dag_node.node_instance_id,
        node_type=dag_node.node_type,
        status=NodeRunStatus.READY,
        owner_process_id=owner_process_id,
        process_generation=process_generation,
    )
    link = store.add_loop_iteration_node_run(
        loop_iteration_id=loop_iteration_id,
        node_run_id=node_run.node_run_id,
        role="ENTRY",
    )
    if link is None:
        return LoopIterationEntryNodeResult(
            LoopIterationEntryNodeStatus.LINK_FAILED,
            node_run=node_run,
            detail=loop_iteration_id,
        )
    return LoopIterationEntryNodeResult(
        LoopIterationEntryNodeStatus.CREATED,
        node_run=node_run,
    )


def _existing_entry_node_run(
    store: RuntimeStore,
    *,
    loop_iteration_id: str,
    node_instance_id: str,
) -> NodeRun | None:
    links = store.list_loop_iteration_node_runs(
        loop_iteration_id,
        node_instance_id=node_instance_id,
        role="ENTRY",
    )
    for link in links:
        node_run = store.get_node_run(link.node_run_id)
        if node_run is not None:
            return node_run
    return None


def _dag_node_by_id(
    dag: WorkflowDag,
    node_instance_id: str,
) -> DagNode | None:
    for node in dag.nodes:
        if node.node_instance_id == node_instance_id:
            return node
    return None
