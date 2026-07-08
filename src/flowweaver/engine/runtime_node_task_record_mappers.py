from __future__ import annotations

import json

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    NodeRunRecord,
    NodeTaskRecord,
    NodeTaskResultRecord,
)
from flowweaver.engine.runtime_models import NodeRun
from flowweaver.engine.runtime_record_codecs import (
    _datetime_from_text,
    _datetime_to_text,
    _json_dumps,
    _optional_datetime_from_text,
)
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


def _node_run_from_record(record: NodeRunRecord) -> NodeRun:
    return NodeRun(
        node_run_id=record.node_run_id,
        workflow_run_id=record.workflow_run_id,
        node_instance_id=record.node_instance_id,
        node_type=record.node_type,
        status=record.status,
        state_version=record.state_version,
        executor_id=record.executor_id,
        progress=record.progress,
        current_stage=record.current_stage,
        attempt=record.attempt,
        started_at=_optional_datetime_from_text(record.started_at),
        finished_at=_optional_datetime_from_text(record.finished_at),
        last_heartbeat=_optional_datetime_from_text(record.last_heartbeat),
        error=json.loads(record.error_json) if record.error_json else None,
    )


def _node_task_to_record(task: NodeTaskModel) -> NodeTaskRecord:
    return NodeTaskRecord(
        task_id=task.task_id,
        workflow_run_id=task.workflow_run_id,
        workflow_process_id=task.workflow_process_id,
        process_generation=task.process_generation,
        node_run_id=task.node_run_id,
        node_instance_id=task.node_instance_id,
        node_type=task.node_type,
        node_version=task.node_version,
        attempt=task.attempt,
        input_refs_json=json.dumps(
            task.input_refs,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        input_slot_bindings_json=json.dumps(
            task.input_slot_bindings,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        config_json=_json_dumps(task.config),
        timeout_seconds=task.timeout_seconds,
        created_at=_datetime_to_text(utc_now()),
    )


def _node_task_from_record(record: NodeTaskRecord) -> NodeTaskModel:
    return NodeTaskModel(
        task_id=record.task_id,
        workflow_run_id=record.workflow_run_id,
        workflow_process_id=record.workflow_process_id,
        process_generation=record.process_generation,
        node_run_id=record.node_run_id,
        node_instance_id=record.node_instance_id,
        node_type=record.node_type,
        node_version=record.node_version,
        attempt=record.attempt,
        input_refs=list(json.loads(record.input_refs_json)),
        input_slot_bindings=dict(json.loads(record.input_slot_bindings_json or "{}")),
        config=json.loads(record.config_json),
        timeout_seconds=record.timeout_seconds,
    )


def _node_task_result_to_record(
    result: NodeTaskResultModel,
) -> NodeTaskResultRecord:
    return NodeTaskResultRecord(
        result_id=result.result_id,
        task_id=result.task_id,
        node_run_id=result.node_run_id,
        attempt=result.attempt,
        executor_id=result.executor_id,
        process_generation=result.process_generation,
        status=result.status.value,
        output_refs_json=json.dumps(
            result.output_refs,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        output_slot_bindings_json=json.dumps(
            result.output_slot_bindings,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        summary_json=_json_dumps(result.summary),
        error_json=_json_dumps(result.error) if result.error is not None else None,
        started_at=_datetime_to_text(result.started_at),
        finished_at=_datetime_to_text(result.finished_at),
    )


def _node_task_result_from_record(
    record: NodeTaskResultRecord,
) -> NodeTaskResultModel:
    return NodeTaskResultModel(
        result_id=record.result_id,
        task_id=record.task_id,
        node_run_id=record.node_run_id,
        attempt=record.attempt,
        executor_id=record.executor_id,
        process_generation=record.process_generation,
        status=NodeResultStatus(record.status),
        output_refs=list(json.loads(record.output_refs_json)),
        output_slot_bindings=dict(
            json.loads(record.output_slot_bindings_json or "{}")
        ),
        summary=json.loads(record.summary_json) if record.summary_json else {},
        error=json.loads(record.error_json) if record.error_json else None,
        started_at=_datetime_from_text(record.started_at),
        finished_at=_datetime_from_text(record.finished_at),
    )
