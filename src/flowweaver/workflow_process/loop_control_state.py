from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import (
    LoopIterationRunStatus,
    LoopIterationTableRefRole,
    LoopRunStatus,
)
from flowweaver.workflow_process.loop_control_models import (
    TERMINAL_LOOP_RUN_STATUSES,
    SerialLoopInspection,
    SerialLoopInspectionStatus,
    SerialLoopStartResult,
    SerialLoopStartStatus,
)


def start_serial_loop(
    store: RuntimeStore,
    *,
    loop_run_id: str,
    first_input_table_ref_id: str | None = None,
    first_input_selector: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> SerialLoopStartResult:
    started_at = now or utc_now()
    loop = store.get_loop_run(loop_run_id)
    if loop is None:
        return SerialLoopStartResult(SerialLoopStartStatus.LOOP_NOT_FOUND)
    first_iteration = store.get_loop_iteration_run_for_index(
        loop_run_id=loop_run_id,
        iteration_index=0,
    )
    if loop.status == LoopRunStatus.RUNNING.value and first_iteration is not None:
        return SerialLoopStartResult(
            SerialLoopStartStatus.ALREADY_STARTED,
            loop_run=loop,
            iteration=first_iteration,
        )
    if loop.status != LoopRunStatus.PENDING.value:
        return SerialLoopStartResult(
            SerialLoopStartStatus.LOOP_STATE_REJECTED,
            loop_run=loop,
            iteration=first_iteration,
        )
    iteration = store.create_loop_iteration_run(
        loop_run_id=loop_run_id,
        iteration_index=0,
        status=LoopIterationRunStatus.RUNNING,
        input_table_ref_id=first_input_table_ref_id,
        input_selector=first_input_selector,
        started_at=started_at,
    )
    if iteration is None:
        return SerialLoopStartResult(
            SerialLoopStartStatus.LOOP_STATE_REJECTED,
            loop_run=loop,
        )
    if first_input_table_ref_id is not None:
        store.add_loop_iteration_table_ref(
            loop_iteration_id=iteration.loop_iteration_id,
            table_ref_id=first_input_table_ref_id,
            role=LoopIterationTableRefRole.INPUT,
        )
    running = store.update_loop_run_status(
        loop_run_id,
        LoopRunStatus.RUNNING,
        current_iteration=0,
        started_at=started_at,
        expected_state_version=loop.state_version,
        allowed_source_statuses=[LoopRunStatus.PENDING],
    )
    if running is None:
        return SerialLoopStartResult(
            SerialLoopStartStatus.LOOP_STATE_REJECTED,
            loop_run=store.get_loop_run(loop_run_id),
            iteration=iteration,
        )
    return SerialLoopStartResult(
        SerialLoopStartStatus.STARTED,
        loop_run=running,
        iteration=iteration,
    )


def inspect_serial_loop_state(
    store: RuntimeStore,
    *,
    loop_run_id: str,
) -> SerialLoopInspection:
    loop = store.get_loop_run(loop_run_id)
    if loop is None:
        return SerialLoopInspection(SerialLoopInspectionStatus.LOOP_NOT_FOUND)

    iterations = store.list_loop_iteration_runs(loop_run_id)
    latest = iterations[-1] if iterations else None
    running_iterations = [
        iteration
        for iteration in iterations
        if iteration.status == LoopIterationRunStatus.RUNNING.value
    ]
    if loop.status in TERMINAL_LOOP_RUN_STATUSES:
        return SerialLoopInspection(
            SerialLoopInspectionStatus.LOOP_TERMINAL,
            loop_run=loop,
            latest_iteration=latest,
            active_iteration=running_iterations[-1] if running_iterations else None,
            next_iteration_index=None,
        )
    if len(running_iterations) > 1:
        return SerialLoopInspection(
            SerialLoopInspectionStatus.INCONSISTENT_STATE,
            loop_run=loop,
            latest_iteration=latest,
            active_iteration=running_iterations[-1],
            next_iteration_index=None,
            detail="multiple_running_iterations",
        )
    if latest is None:
        status = (
            SerialLoopInspectionStatus.NOT_STARTED
            if loop.status == LoopRunStatus.PENDING.value
            else SerialLoopInspectionStatus.INCONSISTENT_STATE
        )
        return SerialLoopInspection(
            status,
            loop_run=loop,
            next_iteration_index=0,
        )
    if running_iterations:
        active = running_iterations[0]
        return SerialLoopInspection(
            SerialLoopInspectionStatus.ACTIVE_ITERATION_RUNNING,
            loop_run=loop,
            latest_iteration=latest,
            active_iteration=active,
            next_iteration_index=active.iteration_index + 1,
        )
    if latest.status == LoopIterationRunStatus.SUCCEEDED.value:
        return SerialLoopInspection(
            SerialLoopInspectionStatus.WAITING_FOR_DECISION,
            loop_run=loop,
            latest_iteration=latest,
            next_iteration_index=latest.iteration_index + 1,
        )
    if latest.status == LoopIterationRunStatus.FAILED.value:
        return SerialLoopInspection(
            SerialLoopInspectionStatus.BLOCKED_BY_FAILED_ITERATION,
            loop_run=loop,
            latest_iteration=latest,
            next_iteration_index=None,
        )
    if latest.status == LoopIterationRunStatus.CANCELLED.value:
        return SerialLoopInspection(
            SerialLoopInspectionStatus.BLOCKED_BY_CANCELLED_ITERATION,
            loop_run=loop,
            latest_iteration=latest,
            next_iteration_index=None,
        )
    return SerialLoopInspection(
        SerialLoopInspectionStatus.INCONSISTENT_STATE,
        loop_run=loop,
        latest_iteration=latest,
        next_iteration_index=None,
        detail=latest.status,
    )


def workflow_loop_runs_are_terminal(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
) -> bool:
    return all(
        loop.status in TERMINAL_LOOP_RUN_STATUSES
        for loop in store.list_loop_runs(workflow_run_id)
    )
