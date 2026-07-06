from __future__ import annotations

from dataclasses import dataclass

from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.enums import NodeRunStatus, TableRole
from flowweaver.workflow_process.dag import DagNode, WorkflowDag

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


def collect_ready_node_candidates(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    dag: WorkflowDag,
) -> tuple[ReadyNodeCandidate, ...]:
    node_runs_by_instance = {
        node_run.node_instance_id: node_run
        for node_run in store.list_node_runs(workflow_run_id)
    }
    candidates: list[ReadyNodeCandidate] = []
    for dag_node in dag.nodes:
        node_run = node_runs_by_instance.get(dag_node.node_instance_id)
        if node_run is None or node_run.status != NodeRunStatus.READY.value:
            continue
        input_refs = _input_refs_for_ready_node(
            store=store,
            node_runs_by_instance=node_runs_by_instance,
            dag_node=dag_node,
        )
        if input_refs is None:
            continue
        candidates.append(
            ReadyNodeCandidate(
                node_run=node_run,
                dag_node=dag_node,
                input_refs=tuple(input_refs),
                dependency_count=len(dag_node.upstream_node_ids),
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


def _input_refs_for_ready_node(
    *,
    store: RuntimeStore,
    node_runs_by_instance: dict[str, NodeRun],
    dag_node: DagNode,
) -> list[str] | None:
    input_refs: list[str] = []
    for upstream_node_id in dag_node.upstream_node_ids:
        upstream_node = node_runs_by_instance.get(upstream_node_id)
        if upstream_node is None:
            return None
        result = store.get_latest_succeeded_node_task_result_for_node_run(
            upstream_node.node_run_id
        )
        if result is None:
            return None
        input_refs.extend(
            _current_input_refs_from_output_refs(
                store=store,
                output_refs=result.output_refs,
            )
        )
    return input_refs


def _current_input_refs_from_output_refs(
    *,
    store: RuntimeStore,
    output_refs: list[str],
) -> list[str]:
    input_refs: list[str] = []
    for output_ref in output_refs:
        table_ref = store.get_table_ref(output_ref)
        if table_ref is None:
            input_refs.append(output_ref)
            continue
        if table_ref.role == TableRole.CURRENT:
            input_refs.append(output_ref)
    return input_refs
