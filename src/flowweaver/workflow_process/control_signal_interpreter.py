from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.protocols.table_ref import TableRefModel
from flowweaver.workflow_process.loop_control import (
    ControlSignal,
    SerialLoopAdvanceResult,
    advance_serial_loop_from_decision,
)


class ControlSignalInterpretationStatus(str, Enum):
    NO_CONTROL_SIGNAL = "NO_CONTROL_SIGNAL"
    IGNORED_PREVIEW_SIGNAL = "IGNORED_PREVIEW_SIGNAL"
    REJECTED_SIGNAL_TYPE = "REJECTED_SIGNAL_TYPE"
    OUTPUT_TABLE_NOT_FOUND = "OUTPUT_TABLE_NOT_FOUND"
    OUTPUT_PROVIDER_NOT_FOUND = "OUTPUT_PROVIDER_NOT_FOUND"
    LOOP_ITERATION_NOT_ASSOCIATED = "LOOP_ITERATION_NOT_ASSOCIATED"
    LOOP_ITERATION_NOT_FOUND = "LOOP_ITERATION_NOT_FOUND"
    LOOP_NOT_FOUND = "LOOP_NOT_FOUND"
    TARGET_LOOP_MISMATCH = "TARGET_LOOP_MISMATCH"
    LOOP_DECISION_APPLIED = "LOOP_DECISION_APPLIED"


@dataclass(frozen=True)
class ControlSignalInterpretationResult:
    status: ControlSignalInterpretationStatus
    signal: ControlSignal | None = None
    advance_result: SerialLoopAdvanceResult | None = None
    detail: str | None = None


def interpret_control_outputs_after_node_success(
    store: RuntimeStore,
    registry: TableProviderRegistry,
    *,
    workflow_run_id: str,
    completed_node: NodeRun,
    output_refs: list[str],
) -> ControlSignalInterpretationResult:
    for output_ref_id in output_refs:
        table_ref = store.get_table_ref(output_ref_id)
        if table_ref is None:
            return ControlSignalInterpretationResult(
                ControlSignalInterpretationStatus.OUTPUT_TABLE_NOT_FOUND,
                detail=output_ref_id,
            )
        signal = _signal_from_table(registry, table_ref)
        if signal is None:
            continue
        return _apply_control_signal(
            store,
            workflow_run_id=workflow_run_id,
            completed_node=completed_node,
            signal=signal,
        )
    return ControlSignalInterpretationResult(
        ControlSignalInterpretationStatus.NO_CONTROL_SIGNAL
    )


def _signal_from_table(
    registry: TableProviderRegistry,
    table_ref: TableRefModel,
) -> ControlSignal | None:
    provider = registry.get(table_ref.provider_id)
    if provider is None:
        return None
    rows = provider.read_rows(table_ref, offset=0, limit=1)
    if not rows:
        return None
    row = rows[0]
    if not _looks_like_control_row(row):
        return None
    return ControlSignal.from_row(row)


def _apply_control_signal(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    completed_node: NodeRun,
    signal: ControlSignal,
) -> ControlSignalInterpretationResult:
    if signal.signal_type != "loop_decision":
        return ControlSignalInterpretationResult(
            ControlSignalInterpretationStatus.REJECTED_SIGNAL_TYPE,
            signal=signal,
            detail=signal.signal_type,
        )
    if not signal.actual_control:
        return ControlSignalInterpretationResult(
            ControlSignalInterpretationStatus.IGNORED_PREVIEW_SIGNAL,
            signal=signal,
        )
    links = store.list_loop_iteration_node_runs_by_node_run(
        completed_node.node_run_id,
    )
    if not links:
        return ControlSignalInterpretationResult(
            ControlSignalInterpretationStatus.LOOP_ITERATION_NOT_ASSOCIATED,
            signal=signal,
            detail=completed_node.node_run_id,
        )
    link = links[-1]
    iteration = store.get_loop_iteration_run(link.loop_iteration_id)
    if iteration is None:
        return ControlSignalInterpretationResult(
            ControlSignalInterpretationStatus.LOOP_ITERATION_NOT_FOUND,
            signal=signal,
            detail=link.loop_iteration_id,
        )
    loop = store.get_loop_run(iteration.loop_run_id)
    if loop is None or loop.workflow_run_id != workflow_run_id:
        return ControlSignalInterpretationResult(
            ControlSignalInterpretationStatus.LOOP_NOT_FOUND,
            signal=signal,
            detail=iteration.loop_run_id,
        )
    target_loop = _target_loop_id(signal)
    if target_loop is not None and target_loop not in {
        loop.loop_id,
        loop.loop_run_id,
    }:
        return ControlSignalInterpretationResult(
            ControlSignalInterpretationStatus.TARGET_LOOP_MISMATCH,
            signal=signal,
            detail=target_loop,
        )
    advance_result = advance_serial_loop_from_decision(
        store,
        loop_run_id=loop.loop_run_id,
        loop_iteration_id=iteration.loop_iteration_id,
        signal=signal,
        next_input_table_ref_id=_next_input_table_ref_id(signal),
        next_input_selector=_next_input_selector(signal),
    )
    return ControlSignalInterpretationResult(
        ControlSignalInterpretationStatus.LOOP_DECISION_APPLIED,
        signal=signal,
        advance_result=advance_result,
    )


def _looks_like_control_row(row: Mapping[str, Any]) -> bool:
    return {
        "signal_type",
        "selected_branch",
        "actual_control",
    }.issubset(row.keys())


def _target_loop_id(signal: ControlSignal) -> str | None:
    if signal.target_anchor:
        return signal.target_anchor
    if signal.details is None:
        return None
    loop_id = signal.details.get("loop_id")
    return loop_id if isinstance(loop_id, str) and loop_id else None


def _next_input_selector(signal: ControlSignal) -> Mapping[str, Any] | None:
    if signal.details is None:
        return None
    selector = signal.details.get("next_input_selector")
    return selector if isinstance(selector, Mapping) else None


def _next_input_table_ref_id(signal: ControlSignal) -> str | None:
    if signal.details is None:
        return None
    value = signal.details.get("next_input_table_ref_id")
    return value if isinstance(value, str) and value else None
