from __future__ import annotations

from dataclasses import dataclass

from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.enums import NodeRunStatus, TableRole
from flowweaver.workflow_process.dag import DagNode, WorkflowDag
from flowweaver.workflow_process.table_input_resolver import (
    TableInputResolutionIssue,
    TableInputResolutionStatus,
    resolve_configured_input_refs,
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
    input_resolution_issue: TableInputResolutionIssue | None = None


@dataclass(frozen=True)
class ReadyInputRefsResult:
    input_refs: tuple[str, ...] = ()
    waiting: bool = False
    issue: TableInputResolutionIssue | None = None


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


def _input_refs_for_ready_node(
    *,
    store: RuntimeStore,
    node_runs: list[NodeRun],
    node_run: NodeRun,
    dag_node: DagNode,
) -> ReadyInputRefsResult:
    loop_links = store.list_loop_iteration_node_runs_by_node_run(node_run.node_run_id)
    if loop_links:
        return _loop_iteration_input_refs_for_ready_node(
            store=store,
            node_runs=node_runs,
            loop_iteration_id=loop_links[-1].loop_iteration_id,
            dag_node=dag_node,
        )
    return _root_input_refs_for_ready_node(
        store=store,
        node_runs=node_runs,
        dag_node=dag_node,
    )


def _root_input_refs_for_ready_node(
    *,
    store: RuntimeStore,
    node_runs: list[NodeRun],
    dag_node: DagNode,
) -> ReadyInputRefsResult:
    input_refs: list[str] = []
    upstream_node_runs: dict[str, NodeRun] = {}
    for upstream_node_id in dag_node.upstream_node_ids:
        upstream_node = _latest_succeeded_node_run_for_instance(
            node_runs,
            upstream_node_id,
        )
        if upstream_node is None:
            return ReadyInputRefsResult(waiting=True)
        upstream_node_runs[upstream_node_id] = upstream_node
        result = store.get_latest_succeeded_node_task_result_for_node_run(
            upstream_node.node_run_id
        )
        if result is None:
            return ReadyInputRefsResult(waiting=True)
        input_refs.extend(
            _current_input_refs_from_output_refs(
                store=store,
                output_refs=result.output_refs,
            )
        )
    return _configured_or_default_input_refs(
        store=store,
        config=dag_node.config,
        upstream_node_runs=upstream_node_runs,
        default_input_refs=tuple(input_refs),
    )


def _loop_iteration_input_refs_for_ready_node(
    *,
    store: RuntimeStore,
    node_runs: list[NodeRun],
    loop_iteration_id: str,
    dag_node: DagNode,
) -> ReadyInputRefsResult:
    input_refs: list[str] = []
    upstream_node_runs: dict[str, NodeRun] = {}
    for upstream_node_id in dag_node.upstream_node_ids:
        upstream_node = _succeeded_loop_iteration_node_run(
            store,
            loop_iteration_id=loop_iteration_id,
            node_instance_id=upstream_node_id,
        )
        if upstream_node is None:
            upstream_node = _latest_succeeded_node_run_for_instance(
                node_runs,
                upstream_node_id,
            )
        if upstream_node is None:
            return ReadyInputRefsResult(waiting=True)
        upstream_node_runs[upstream_node_id] = upstream_node
        result = store.get_latest_succeeded_node_task_result_for_node_run(
            upstream_node.node_run_id
        )
        if result is None:
            return ReadyInputRefsResult(waiting=True)
        input_refs.extend(
            _current_input_refs_from_output_refs(
                store=store,
                output_refs=result.output_refs,
            )
        )
    return _configured_or_default_input_refs(
        store=store,
        config=dag_node.config,
        upstream_node_runs=upstream_node_runs,
        default_input_refs=tuple(input_refs),
    )


def _configured_or_default_input_refs(
    *,
    store: RuntimeStore,
    config: dict,
    upstream_node_runs: dict[str, NodeRun],
    default_input_refs: tuple[str, ...],
) -> ReadyInputRefsResult:
    resolution = resolve_configured_input_refs(
        store=store,
        config=config,
        upstream_node_runs=upstream_node_runs,
    )
    if resolution.status == TableInputResolutionStatus.NO_CONFIG:
        return ReadyInputRefsResult(input_refs=default_input_refs)
    if resolution.status == TableInputResolutionStatus.RESOLVED:
        return ReadyInputRefsResult(input_refs=resolution.input_refs)
    if resolution.status == TableInputResolutionStatus.WAITING:
        return ReadyInputRefsResult(waiting=True)
    return ReadyInputRefsResult(issue=resolution.issue)


def _succeeded_loop_iteration_node_run(
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
        if node_run is not None and node_run.status == NodeRunStatus.SUCCEEDED.value:
            return node_run
    return None


def _latest_succeeded_node_run_for_instance(
    node_runs: list[NodeRun],
    node_instance_id: str,
) -> NodeRun | None:
    for node_run in reversed(node_runs):
        if (
            node_run.node_instance_id == node_instance_id
            and node_run.status == NodeRunStatus.SUCCEEDED.value
        ):
            return node_run
    return None


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
