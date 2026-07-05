from __future__ import annotations

import pytest
from pydantic import ValidationError

from flowweaver.common.serialization import from_msgpack, to_msgpack
from flowweaver.common.time import utc_now
from flowweaver.protocols import (
    ErrorModel,
    ErrorOrigin,
    FieldSchemaModel,
    IPCEnvelope,
    IPCMessageType,
    NodeResultModel,
    NodeResultStatus,
    NodeTaskCancelRequestPayload,
    NodeTaskModel,
    NodeTaskResultModel,
    TableMutability,
    TableRefModel,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.enums import LifecycleStatus


def make_table_ref() -> TableRefModel:
    return TableRefModel(
        table_ref_id="table-1",
        role=TableRole.CURRENT,
        storage_kind=TableStorageKind.RUNTIME_SQL,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.PUBLISHED_IMMUTABLE,
        provider_id="sqlite_runtime",
        logical_table_id="orders",
        opaque_handle={
            "database_path": "runtime/workflow_runs/run-1.db",
            "table_name": "stg_node-1_output",
        },
        schema=[
            FieldSchemaModel(
                field_id="field-1",
                name="amount",
                data_type="number",
                nullable=False,
                ordinal=0,
            )
        ],
        schema_fingerprint="schema-fp",
        version=1,
        capabilities={"READ"},
        lifecycle_status=LifecycleStatus.PUBLISHED,
        created_by_workflow_run_id="run-1",
        created_by_node_run_id="node-run-1",
        created_at=utc_now(),
    )


def test_ipc_envelope_msgpack_round_trip() -> None:
    envelope = IPCEnvelope(
        message_type=IPCMessageType.NODE_TASK_SUBMIT,
        workflow_run_id="run-1",
        node_run_id="node-run-1",
        payload={
            "node_type": "GenerateTestTableNode",
            "input_refs": [],
        },
    )

    restored = from_msgpack(to_msgpack(envelope), IPCEnvelope)

    assert restored == envelope
    assert restored.protocol_version == "1.0"
    assert restored.message_id


def test_node_result_msgpack_round_trip() -> None:
    result = NodeResultModel(
        status=NodeResultStatus.FAILED,
        outputs=[make_table_ref()],
        affected_rows=5,
        errors=[
            ErrorModel(
                error_code="VALIDATION_ERROR",
                message="Invalid field",
                details={"field": "missing_field"},
                retryable=False,
                origin=ErrorOrigin.NODE,
                trace_id="trace-1",
            )
        ],
        metrics={"elapsed_ms": 12.5},
    )

    restored = from_msgpack(to_msgpack(result), NodeResultModel)

    assert restored == result
    assert restored.outputs[0].opaque_handle["table_name"] == "stg_node-1_output"
    assert restored.errors[0].error_code == "VALIDATION_ERROR"


def test_node_task_and_result_msgpack_round_trip() -> None:
    task = NodeTaskModel(
        workflow_run_id="run-1",
        workflow_process_id="process-1",
        process_generation=1,
        node_run_id="node-run-1",
        node_instance_id="source",
        node_type="core.source",
        node_version="1.0",
        attempt=1,
        input_refs=[],
        config={"rows": 3},
        timeout_seconds=60,
    )
    result = NodeTaskResultModel(
        task_id=task.task_id,
        node_run_id=task.node_run_id,
        attempt=task.attempt,
        executor_id="executor-1",
        process_generation=task.process_generation,
        status=NodeResultStatus.SUCCEEDED,
        output_refs=[],
    )

    restored_task = from_msgpack(to_msgpack(task), NodeTaskModel)
    restored_result = from_msgpack(to_msgpack(result), NodeTaskResultModel)

    assert restored_task == task
    assert restored_result == result
    assert restored_result.task_id == task.task_id


def test_node_task_cancel_request_payload_msgpack_round_trip() -> None:
    payload = NodeTaskCancelRequestPayload(task_id="task-1")

    restored = from_msgpack(to_msgpack(payload), NodeTaskCancelRequestPayload)

    assert restored == payload
    assert restored.reason == "WORKFLOW_CANCEL_REQUESTED"


def test_protocol_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        FieldSchemaModel(
            field_id="field-1",
            name="amount",
            data_type="number",
            nullable=False,
            ordinal=0,
            unexpected=True,
        )
