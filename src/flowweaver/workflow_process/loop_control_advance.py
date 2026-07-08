from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import LoopIterationRun, LoopRun, RuntimeStore
from flowweaver.protocols.enums import (
    LoopIterationRunStatus,
    LoopIterationTableRefRole,
    LoopRunStatus,
)
from flowweaver.workflow_process.loop_control_models import (
    ControlSignal,
    SerialLoopAdvanceResult,
    SerialLoopAdvanceStatus,
)


def advance_serial_loop_from_decision(
    store: RuntimeStore,
    *,
    loop_run_id: str,
    loop_iteration_id: str,
    signal: ControlSignal,
    continue_branch: str = "continue_loop",
    end_branch: str = "end_loop",
    next_input_table_ref_id: str | None = None,
    next_input_selector: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> SerialLoopAdvanceResult:
    finished_at = now or utc_now()
    if signal.signal_type != "loop_decision":
        return SerialLoopAdvanceResult(
            SerialLoopAdvanceStatus.REJECTED_SIGNAL_TYPE,
            detail=signal.signal_type,
        )
    if not signal.actual_control:
        return SerialLoopAdvanceResult(SerialLoopAdvanceStatus.IGNORED_PREVIEW_SIGNAL)
    if signal.selected_branch not in {continue_branch, end_branch}:
        return SerialLoopAdvanceResult(
            SerialLoopAdvanceStatus.REJECTED_BRANCH,
            detail=signal.selected_branch,
        )

    loop = store.get_loop_run(loop_run_id)
    if loop is None:
        return SerialLoopAdvanceResult(SerialLoopAdvanceStatus.LOOP_NOT_FOUND)
    iteration = store.get_loop_iteration_run(loop_iteration_id)
    if iteration is None or iteration.loop_run_id != loop_run_id:
        return SerialLoopAdvanceResult(
            SerialLoopAdvanceStatus.ITERATION_NOT_FOUND,
            loop_run=loop,
        )
    duplicate = _duplicate_advance_result(
        store,
        loop=loop,
        iteration=iteration,
        signal=signal,
        continue_branch=continue_branch,
        end_branch=end_branch,
    )
    if duplicate is not None:
        return duplicate
    completed_iteration = iteration
    if iteration.status == LoopIterationRunStatus.SUCCEEDED.value:
        if loop.status != LoopRunStatus.RUNNING.value:
            return SerialLoopAdvanceResult(
                SerialLoopAdvanceStatus.LOOP_STATE_REJECTED,
                loop_run=loop,
                completed_iteration=iteration,
            )
    elif iteration.status != LoopIterationRunStatus.RUNNING.value:
        return SerialLoopAdvanceResult(
            SerialLoopAdvanceStatus.ITERATION_STATE_REJECTED,
            loop_run=loop,
            completed_iteration=iteration,
        )
    else:
        updated_iteration = store.update_loop_iteration_run_status(
            loop_iteration_id,
            LoopIterationRunStatus.SUCCEEDED,
            finished_at=finished_at,
            expected_state_version=iteration.state_version,
            allowed_source_statuses=[LoopIterationRunStatus.RUNNING],
        )
        if updated_iteration is None:
            return SerialLoopAdvanceResult(
                SerialLoopAdvanceStatus.ITERATION_STATE_REJECTED,
                loop_run=store.get_loop_run(loop_run_id),
                completed_iteration=store.get_loop_iteration_run(loop_iteration_id),
            )
        completed_iteration = updated_iteration
    loop = store.get_loop_run(loop_run_id)
    if loop is None:
        return SerialLoopAdvanceResult(
            SerialLoopAdvanceStatus.LOOP_NOT_FOUND,
            completed_iteration=completed_iteration,
        )
    if signal.selected_branch == end_branch:
        ended = store.update_loop_run_status(
            loop_run_id,
            LoopRunStatus.ENDED,
            exit_reason=end_branch,
            finished_at=finished_at,
            expected_state_version=loop.state_version,
            allowed_source_statuses=[LoopRunStatus.RUNNING],
        )
        if ended is None:
            return SerialLoopAdvanceResult(
                SerialLoopAdvanceStatus.LOOP_STATE_REJECTED,
                loop_run=store.get_loop_run(loop_run_id),
                completed_iteration=completed_iteration,
            )
        return SerialLoopAdvanceResult(
            SerialLoopAdvanceStatus.LOOP_ENDED,
            loop_run=ended,
            completed_iteration=completed_iteration,
        )

    next_index = completed_iteration.iteration_index + 1
    if next_index >= loop.max_iterations:
        capped = store.update_loop_run_status(
            loop_run_id,
            LoopRunStatus.MAX_ITERATIONS_REACHED,
            current_iteration=completed_iteration.iteration_index,
            exit_reason="max_iterations_reached",
            finished_at=finished_at,
            expected_state_version=loop.state_version,
            allowed_source_statuses=[LoopRunStatus.RUNNING],
        )
        if capped is None:
            return SerialLoopAdvanceResult(
                SerialLoopAdvanceStatus.LOOP_STATE_REJECTED,
                loop_run=store.get_loop_run(loop_run_id),
                completed_iteration=completed_iteration,
            )
        return SerialLoopAdvanceResult(
            SerialLoopAdvanceStatus.LOOP_MAX_ITERATIONS_REACHED,
            loop_run=capped,
            completed_iteration=completed_iteration,
        )

    next_iteration = store.create_loop_iteration_run(
        loop_run_id=loop_run_id,
        iteration_index=next_index,
        status=LoopIterationRunStatus.RUNNING,
        input_table_ref_id=next_input_table_ref_id,
        input_selector=next_input_selector,
        started_at=finished_at,
    )
    if next_iteration is None:
        next_iteration = store.get_loop_iteration_run_for_index(
            loop_run_id=loop_run_id,
            iteration_index=next_index,
        )
    if next_iteration is None:
        return SerialLoopAdvanceResult(
            SerialLoopAdvanceStatus.LOOP_STATE_REJECTED,
            loop_run=store.get_loop_run(loop_run_id),
            completed_iteration=completed_iteration,
        )
    if next_input_table_ref_id is not None:
        store.add_loop_iteration_table_ref(
            loop_iteration_id=next_iteration.loop_iteration_id,
            table_ref_id=next_input_table_ref_id,
            role=LoopIterationTableRefRole.INPUT,
        )
    advanced_loop = store.update_loop_run_status(
        loop_run_id,
        LoopRunStatus.RUNNING,
        current_iteration=next_index,
        expected_state_version=loop.state_version,
        allowed_source_statuses=[LoopRunStatus.RUNNING],
    )
    if advanced_loop is None:
        return SerialLoopAdvanceResult(
            SerialLoopAdvanceStatus.LOOP_STATE_REJECTED,
            loop_run=store.get_loop_run(loop_run_id),
            completed_iteration=completed_iteration,
            next_iteration=next_iteration,
        )
    return SerialLoopAdvanceResult(
        SerialLoopAdvanceStatus.CREATED_NEXT_ITERATION,
        loop_run=advanced_loop,
        completed_iteration=completed_iteration,
        next_iteration=next_iteration,
    )


def _duplicate_advance_result(
    store: RuntimeStore,
    *,
    loop: LoopRun,
    iteration: LoopIterationRun,
    signal: ControlSignal,
    continue_branch: str,
    end_branch: str,
) -> SerialLoopAdvanceResult | None:
    if iteration.status != LoopIterationRunStatus.SUCCEEDED.value:
        return None
    if signal.selected_branch == continue_branch:
        next_iteration = store.get_loop_iteration_run_for_index(
            loop_run_id=loop.loop_run_id,
            iteration_index=iteration.iteration_index + 1,
        )
        if (
            next_iteration is not None
            or loop.status == LoopRunStatus.MAX_ITERATIONS_REACHED.value
        ):
            return SerialLoopAdvanceResult(
                SerialLoopAdvanceStatus.ALREADY_ADVANCED,
                loop_run=loop,
                completed_iteration=iteration,
                next_iteration=next_iteration,
            )
    if signal.selected_branch == end_branch and loop.status in {
        LoopRunStatus.ENDED.value,
        LoopRunStatus.MAX_ITERATIONS_REACHED.value,
    }:
        return SerialLoopAdvanceResult(
            SerialLoopAdvanceStatus.ALREADY_ADVANCED,
            loop_run=loop,
            completed_iteration=iteration,
        )
    return None
