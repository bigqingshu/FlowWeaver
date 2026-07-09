from __future__ import annotations

from typing import Any

from flowweaver.engine.runtime_models import (
    LoopIterationRun,
    LoopIterationTableRef,
    LoopRun,
)


def loop_run_to_jsonable(value: LoopRun) -> dict[str, Any]:
    return {
        "loop_run_id": value.loop_run_id,
        "workflow_run_id": value.workflow_run_id,
        "loop_id": value.loop_id,
        "start_node_instance_id": value.start_node_instance_id,
        "judge_node_instance_id": value.judge_node_instance_id,
        "status": value.status,
        "state_version": value.state_version,
        "current_iteration": value.current_iteration,
        "max_iterations": value.max_iterations,
        "exit_reason": value.exit_reason,
        "started_at": value.started_at.isoformat() if value.started_at else None,
        "finished_at": value.finished_at.isoformat() if value.finished_at else None,
        "error": value.error,
        "created_at": value.created_at.isoformat(),
    }


def loop_iteration_run_to_jsonable(
    value: LoopIterationRun,
) -> dict[str, Any]:
    return {
        "loop_iteration_id": value.loop_iteration_id,
        "loop_run_id": value.loop_run_id,
        "iteration_index": value.iteration_index,
        "status": value.status,
        "state_version": value.state_version,
        "input_table_ref_id": value.input_table_ref_id,
        "input_selector": value.input_selector,
        "output_table_ref_id": value.output_table_ref_id,
        "failed_node_run_id": value.failed_node_run_id,
        "started_at": value.started_at.isoformat() if value.started_at else None,
        "finished_at": value.finished_at.isoformat() if value.finished_at else None,
        "error": value.error,
        "created_at": value.created_at.isoformat(),
    }


def loop_iteration_table_ref_to_jsonable(
    value: LoopIterationTableRef,
) -> dict[str, Any]:
    return {
        "loop_iteration_id": value.loop_iteration_id,
        "table_ref_id": value.table_ref_id,
        "role": value.role,
        "created_at": value.created_at.isoformat(),
    }
