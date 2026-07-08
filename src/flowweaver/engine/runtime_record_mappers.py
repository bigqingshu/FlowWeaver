from __future__ import annotations

import json

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    LoopIterationNodeRunRecord,
    LoopIterationRunRecord,
    LoopIterationTableRefRecord,
    LoopRunRecord,
    NodeRunRecord,
    NodeTaskRecord,
    NodeTaskResultRecord,
    RuntimeEventRecord,
    WorkflowProcessRecord,
    WorkflowRecord,
    WorkflowRevisionRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_models import (
    LoopIterationNodeRun,
    LoopIterationRun,
    LoopIterationTableRef,
    LoopRun,
    NodeRun,
    RuntimeEventLog,
    WorkflowDefinition,
    WorkflowProcess,
    WorkflowRevision,
    WorkflowRun,
)
from flowweaver.engine.runtime_record_codecs import (
    _datetime_from_text,
    _datetime_to_text,
    _optional_datetime_from_text,
)
from flowweaver.engine.runtime_record_codecs import (
    _definition_hash as _definition_hash,
)
from flowweaver.engine.runtime_record_codecs import (
    _json_dumps as _json_dumps,
)
from flowweaver.engine.runtime_record_codecs import (
    _optional_datetime_to_text as _optional_datetime_to_text,
)
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _input_snapshot_from_record as _input_snapshot_from_record,
)
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _input_snapshot_json as _input_snapshot_json,
)
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _read_lease_from_record as _read_lease_from_record,
)
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _selected_members_json as _selected_members_json,
)
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _shared_publication_from_records as _shared_publication_from_records,
)
from flowweaver.engine.runtime_table_ref_mappers import (
    _data_ref_from_model as _data_ref_from_model,
)
from flowweaver.engine.runtime_table_ref_mappers import (
    _table_ref_from_record as _table_ref_from_record,
)
from flowweaver.protocols.enums import (
    NodeResultStatus,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


def _workflow_definition_from_records(
    workflow: WorkflowRecord,
    revision: WorkflowRevisionRecord,
) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id=workflow.workflow_id,
        name=workflow.name,
        revision_id=revision.revision_id,
        version=revision.version,
        definition_hash=revision.definition_hash,
        definition=json.loads(revision.definition_json),
        status=workflow.status,
        created_at=_datetime_from_text(workflow.created_at),
        updated_at=_datetime_from_text(workflow.updated_at),
    )




def _workflow_revision_from_record(record: WorkflowRevisionRecord) -> WorkflowRevision:
    return WorkflowRevision(
        revision_id=record.revision_id,
        workflow_id=record.workflow_id,
        version=record.version,
        definition_hash=record.definition_hash,
        definition=json.loads(record.definition_json),
        created_at=_datetime_from_text(record.created_at),
        created_by=record.created_by,
    )




def _workflow_run_from_record(record: WorkflowRunRecord) -> WorkflowRun:
    return WorkflowRun(
        workflow_run_id=record.workflow_run_id,
        workflow_id=record.workflow_id,
        revision_id=record.revision_id,
        workflow_version=record.workflow_version,
        definition_hash=record.definition_hash,
        status=record.status,
        state_version=record.state_version,
        owner_process_id=record.owner_process_id,
        process_generation=record.process_generation,
        fencing_token=record.fencing_token,
        input_snapshot_id=record.input_snapshot_id,
        run_mode=record.run_mode,
        trigger_source=record.trigger_source,
        target_node_instance_id=record.target_node_instance_id,
        started_at=_optional_datetime_from_text(record.started_at),
        finished_at=_optional_datetime_from_text(record.finished_at),
        completion_reason=record.completion_reason,
        error=json.loads(record.error_json) if record.error_json else None,
    )




def _workflow_process_from_record(record: WorkflowProcessRecord) -> WorkflowProcess:
    return WorkflowProcess(
        process_id=record.process_id,
        workflow_run_id=record.workflow_run_id,
        os_pid=record.os_pid,
        process_generation=record.process_generation,
        fencing_token=record.fencing_token,
        status=record.status,
        started_at=_datetime_from_text(record.started_at),
        last_heartbeat_at=_optional_datetime_from_text(record.last_heartbeat_at),
        cancel_requested_at=_optional_datetime_from_text(record.cancel_requested_at),
        exited_at=_optional_datetime_from_text(record.exited_at),
        exit_code=record.exit_code,
        error=json.loads(record.error_json) if record.error_json else None,
    )




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




def _runtime_event_from_record(record: RuntimeEventRecord) -> RuntimeEventLog:
    return RuntimeEventLog(
        event_id=record.event_id,
        sequence_number=record.sequence_number,
        event_version=record.event_version,
        event_type=record.event_type,
        timestamp=_datetime_from_text(record.timestamp),
        workflow_run_id=record.workflow_run_id,
        node_run_id=record.node_run_id,
        payload=json.loads(record.payload_json),
    )





