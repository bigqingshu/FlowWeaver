from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import (
    LoopIterationRunStatus,
    LoopRunStatus,
    NodeResultStatus,
)


class LoopTerminalCloseStatus(str, Enum):
    CLOSED = "CLOSED"
    NO_LOOP_ASSOCIATION = "NO_LOOP_ASSOCIATION"
    ITERATION_NOT_FOUND = "ITERATION_NOT_FOUND"
    LOOP_NOT_FOUND = "LOOP_NOT_FOUND"
    UNSUPPORTED_NODE_RESULT = "UNSUPPORTED_NODE_RESULT"


@dataclass(frozen=True)
class LoopTerminalCloseResult:
    status: LoopTerminalCloseStatus
    loop_run_id: str | None = None
    loop_iteration_id: str | None = None


def close_loop_after_node_terminal_result(
    store: RuntimeStore,
    *,
    node_run_id: str,
    result_status: NodeResultStatus,
    error: dict[str, Any] | None = None,
    finished_at: datetime | None = None,
) -> LoopTerminalCloseResult:
    if result_status not in {
        NodeResultStatus.FAILED,
        NodeResultStatus.CANCELLED,
    }:
        return LoopTerminalCloseResult(LoopTerminalCloseStatus.UNSUPPORTED_NODE_RESULT)
    links = store.list_loop_iteration_node_runs_by_node_run(node_run_id)
    if not links:
        return LoopTerminalCloseResult(LoopTerminalCloseStatus.NO_LOOP_ASSOCIATION)
    link = links[-1]
    iteration = store.get_loop_iteration_run(link.loop_iteration_id)
    if iteration is None:
        return LoopTerminalCloseResult(
            LoopTerminalCloseStatus.ITERATION_NOT_FOUND,
            loop_iteration_id=link.loop_iteration_id,
        )
    loop = store.get_loop_run(iteration.loop_run_id)
    if loop is None:
        return LoopTerminalCloseResult(
            LoopTerminalCloseStatus.LOOP_NOT_FOUND,
            loop_iteration_id=iteration.loop_iteration_id,
        )

    close_time = finished_at or utc_now()
    if result_status == NodeResultStatus.CANCELLED:
        iteration_status = LoopIterationRunStatus.CANCELLED
        loop_status = LoopRunStatus.CANCELLED
        failed_node_run_id = None
    else:
        iteration_status = LoopIterationRunStatus.FAILED
        loop_status = LoopRunStatus.FAILED
        failed_node_run_id = node_run_id

    store.update_loop_iteration_run_status(
        iteration.loop_iteration_id,
        iteration_status,
        failed_node_run_id=failed_node_run_id,
        finished_at=close_time,
        error=error,
        allowed_source_statuses=[
            LoopIterationRunStatus.PENDING,
            LoopIterationRunStatus.RUNNING,
        ],
    )
    current_loop = store.get_loop_run(loop.loop_run_id)
    if current_loop is not None:
        store.update_loop_run_status(
            current_loop.loop_run_id,
            loop_status,
            finished_at=close_time,
            error=error,
            expected_state_version=current_loop.state_version,
            allowed_source_statuses=[LoopRunStatus.PENDING, LoopRunStatus.RUNNING],
        )
    return LoopTerminalCloseResult(
        LoopTerminalCloseStatus.CLOSED,
        loop_run_id=loop.loop_run_id,
        loop_iteration_id=iteration.loop_iteration_id,
    )


def cancel_active_loop_runs_for_workflow(
    store: RuntimeStore,
    *,
    workflow_run_id: str,
    error: dict[str, Any] | None = None,
    finished_at: datetime | None = None,
) -> int:
    close_time = finished_at or utc_now()
    closed_count = 0
    for loop in store.list_loop_runs(
        workflow_run_id,
        statuses=[LoopRunStatus.PENDING, LoopRunStatus.RUNNING],
    ):
        for iteration in store.list_loop_iteration_runs(
            loop.loop_run_id,
            statuses=[
                LoopIterationRunStatus.PENDING,
                LoopIterationRunStatus.RUNNING,
            ],
        ):
            store.update_loop_iteration_run_status(
                iteration.loop_iteration_id,
                LoopIterationRunStatus.CANCELLED,
                finished_at=close_time,
                error=error,
                allowed_source_statuses=[
                    LoopIterationRunStatus.PENDING,
                    LoopIterationRunStatus.RUNNING,
                ],
            )
        updated = store.update_loop_run_status(
            loop.loop_run_id,
            LoopRunStatus.CANCELLED,
            finished_at=close_time,
            error=error,
            expected_state_version=loop.state_version,
            allowed_source_statuses=[LoopRunStatus.PENDING, LoopRunStatus.RUNNING],
        )
        if updated is not None:
            closed_count += 1
    return closed_count
