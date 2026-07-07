from __future__ import annotations

from dataclasses import dataclass

from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.workflow.definition import (
    ControlProtocolMode,
    LoopRegionModel,
    WorkflowDefinitionModel,
)
from flowweaver.workflow_process.dag import WorkflowDag
from flowweaver.workflow_process.loop_control import (
    SerialLoopStartStatus,
    start_serial_loop,
)


@dataclass(frozen=True)
class LoopRuntimeInitializationSummary:
    loop_runs_seen: int = 0
    loop_runs_started: int = 0
    first_iteration_node_links_added: int = 0


def initialize_enabled_loop_runtime_state(
    store: RuntimeStore,
    *,
    definition: WorkflowDefinitionModel,
    workflow_run_id: str,
    dag: WorkflowDag,
) -> LoopRuntimeInitializationSummary:
    protocol = definition.control_protocol
    if protocol is None or protocol.mode != ControlProtocolMode.ENABLED:
        return LoopRuntimeInitializationSummary()

    loop_runs_seen = 0
    loop_runs_started = 0
    node_links_added = 0
    dag_node_ids = {node.node_instance_id for node in dag.nodes}
    for region in protocol.loop_regions:
        if not region.enabled:
            continue
        loop = store.create_loop_run(
            workflow_run_id=workflow_run_id,
            loop_id=region.loop_id,
            start_node_instance_id=region.start_node_id,
            judge_node_instance_id=region.judge_node_id,
            max_iterations=region.max_iterations,
        )
        if loop is None:
            continue
        loop_runs_seen += 1
        started = start_serial_loop(store, loop_run_id=loop.loop_run_id)
        if started.status == SerialLoopStartStatus.STARTED:
            loop_runs_started += 1
        iteration = started.iteration or store.get_loop_iteration_run_for_index(
            loop_run_id=loop.loop_run_id,
            iteration_index=0,
        )
        if iteration is None:
            continue
        node_links_added += _bind_first_iteration_existing_node_runs(
            store,
            workflow_run_id=workflow_run_id,
            loop_iteration_id=iteration.loop_iteration_id,
            region=region,
            dag_node_ids=dag_node_ids,
        )

    return LoopRuntimeInitializationSummary(
        loop_runs_seen=loop_runs_seen,
        loop_runs_started=loop_runs_started,
        first_iteration_node_links_added=node_links_added,
    )


def _bind_first_iteration_existing_node_runs(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    loop_iteration_id: str,
    region: LoopRegionModel,
    dag_node_ids: set[str],
) -> int:
    added = 0
    for node_instance_id, role in _first_iteration_node_roles(region):
        if node_instance_id not in dag_node_ids:
            continue
        node_run = store.get_node_run_for_instance(
            workflow_run_id=workflow_run_id,
            node_instance_id=node_instance_id,
        )
        if node_run is None:
            continue
        existing = store.list_loop_iteration_node_runs(
            loop_iteration_id,
            node_instance_id=node_instance_id,
            role=role,
        )
        if any(link.node_run_id == node_run.node_run_id for link in existing):
            continue
        link = store.add_loop_iteration_node_run(
            loop_iteration_id=loop_iteration_id,
            node_run_id=node_run.node_run_id,
            role=role,
        )
        if link is not None:
            added += 1
    return added


def _first_iteration_node_roles(
    region: LoopRegionModel,
) -> tuple[tuple[str, str], ...]:
    return (
        ((region.start_node_id, "ENTRY"),)
        + tuple((node_id, "BODY") for node_id in region.body_node_ids)
        + ((region.judge_node_id, "JUDGE"),)
    )
