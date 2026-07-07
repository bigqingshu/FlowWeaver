from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import (
    LoopIterationRun,
    LoopRun,
    RuntimeStore,
)
from flowweaver.protocols.enums import (
    LoopIterationRunStatus,
    LoopIterationTableRefRole,
    LoopRunStatus,
)


class SerialLoopStartStatus(str, Enum):
    STARTED = "STARTED"
    ALREADY_STARTED = "ALREADY_STARTED"
    LOOP_NOT_FOUND = "LOOP_NOT_FOUND"
    LOOP_STATE_REJECTED = "LOOP_STATE_REJECTED"


class SerialLoopAdvanceStatus(str, Enum):
    CREATED_NEXT_ITERATION = "CREATED_NEXT_ITERATION"
    LOOP_ENDED = "LOOP_ENDED"
    LOOP_MAX_ITERATIONS_REACHED = "LOOP_MAX_ITERATIONS_REACHED"
    ALREADY_ADVANCED = "ALREADY_ADVANCED"
    IGNORED_PREVIEW_SIGNAL = "IGNORED_PREVIEW_SIGNAL"
    REJECTED_SIGNAL_TYPE = "REJECTED_SIGNAL_TYPE"
    REJECTED_BRANCH = "REJECTED_BRANCH"
    LOOP_NOT_FOUND = "LOOP_NOT_FOUND"
    ITERATION_NOT_FOUND = "ITERATION_NOT_FOUND"
    ITERATION_STATE_REJECTED = "ITERATION_STATE_REJECTED"
    LOOP_STATE_REJECTED = "LOOP_STATE_REJECTED"


class SerialLoopInspectionStatus(str, Enum):
    LOOP_NOT_FOUND = "LOOP_NOT_FOUND"
    NOT_STARTED = "NOT_STARTED"
    ACTIVE_ITERATION_RUNNING = "ACTIVE_ITERATION_RUNNING"
    WAITING_FOR_DECISION = "WAITING_FOR_DECISION"
    LOOP_TERMINAL = "LOOP_TERMINAL"
    BLOCKED_BY_FAILED_ITERATION = "BLOCKED_BY_FAILED_ITERATION"
    BLOCKED_BY_CANCELLED_ITERATION = "BLOCKED_BY_CANCELLED_ITERATION"
    INCONSISTENT_STATE = "INCONSISTENT_STATE"


_TERMINAL_LOOP_RUN_STATUSES = frozenset(
    {
        LoopRunStatus.ENDED.value,
        LoopRunStatus.FAILED.value,
        LoopRunStatus.CANCELLED.value,
        LoopRunStatus.MAX_ITERATIONS_REACHED.value,
    }
)


@dataclass(frozen=True)
class ControlSignal:
    signal_type: str
    selected_branch: str
    actual_control: bool
    source_node_id: str = ""
    target_anchor: str = ""
    details: dict[str, Any] | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> ControlSignal:
        details_value = row.get("details")
        details = _details_from_value(details_value)
        return cls(
            signal_type=str(row.get("signal_type", "")),
            selected_branch=str(row.get("selected_branch", "")),
            actual_control=_truthy(row.get("actual_control")),
            source_node_id=str(row.get("source_node_id", "")),
            target_anchor=str(row.get("target_anchor", "")),
            details=details,
        )


@dataclass(frozen=True)
class SerialLoopStartResult:
    status: SerialLoopStartStatus
    loop_run: LoopRun | None = None
    iteration: LoopIterationRun | None = None


@dataclass(frozen=True)
class SerialLoopAdvanceResult:
    status: SerialLoopAdvanceStatus
    loop_run: LoopRun | None = None
    completed_iteration: LoopIterationRun | None = None
    next_iteration: LoopIterationRun | None = None
    detail: str | None = None


@dataclass(frozen=True)
class SerialLoopInspection:
    status: SerialLoopInspectionStatus
    loop_run: LoopRun | None = None
    latest_iteration: LoopIterationRun | None = None
    active_iteration: LoopIterationRun | None = None
    next_iteration_index: int | None = None
    detail: str | None = None


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
    if loop.status in _TERMINAL_LOOP_RUN_STATUSES:
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
        loop.status in _TERMINAL_LOOP_RUN_STATUSES
        for loop in store.list_loop_runs(workflow_run_id)
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
    if iteration.status != LoopIterationRunStatus.RUNNING.value:
        return SerialLoopAdvanceResult(
            SerialLoopAdvanceStatus.ITERATION_STATE_REJECTED,
            loop_run=loop,
            completed_iteration=iteration,
        )

    completed_iteration = store.update_loop_iteration_run_status(
        loop_iteration_id,
        LoopIterationRunStatus.SUCCEEDED,
        finished_at=finished_at,
        expected_state_version=iteration.state_version,
        allowed_source_statuses=[LoopIterationRunStatus.RUNNING],
    )
    if completed_iteration is None:
        return SerialLoopAdvanceResult(
            SerialLoopAdvanceStatus.ITERATION_STATE_REJECTED,
            loop_run=store.get_loop_run(loop_run_id),
            completed_iteration=store.get_loop_iteration_run(loop_iteration_id),
        )
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


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return False


def _details_from_value(value: Any) -> dict[str, Any] | None:
    if value is None or value == "":
        return None
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None
