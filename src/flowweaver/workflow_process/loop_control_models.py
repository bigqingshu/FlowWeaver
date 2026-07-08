from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from flowweaver.engine.runtime_store import LoopIterationRun, LoopRun
from flowweaver.protocols.enums import LoopRunStatus


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


TERMINAL_LOOP_RUN_STATUSES = frozenset(
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
