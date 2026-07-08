from __future__ import annotations

import json

from flowweaver.engine.db_models import (
    LoopIterationNodeRunRecord,
    LoopIterationRunRecord,
    LoopIterationTableRefRecord,
    LoopRunRecord,
)
from flowweaver.engine.runtime_models import (
    LoopIterationNodeRun,
    LoopIterationRun,
    LoopIterationTableRef,
    LoopRun,
)
from flowweaver.engine.runtime_record_codecs import (
    _datetime_from_text,
    _optional_datetime_from_text,
)


def _loop_run_from_record(record: LoopRunRecord) -> LoopRun:
    return LoopRun(
        loop_run_id=record.loop_run_id,
        workflow_run_id=record.workflow_run_id,
        loop_id=record.loop_id,
        start_node_instance_id=record.start_node_instance_id,
        judge_node_instance_id=record.judge_node_instance_id,
        status=record.status,
        state_version=record.state_version,
        current_iteration=record.current_iteration,
        max_iterations=record.max_iterations,
        exit_reason=record.exit_reason,
        started_at=_optional_datetime_from_text(record.started_at),
        finished_at=_optional_datetime_from_text(record.finished_at),
        error=json.loads(record.error_json) if record.error_json else None,
        created_at=_datetime_from_text(record.created_at),
    )


def _loop_iteration_run_from_record(
    record: LoopIterationRunRecord,
) -> LoopIterationRun:
    return LoopIterationRun(
        loop_iteration_id=record.loop_iteration_id,
        loop_run_id=record.loop_run_id,
        iteration_index=record.iteration_index,
        status=record.status,
        state_version=record.state_version,
        input_table_ref_id=record.input_table_ref_id,
        input_selector=(
            json.loads(record.input_selector_json)
            if record.input_selector_json
            else None
        ),
        output_table_ref_id=record.output_table_ref_id,
        failed_node_run_id=record.failed_node_run_id,
        started_at=_optional_datetime_from_text(record.started_at),
        finished_at=_optional_datetime_from_text(record.finished_at),
        error=json.loads(record.error_json) if record.error_json else None,
        created_at=_datetime_from_text(record.created_at),
    )


def _loop_iteration_table_ref_from_record(
    record: LoopIterationTableRefRecord,
) -> LoopIterationTableRef:
    return LoopIterationTableRef(
        loop_iteration_id=record.loop_iteration_id,
        table_ref_id=record.table_ref_id,
        role=record.role,
        created_at=_datetime_from_text(record.created_at),
    )


def _loop_iteration_node_run_from_record(
    record: LoopIterationNodeRunRecord,
) -> LoopIterationNodeRun:
    return LoopIterationNodeRun(
        loop_iteration_id=record.loop_iteration_id,
        node_run_id=record.node_run_id,
        node_instance_id=record.node_instance_id,
        role=record.role,
        created_at=_datetime_from_text(record.created_at),
    )
