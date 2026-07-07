from __future__ import annotations

from dataclasses import dataclass

from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.enums import LoopIterationRunStatus, NodeRunStatus
from flowweaver.workflow_process.dag import (
    DagLoopRegion,
    DagNode,
    WorkflowDag,
    loop_region_for_loop_id,
)


@dataclass(frozen=True)
class LoopIterationSchedulingSummary:
    created_node_runs: int = 0
    marked_ready_node_runs: int = 0


def advance_loop_iteration_after_node_success(
    store: RuntimeStore,
    *,
    dag: WorkflowDag,
    completed_node: NodeRun,
    owner_process_id: str | None = None,
    process_generation: int | None = None,
) -> LoopIterationSchedulingSummary:
    created = 0
    marked_ready = 0
    links = store.list_loop_iteration_node_runs_by_node_run(completed_node.node_run_id)
    if not links:
        return LoopIterationSchedulingSummary()
    dag_nodes = {node.node_instance_id: node for node in dag.nodes}
    for link in links:
        iteration = store.get_loop_iteration_run(link.loop_iteration_id)
        if (
            iteration is None
            or iteration.status != LoopIterationRunStatus.RUNNING.value
        ):
            continue
        loop = store.get_loop_run(iteration.loop_run_id)
        if loop is None:
            continue
        region = loop_region_for_loop_id(dag, loop.loop_id)
        if region is None:
            continue
        if completed_node.node_instance_id == region.judge_node_instance_id:
            continue
        for target in _downstream_loop_nodes(
            dag_nodes,
            region=region,
            node_instance_id=completed_node.node_instance_id,
        ):
            result = _ensure_iteration_node_ready(
                store,
                loop_iteration_id=iteration.loop_iteration_id,
                workflow_run_id=loop.workflow_run_id,
                region=region,
                target=target,
                dag_nodes=dag_nodes,
                owner_process_id=owner_process_id,
                process_generation=process_generation,
            )
            created += result.created_node_runs
            marked_ready += result.marked_ready_node_runs
    return LoopIterationSchedulingSummary(
        created_node_runs=created,
        marked_ready_node_runs=marked_ready,
    )


def _downstream_loop_nodes(
    dag_nodes: dict[str, DagNode],
    *,
    region: DagLoopRegion,
    node_instance_id: str,
) -> tuple[DagNode, ...]:
    node = dag_nodes.get(node_instance_id)
    if node is None:
        return ()
    member_ids = set(region.member_node_instance_ids)
    return tuple(
        dag_nodes[downstream_id]
        for downstream_id in node.downstream_node_ids
        if downstream_id in member_ids and downstream_id in dag_nodes
    )


def _ensure_iteration_node_ready(
    store: RuntimeStore,
    *,
    loop_iteration_id: str,
    workflow_run_id: str,
    region: DagLoopRegion,
    target: DagNode,
    dag_nodes: dict[str, DagNode],
    owner_process_id: str | None,
    process_generation: int | None,
) -> LoopIterationSchedulingSummary:
    if not _iteration_dependencies_succeeded(
        store,
        loop_iteration_id=loop_iteration_id,
        region=region,
        target=target,
        dag_nodes=dag_nodes,
        workflow_run_id=workflow_run_id,
    ):
        return LoopIterationSchedulingSummary()
    role = _role_for_node(region, target.node_instance_id)
    existing = _linked_node_run_for_iteration_node(
        store,
        loop_iteration_id=loop_iteration_id,
        node_instance_id=target.node_instance_id,
    )
    if existing is not None:
        if existing.status in {
            NodeRunStatus.READY.value,
            NodeRunStatus.QUEUED.value,
            NodeRunStatus.RUNNING.value,
            NodeRunStatus.LONG_RUNNING.value,
            NodeRunStatus.SUCCEEDED.value,
        }:
            return LoopIterationSchedulingSummary()
        ready = store.update_node_run_status(
            existing.node_run_id,
            NodeRunStatus.READY,
            expected_state_version=existing.state_version,
            allowed_source_statuses=[
                NodeRunStatus.PENDING,
                NodeRunStatus.WAITING_DEPENDENCY,
            ],
            owner_process_id=owner_process_id,
            process_generation=process_generation,
        )
        return LoopIterationSchedulingSummary(
            marked_ready_node_runs=1 if ready is not None else 0
        )

    created = store.create_node_run(
        workflow_run_id=workflow_run_id,
        node_instance_id=target.node_instance_id,
        node_type=target.node_type,
        status=NodeRunStatus.READY,
        owner_process_id=owner_process_id,
        process_generation=process_generation,
    )
    link = store.add_loop_iteration_node_run(
        loop_iteration_id=loop_iteration_id,
        node_run_id=created.node_run_id,
        role=role,
    )
    if link is None:
        return LoopIterationSchedulingSummary()
    return LoopIterationSchedulingSummary(created_node_runs=1)


def _iteration_dependencies_succeeded(
    store: RuntimeStore,
    *,
    loop_iteration_id: str,
    region: DagLoopRegion,
    target: DagNode,
    dag_nodes: dict[str, DagNode],
    workflow_run_id: str,
) -> bool:
    member_ids = set(region.member_node_instance_ids)
    for upstream_id in target.upstream_node_ids:
        if upstream_id in member_ids:
            upstream = _linked_node_run_for_iteration_node(
                store,
                loop_iteration_id=loop_iteration_id,
                node_instance_id=upstream_id,
            )
            if upstream is None or upstream.status != NodeRunStatus.SUCCEEDED.value:
                return False
            continue
        if upstream_id not in dag_nodes:
            continue
        upstream = store.get_node_run_for_instance(
            workflow_run_id=workflow_run_id,
            node_instance_id=upstream_id,
        )
        if upstream is None or upstream.status != NodeRunStatus.SUCCEEDED.value:
            return False
    return True


def _linked_node_run_for_iteration_node(
    store: RuntimeStore,
    *,
    loop_iteration_id: str,
    node_instance_id: str,
) -> NodeRun | None:
    links = store.list_loop_iteration_node_runs(
        loop_iteration_id,
        node_instance_id=node_instance_id,
    )
    for link in reversed(links):
        node_run = store.get_node_run(link.node_run_id)
        if node_run is not None:
            return node_run
    return None


def _role_for_node(region: DagLoopRegion, node_instance_id: str) -> str:
    if node_instance_id == region.start_node_instance_id:
        return "ENTRY"
    if node_instance_id == region.judge_node_instance_id:
        return "JUDGE"
    return "BODY"
