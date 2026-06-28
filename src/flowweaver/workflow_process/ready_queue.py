from __future__ import annotations

from dataclasses import dataclass

from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.enums import NodeRunStatus
from flowweaver.workflow_process.dag import DagNode, WorkflowDag


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
        input_refs.extend(result.output_refs)
    return input_refs
