from __future__ import annotations

from dataclasses import dataclass, field

from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.enums import NodeRunStatus
from flowweaver.workflow_process.dag import DagNode, WorkflowDag
from flowweaver.workflow_process.ready_queue_input_refs import (
    input_refs_for_ready_node as _input_refs_for_ready_node,
)
from flowweaver.workflow_process.table_input_resolver import (
    TableInputResolutionIssue,
)

_IN_FLIGHT_NODE_RUN_STATUSES = frozenset(
    {
        NodeRunStatus.RUNNING.value,
        NodeRunStatus.LONG_RUNNING.value,
        NodeRunStatus.CANCEL_REQUESTED.value,
    }
)


@dataclass(frozen=True)
class ReadyNodeCandidate:
    node_run: NodeRun
    dag_node: DagNode
    input_refs: tuple[str, ...]
    dependency_count: int
    input_slot_bindings: dict[str, str] = field(default_factory=dict)
    input_resolution_issue: TableInputResolutionIssue | None = None

def collect_ready_node_candidates(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    dag: WorkflowDag,
) -> tuple[ReadyNodeCandidate, ...]:
    node_runs = store.list_node_runs(workflow_run_id)
    dag_nodes_by_instance = {node.node_instance_id: node for node in dag.nodes}
    dag_order_by_instance = {
        node.node_instance_id: index for index, node in enumerate(dag.nodes)
    }
    candidates: list[ReadyNodeCandidate] = []
    for node_run in node_runs:
        if node_run.status != NodeRunStatus.READY.value:
            continue
        dag_node = dag_nodes_by_instance.get(node_run.node_instance_id)
        if dag_node is None:
            continue
        input_result = _input_refs_for_ready_node(
            store=store,
            node_runs=node_runs,
            node_run=node_run,
            dag_node=dag_node,
        )
        if input_result.waiting:
            continue
        candidates.append(
            ReadyNodeCandidate(
                node_run=node_run,
                dag_node=dag_node,
                input_refs=input_result.input_refs,
                dependency_count=len(dag_node.upstream_node_ids),
                input_slot_bindings=input_result.input_slot_bindings,
                input_resolution_issue=input_result.issue,
            )
        )
    candidates.sort(
        key=lambda candidate: (
            dag_order_by_instance[candidate.node_run.node_instance_id],
        )
    )
    return tuple(candidates)


def count_in_flight_node_runs(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
) -> int:
    return sum(
        1
        for node_run in store.list_node_runs(workflow_run_id)
        if node_run.status in _IN_FLIGHT_NODE_RUN_STATUSES
    )
