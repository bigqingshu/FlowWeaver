from __future__ import annotations

from flowweaver.engine.runtime_store import LoopIterationRun, LoopRun, RuntimeStore
from flowweaver.protocols.enums import LoopIterationRunStatus, LoopRunStatus
from flowweaver.workflow_process.loop_control_models import (
    ControlSignal,
    SerialLoopAdvanceResult,
    SerialLoopAdvanceStatus,
)


def duplicate_advance_result(
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
