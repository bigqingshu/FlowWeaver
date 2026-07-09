from __future__ import annotations

from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.enums import (
    LoopRunStatus,
    NodeRunStatus,
)
from flowweaver.workflow_process.dag import (
    DagNode,
    WorkflowDag,
    loop_exit_dependencies_for_node,
)

_LOOP_EXIT_READY_STATUSES = frozenset(
    {
        LoopRunStatus.ENDED.value,
        LoopRunStatus.MAX_ITERATIONS_REACHED.value,
    }
)


def node_runs_by_instance(
    store: RuntimeStore,
    workflow_run_id: str,
) -> dict[str, NodeRun]:
    return {
        node_run.node_instance_id: node_run
        for node_run in store.list_node_runs(workflow_run_id)
    }


def node_dependencies_are_ready(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    dag: WorkflowDag,
    node: DagNode,
    node_runs: dict[str, NodeRun],
) -> bool:
    return _ordinary_upstreams_are_ready(
        node=node,
        node_runs=node_runs,
    ) and _loop_exit_dependencies_are_ready(
        store=store,
        workflow_run_id=workflow_run_id,
        dag=dag,
        node_instance_id=node.node_instance_id,
    )


def _ordinary_upstreams_are_ready(
    *,
    node: DagNode,
    node_runs: dict[str, NodeRun],
) -> bool:
    return all(
        node_runs.get(upstream_id) is not None
        and node_runs[upstream_id].status == NodeRunStatus.SUCCEEDED.value
        for upstream_id in node.upstream_node_ids
    )


def _loop_exit_dependencies_are_ready(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    dag: WorkflowDag,
    node_instance_id: str,
) -> bool:
    dependencies = loop_exit_dependencies_for_node(dag, node_instance_id)
    if not dependencies:
        return True
    for dependency in dependencies:
        loop = store.get_loop_run_for_workflow_loop(
            workflow_run_id=workflow_run_id,
            loop_id=dependency.loop_id,
        )
        if loop is None or loop.status not in _LOOP_EXIT_READY_STATUSES:
            return False
    return True
