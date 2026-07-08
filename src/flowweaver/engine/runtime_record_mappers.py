from __future__ import annotations

import json

from flowweaver.engine.db_models import (
    RuntimeEventRecord,
    WorkflowProcessRecord,
    WorkflowRecord,
    WorkflowRevisionRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_loop_record_mappers import (
    _loop_iteration_node_run_from_record as _loop_iteration_node_run_from_record,
)
from flowweaver.engine.runtime_loop_record_mappers import (
    _loop_iteration_run_from_record as _loop_iteration_run_from_record,
)
from flowweaver.engine.runtime_loop_record_mappers import (
    _loop_iteration_table_ref_from_record as _loop_iteration_table_ref_from_record,
)
from flowweaver.engine.runtime_loop_record_mappers import (
    _loop_run_from_record as _loop_run_from_record,
)
from flowweaver.engine.runtime_models import (
    RuntimeEventLog,
    WorkflowDefinition,
    WorkflowProcess,
    WorkflowRevision,
    WorkflowRun,
)
from flowweaver.engine.runtime_node_task_record_mappers import (
    _node_run_from_record as _node_run_from_record,
)
from flowweaver.engine.runtime_node_task_record_mappers import (
    _node_task_from_record as _node_task_from_record,
)
from flowweaver.engine.runtime_node_task_record_mappers import (
    _node_task_result_from_record as _node_task_result_from_record,
)
from flowweaver.engine.runtime_node_task_record_mappers import (
    _node_task_result_to_record as _node_task_result_to_record,
)
from flowweaver.engine.runtime_node_task_record_mappers import (
    _node_task_to_record as _node_task_to_record,
)
from flowweaver.engine.runtime_record_codecs import (
    _datetime_from_text,
    _optional_datetime_from_text,
)
from flowweaver.engine.runtime_record_codecs import (
    _datetime_to_text as _datetime_to_text,
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





