from __future__ import annotations

from typing import Any

from flowweaver.engine.runtime_models import (
    LoopIterationNodeRun,
    LoopIterationRun,
    LoopIterationTableRef,
    LoopRun,
    NodeRun,
)
from flowweaver.protocols.table_ref import TableRefModel


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
    table_ref: TableRefModel | None = None,
    source_node_instance_id: str | None = None,
) -> dict[str, Any]:
    payload = {
        "loop_iteration_id": value.loop_iteration_id,
        "table_ref_id": value.table_ref_id,
        "role": value.role,
        "created_at": value.created_at.isoformat(),
    }
    if table_ref is not None:
        output_slot = table_ref.opaque_handle.get("output_slot")
        if not isinstance(output_slot, str) or not output_slot:
            output_slot = table_ref.opaque_handle.get("output_name")
        payload.update(
            {
                "logical_table_id": table_ref.logical_table_id,
                "storage_kind": table_ref.storage_kind.value,
                "table_role": table_ref.role.value,
                "version": table_ref.version,
                "lifecycle_status": table_ref.lifecycle_status.value,
                "source_node_run_id": table_ref.created_by_node_run_id,
                "source_node_instance_id": source_node_instance_id,
                "output_slot": output_slot,
            }
        )
    return payload


def loop_iteration_node_run_to_jsonable(
    value: LoopIterationNodeRun,
    node_run: NodeRun,
) -> dict[str, Any]:
    return {
        "loop_iteration_id": value.loop_iteration_id,
        "node_run_id": value.node_run_id,
        "node_instance_id": value.node_instance_id,
        "role": value.role,
        "node_type": node_run.node_type,
        "status": node_run.status,
        "progress": node_run.progress,
        "current_stage": node_run.current_stage,
        "attempt": node_run.attempt,
        "started_at": (
            node_run.started_at.isoformat() if node_run.started_at else None
        ),
        "finished_at": (
            node_run.finished_at.isoformat() if node_run.finished_at else None
        ),
        "error": node_run.error,
    }
