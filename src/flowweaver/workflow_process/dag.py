from __future__ import annotations

from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.dag_loop_regions import (
    build_loop_exit_dependencies as _build_loop_exit_dependencies,
)
from flowweaver.workflow_process.dag_loop_regions import (
    build_loop_regions as _build_loop_regions,
)
from flowweaver.workflow_process.dag_loop_regions import (
    loop_exit_dependencies_for_node as loop_exit_dependencies_for_node,
)
from flowweaver.workflow_process.dag_loop_regions import (
    loop_region_for_loop_id as loop_region_for_loop_id,
)
from flowweaver.workflow_process.dag_loop_regions import (
    node_has_loop_exit_dependency as _node_has_loop_exit_dependency,
)
from flowweaver.workflow_process.dag_models import DagLoopRegion as DagLoopRegion
from flowweaver.workflow_process.dag_models import DagNode as DagNode
from flowweaver.workflow_process.dag_models import (
    LoopExitDependency as LoopExitDependency,
)
from flowweaver.workflow_process.dag_models import WorkflowDag as WorkflowDag
from flowweaver.workflow_process.dag_topology import (
    topological_sort as _topological_sort,
)


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
    loop_regions = _build_loop_regions(definition, node_id_set)
    loop_exit_dependencies = _build_loop_exit_dependencies(loop_regions)
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
        loop_regions=loop_regions,
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
        loop_regions=tuple(
            region
            for region in dag.loop_regions
            if set(region.member_node_instance_ids).issubset(selected)
        ),
    )
