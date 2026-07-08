from __future__ import annotations

from datetime import datetime

from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.enums import NodeRunStatus
from flowweaver.workflow_process.dag import WorkflowDag


def mark_blocked_descendants_skipped(
    *,
    store: RuntimeStore,
    dag: WorkflowDag,
    workflow_run_id: str,
    process_id: str,
    process_generation: int,
    failed_node: NodeRun,
    finished_at: datetime,
) -> None:
    dag_nodes_by_id = {node.node_instance_id: node for node in dag.nodes}
    node_runs_by_instance = {
        node.node_instance_id: node
        for node in store.list_node_runs(workflow_run_id)
    }
    failed_dag_node = dag_nodes_by_id.get(failed_node.node_instance_id)
    if failed_dag_node is None:
        return
    stack = list(failed_dag_node.downstream_node_ids)
    visited: set[str] = set()
    while stack:
        node_instance_id = stack.pop()
        if node_instance_id in visited:
            continue
        visited.add(node_instance_id)
        dag_node = dag_nodes_by_id.get(node_instance_id)
        if dag_node is not None:
            stack.extend(dag_node.downstream_node_ids)
        node_run = node_runs_by_instance.get(node_instance_id)
        if node_run is None:
            continue
        skipped = store.update_node_run_status(
            node_run.node_run_id,
            NodeRunStatus.SKIPPED,
            finished_at=finished_at,
            error={
                "reason": "UPSTREAM_FAILED",
                "failed_node_instance_id": failed_node.node_instance_id,
                "failed_node_run_id": failed_node.node_run_id,
            },
            expected_state_version=node_run.state_version,
            allowed_source_statuses=[
                NodeRunStatus.PENDING,
                NodeRunStatus.READY,
                NodeRunStatus.WAITING_DEPENDENCY,
            ],
            owner_process_id=process_id,
            process_generation=process_generation,
        )
        if skipped is not None:
            node_runs_by_instance[node_instance_id] = skipped
