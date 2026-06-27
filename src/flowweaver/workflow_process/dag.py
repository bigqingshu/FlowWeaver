from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from flowweaver.workflow.definition import WorkflowDefinitionModel


@dataclass(frozen=True)
class DagNode:
    node_instance_id: str
    node_type: str
    node_version: str
    upstream_node_ids: tuple[str, ...]
    downstream_node_ids: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowDag:
    nodes: tuple[DagNode, ...]
    topological_order: tuple[str, ...]
    ready_node_ids: tuple[str, ...]


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
            upstream_node_ids=tuple(sorted(upstream[node_id])),
            downstream_node_ids=tuple(sorted(downstream[node_id])),
        )
        for node_id in order
    )
    return WorkflowDag(
        nodes=dag_nodes,
        topological_order=tuple(order),
        ready_node_ids=tuple(node_id for node_id in order if not upstream[node_id]),
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
