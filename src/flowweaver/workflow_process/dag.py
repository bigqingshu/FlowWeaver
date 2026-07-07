from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from flowweaver.workflow.definition import (
    ControlProtocolMode,
    WorkflowDefinitionModel,
)


@dataclass(frozen=True)
class DagNode:
    node_instance_id: str
    node_type: str
    node_version: str
    config: dict[str, Any]
    upstream_node_ids: tuple[str, ...]
    downstream_node_ids: tuple[str, ...]


@dataclass(frozen=True)
class LoopExitDependency:
    node_instance_id: str
    loop_id: str


@dataclass(frozen=True)
class WorkflowDag:
    nodes: tuple[DagNode, ...]
    topological_order: tuple[str, ...]
    ready_node_ids: tuple[str, ...]
    loop_exit_dependencies: tuple[LoopExitDependency, ...] = ()


def build_workflow_dag(definition: WorkflowDefinitionModel) -> WorkflowDag:
    node_ids = [node.node_instance_id for node in definition.nodes if node.enabled]
    node_id_set = set(node_ids)
    upstream: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    downstream: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for connection in definition.connections:
        if (
            connection.source_node_id not in node_id_set
            or connection.target_node_id not in node_id_set
        ):
            continue
        downstream[connection.source_node_id].add(connection.target_node_id)
        upstream[connection.target_node_id].add(connection.source_node_id)

    order = _topological_sort(node_ids, downstream, upstream)
    node_by_id = {node.node_instance_id: node for node in definition.nodes}
    dag_nodes = tuple(
        DagNode(
            node_instance_id=node_id,
            node_type=node_by_id[node_id].node_type,
            node_version=node_by_id[node_id].node_version,
            config=node_by_id[node_id].config,
            upstream_node_ids=tuple(sorted(upstream[node_id])),
            downstream_node_ids=tuple(sorted(downstream[node_id])),
        )
        for node_id in order
    )
    loop_exit_dependencies = _loop_exit_dependencies(definition, node_id_set)
    loop_exit_node_ids = {
        dependency.node_instance_id for dependency in loop_exit_dependencies
    }
    return WorkflowDag(
        nodes=dag_nodes,
        topological_order=tuple(order),
        ready_node_ids=tuple(
            node_id
            for node_id in order
            if not upstream[node_id] and node_id not in loop_exit_node_ids
        ),
        loop_exit_dependencies=loop_exit_dependencies,
    )


def restrict_workflow_dag_to_upstream_closure(
    dag: WorkflowDag,
    target_node_instance_id: str,
) -> WorkflowDag:
    node_by_id = {node.node_instance_id: node for node in dag.nodes}
    if target_node_instance_id not in node_by_id:
        raise ValueError(
            f"Target node not found in workflow DAG: {target_node_instance_id}"
        )

    selected: set[str] = set()
    stack = [target_node_instance_id]
    while stack:
        node_id = stack.pop()
        if node_id in selected:
            continue
        selected.add(node_id)
        stack.extend(node_by_id[node_id].upstream_node_ids)

    ordered_ids = tuple(
        node_id for node_id in dag.topological_order if node_id in selected
    )
    nodes = tuple(
        DagNode(
            node_instance_id=node_id,
            node_type=node_by_id[node_id].node_type,
            node_version=node_by_id[node_id].node_version,
            config=node_by_id[node_id].config,
            upstream_node_ids=tuple(
                upstream_id
                for upstream_id in node_by_id[node_id].upstream_node_ids
                if upstream_id in selected
            ),
            downstream_node_ids=tuple(
                downstream_id
                for downstream_id in node_by_id[node_id].downstream_node_ids
                if downstream_id in selected
            ),
        )
        for node_id in ordered_ids
    )
    return WorkflowDag(
        nodes=nodes,
        topological_order=ordered_ids,
        ready_node_ids=tuple(
            node.node_instance_id
            for node in nodes
            if not node.upstream_node_ids
            and not _node_has_loop_exit_dependency(
                dag.loop_exit_dependencies,
                node.node_instance_id,
            )
        ),
        loop_exit_dependencies=tuple(
            dependency
            for dependency in dag.loop_exit_dependencies
            if dependency.node_instance_id in selected
        ),
    )


def loop_exit_dependencies_for_node(
    dag: WorkflowDag,
    node_instance_id: str,
) -> tuple[LoopExitDependency, ...]:
    return tuple(
        dependency
        for dependency in dag.loop_exit_dependencies
        if dependency.node_instance_id == node_instance_id
    )


def _loop_exit_dependencies(
    definition: WorkflowDefinitionModel,
    node_id_set: set[str],
) -> tuple[LoopExitDependency, ...]:
    protocol = definition.control_protocol
    if protocol is None or protocol.mode != ControlProtocolMode.ENABLED:
        return ()
    dependencies: list[LoopExitDependency] = []
    for region in protocol.loop_regions:
        if not region.enabled or region.end_node_id is None:
            continue
        if region.end_node_id in node_id_set:
            dependencies.append(
                LoopExitDependency(
                    node_instance_id=region.end_node_id,
                    loop_id=region.loop_id,
                )
            )
    return tuple(dependencies)


def _node_has_loop_exit_dependency(
    dependencies: tuple[LoopExitDependency, ...],
    node_instance_id: str,
) -> bool:
    return any(
        dependency.node_instance_id == node_instance_id for dependency in dependencies
    )


def _topological_sort(
    node_ids: list[str],
    downstream: dict[str, set[str]],
    upstream: dict[str, set[str]],
) -> list[str]:
    indegree = {node_id: len(upstream[node_id]) for node_id in node_ids}
    queue = deque([node_id for node_id in node_ids if indegree[node_id] == 0])
    order: list[str] = []
    reverse_index = defaultdict(list)
    for node_id, children in downstream.items():
        for child in children:
            reverse_index[node_id].append(child)

    while queue:
        node_id = queue.popleft()
        order.append(node_id)
        for child in sorted(reverse_index[node_id]):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(order) != len(node_ids):
        raise ValueError("Workflow DAG contains a cycle")
    return order
