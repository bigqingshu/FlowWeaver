from __future__ import annotations

from dataclasses import dataclass

from flowweaver.engine.runtime_store import (
    LoopIterationRun,
    LoopRun,
    NodeRun,
    RuntimeStore,
)
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.protocols.enums import LoopRunStatus, NodeRunStatus
from flowweaver.workflow_process.control_signal_interpreter import (
    ControlSignalInterpretationStatus,
    interpret_control_outputs_after_node_success,
)
from flowweaver.workflow_process.dag import WorkflowDag
from flowweaver.workflow_process.loop_control import (
    SerialLoopInspectionStatus,
    inspect_serial_loop_state,
)
from flowweaver.workflow_process.loop_iteration_nodes import (
    LoopIterationEntryNodeStatus,
    ensure_loop_iteration_entry_node_run,
)


@dataclass(frozen=True)
class LoopRecoverySummary:
    interpreted_decisions: int = 0
    ensured_entry_nodes: int = 0
    closed_failed_loops: int = 0
    inconsistent_loops: tuple[str, ...] = ()


def recover_serial_loop_runtime_state(
    store: RuntimeStore,
    registry: TableProviderRegistry,
    *,
    workflow_run_id: str,
    dag: WorkflowDag,
    process_id: str,
    process_generation: int | None = None,
) -> LoopRecoverySummary:
    interpreted_decisions = 0
    ensured_entry_nodes = 0
    closed_failed_loops = 0
    inconsistent: list[str] = []
    for loop in store.list_loop_runs(workflow_run_id):
        inspection = inspect_serial_loop_state(store, loop_run_id=loop.loop_run_id)
        if inspection.status == SerialLoopInspectionStatus.ACTIVE_ITERATION_RUNNING:
            if inspection.active_iteration is not None:
                ensured_entry_nodes += _ensure_entry_node(
                    store,
                    dag=dag,
                    loop_iteration_id=inspection.active_iteration.loop_iteration_id,
                    process_id=process_id,
                    process_generation=process_generation,
                )
                interpreted_decisions += _recover_iteration_decision(
                    store,
                    registry,
                    workflow_run_id=workflow_run_id,
                    loop=loop,
                    iteration=inspection.active_iteration,
                    dag=dag,
                    process_id=process_id,
                    process_generation=process_generation,
                )
        elif inspection.status == SerialLoopInspectionStatus.WAITING_FOR_DECISION:
            if inspection.latest_iteration is not None:
                interpreted_decisions += _recover_iteration_decision(
                    store,
                    registry,
                    workflow_run_id=workflow_run_id,
                    loop=loop,
                    iteration=inspection.latest_iteration,
                    dag=dag,
                    process_id=process_id,
                    process_generation=process_generation,
                )
        elif (
            inspection.status == SerialLoopInspectionStatus.BLOCKED_BY_FAILED_ITERATION
        ):
            closed_failed_loops += _close_failed_loop(
                store,
                loop=loop,
                iteration=inspection.latest_iteration,
            )
        elif inspection.status == SerialLoopInspectionStatus.INCONSISTENT_STATE:
            inconsistent.append(loop.loop_run_id)
    return LoopRecoverySummary(
        interpreted_decisions=interpreted_decisions,
        ensured_entry_nodes=ensured_entry_nodes,
        closed_failed_loops=closed_failed_loops,
        inconsistent_loops=tuple(inconsistent),
    )


def _recover_iteration_decision(
    store: RuntimeStore,
    registry: TableProviderRegistry,
    *,
    workflow_run_id: str,
    loop: LoopRun,
    iteration: LoopIterationRun,
    dag: WorkflowDag,
    process_id: str,
    process_generation: int | None,
) -> int:
    decision = _latest_successful_judge_result(
        store,
        iteration=iteration,
        judge_node_instance_id=loop.judge_node_instance_id,
    )
    if decision is None:
        return 0
    node_run, output_refs = decision
    interpreted = interpret_control_outputs_after_node_success(
        store,
        registry,
        workflow_run_id=workflow_run_id,
        completed_node=node_run,
        output_refs=output_refs,
    )
    if (
        interpreted.status == ControlSignalInterpretationStatus.LOOP_DECISION_APPLIED
        and interpreted.advance_result is not None
        and interpreted.advance_result.next_iteration is not None
    ):
        _ensure_entry_node(
            store,
            dag=dag,
            loop_iteration_id=interpreted.advance_result.next_iteration.loop_iteration_id,
            process_id=process_id,
            process_generation=process_generation,
        )
    return (
        1
        if interpreted.status == ControlSignalInterpretationStatus.LOOP_DECISION_APPLIED
        else 0
    )


def _latest_successful_judge_result(
    store: RuntimeStore,
    *,
    iteration: LoopIterationRun,
    judge_node_instance_id: str,
) -> tuple[NodeRun, list[str]] | None:
    links = store.list_loop_iteration_node_runs(
        iteration.loop_iteration_id,
        node_instance_id=judge_node_instance_id,
    )
    for link in reversed(links):
        node_run = store.get_node_run(link.node_run_id)
        if node_run is None or node_run.status != NodeRunStatus.SUCCEEDED.value:
            continue
        result = store.get_latest_succeeded_node_task_result_for_node_run(
            node_run.node_run_id
        )
        if result is not None:
            return node_run, result.output_refs
    return None


def _ensure_entry_node(
    store: RuntimeStore,
    *,
    dag: WorkflowDag,
    loop_iteration_id: str,
    process_id: str,
    process_generation: int | None,
) -> int:
    result = ensure_loop_iteration_entry_node_run(
        store,
        dag=dag,
        loop_iteration_id=loop_iteration_id,
        owner_process_id=process_id if process_generation is not None else None,
        process_generation=process_generation,
    )
    return 1 if result.status == LoopIterationEntryNodeStatus.CREATED else 0


def _close_failed_loop(
    store: RuntimeStore,
    *,
    loop: LoopRun,
    iteration: LoopIterationRun | None,
) -> int:
    if iteration is None:
        return 0
    current = store.get_loop_run(loop.loop_run_id)
    if current is None:
        return 0
    updated = store.update_loop_run_status(
        current.loop_run_id,
        LoopRunStatus.FAILED,
        error={
            "message": "Loop blocked by failed iteration",
            "loop_run_id": current.loop_run_id,
            "loop_iteration_id": iteration.loop_iteration_id,
        },
        expected_state_version=current.state_version,
        allowed_source_statuses=[LoopRunStatus.PENDING, LoopRunStatus.RUNNING],
    )
    return 1 if updated is not None else 0
