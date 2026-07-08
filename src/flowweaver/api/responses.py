from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from flowweaver.common.ids import new_id
from flowweaver.engine.runtime_store import (
    LoopIterationRun,
    LoopIterationTableRef,
    LoopRun,
    NodeRun,
    RuntimeEventLog,
    SharedPublication,
    WorkflowDefinition,
    WorkflowProcess,
    WorkflowRevision,
    WorkflowRun,
)
from flowweaver.protocols.enums import LifecycleStatus, TableRole, TableStorageKind
from flowweaver.protocols.table_ref import TableRefModel


def request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or new_id()


def ok_response(request: Request, data: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": True,
            "data": _to_jsonable(data),
            "error": None,
            "request_id": request_id(request),
        },
    )


def error_response(
    request: Request,
    *,
    error_code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
    retryable: bool = False,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "data": None,
            "error": {
                "error_code": error_code,
                "message": message,
                "details": details or {},
                "retryable": retryable,
            },
            "request_id": request_id(request),
        },
    )


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, WorkflowDefinition):
        return {
            "workflow_id": value.workflow_id,
            "name": value.name,
            "revision_id": value.revision_id,
            "version": value.version,
            "definition_hash": value.definition_hash,
            "definition": value.definition,
            "status": value.status,
            "created_at": value.created_at.isoformat(),
            "updated_at": value.updated_at.isoformat(),
        }
    if isinstance(value, WorkflowRevision):
        return {
            "revision_id": value.revision_id,
            "workflow_id": value.workflow_id,
            "version": value.version,
            "definition_hash": value.definition_hash,
            "definition": value.definition,
            "created_at": value.created_at.isoformat(),
            "created_by": value.created_by,
        }
    if isinstance(value, WorkflowRun):
        return {
            "workflow_run_id": value.workflow_run_id,
            "workflow_id": value.workflow_id,
            "revision_id": value.revision_id,
            "workflow_version": value.workflow_version,
            "definition_hash": value.definition_hash,
            "status": value.status,
            "state_version": value.state_version,
            "owner_process_id": value.owner_process_id,
            "process_generation": value.process_generation,
            "fencing_token": value.fencing_token,
            "input_snapshot_id": value.input_snapshot_id,
            "run_mode": value.run_mode,
            "trigger_source": value.trigger_source,
            "target_node_instance_id": value.target_node_instance_id,
            "started_at": value.started_at.isoformat() if value.started_at else None,
            "finished_at": value.finished_at.isoformat() if value.finished_at else None,
            "completion_reason": value.completion_reason,
            "error": value.error,
        }
    if isinstance(value, WorkflowProcess):
        return {
            "process_id": value.process_id,
            "workflow_run_id": value.workflow_run_id,
            "os_pid": value.os_pid,
            "process_generation": value.process_generation,
            "fencing_token": value.fencing_token,
            "status": value.status,
            "started_at": value.started_at.isoformat(),
            "last_heartbeat_at": (
                value.last_heartbeat_at.isoformat() if value.last_heartbeat_at else None
            ),
            "cancel_requested_at": (
                value.cancel_requested_at.isoformat()
                if value.cancel_requested_at
                else None
            ),
            "exited_at": value.exited_at.isoformat() if value.exited_at else None,
            "exit_code": value.exit_code,
            "error": value.error,
        }
    if isinstance(value, NodeRun):
        return {
            "node_run_id": value.node_run_id,
            "workflow_run_id": value.workflow_run_id,
            "node_instance_id": value.node_instance_id,
            "node_type": value.node_type,
            "status": value.status,
            "state_version": value.state_version,
            "executor_id": value.executor_id,
            "progress": value.progress,
            "current_stage": value.current_stage,
            "attempt": value.attempt,
            "started_at": value.started_at.isoformat() if value.started_at else None,
            "finished_at": value.finished_at.isoformat() if value.finished_at else None,
            "last_heartbeat": (
                value.last_heartbeat.isoformat() if value.last_heartbeat else None
            ),
            "error": value.error,
        }
    if isinstance(value, LoopRun):
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
    if isinstance(value, LoopIterationRun):
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
    if isinstance(value, LoopIterationTableRef):
        return {
            "loop_iteration_id": value.loop_iteration_id,
            "table_ref_id": value.table_ref_id,
            "role": value.role,
            "created_at": value.created_at.isoformat(),
        }
    if isinstance(value, RuntimeEventLog):
        return {
            "event_id": value.event_id,
            "sequence_number": value.sequence_number,
            "event_version": value.event_version,
            "event_type": value.event_type,
            "timestamp": value.timestamp.isoformat(),
            "workflow_run_id": value.workflow_run_id,
            "node_run_id": value.node_run_id,
            "payload": value.payload,
        }
    if isinstance(value, TableRefModel):
        return _table_ref_to_jsonable(value)
    if isinstance(value, SharedPublication):
        return {
            "publication_id": value.publication_id,
            "share_name": value.share_name,
            "publication_version": value.publication_version,
            "producer_workflow_id": value.producer_workflow_id,
            "producer_run_id": value.producer_run_id,
            "status": value.status,
            "input_snapshot_id": value.input_snapshot_id,
            "retention_policy": value.retention_policy,
            "created_at": value.created_at.isoformat(),
            "members": [
                {
                    "publication_id": member.publication_id,
                    "export_name": member.export_name,
                    "table_ref_id": member.table_ref_id,
                    "exact_table_version": member.exact_table_version,
                }
                for member in value.members
            ],
        }
    return value


def _table_ref_to_jsonable(value: TableRefModel) -> dict[str, Any]:
    can_read_rows = _table_ref_can_read_rows(value)
    output_slot = _table_ref_output_slot(value)
    payload: dict[str, Any] = {
        "table_ref_id": value.table_ref_id,
        "workflow_run_id": value.created_by_workflow_run_id,
        "node_run_id": value.created_by_node_run_id,
        "source_node_run_id": value.created_by_node_run_id,
        "role": value.role.value,
        "storage_kind": value.storage_kind.value,
        "scope": value.scope.value,
        "mutability": value.mutability.value,
        "provider_id": value.provider_id,
        "resource_profile_id": value.resource_profile_id,
        "mount_id": value.mount_id,
        "logical_table_id": value.logical_table_id,
        "output_slot": output_slot,
        "table_type": _table_ref_type(value),
        "preview_persistence": _table_ref_preview_persistence(value),
        "can_read_rows": can_read_rows,
        "supports_paged_rows": can_read_rows,
        "schema": [field.model_dump(mode="json") for field in value.schema],
        "schema_fingerprint": value.schema_fingerprint,
        "version": value.version,
        "capabilities": sorted(value.capabilities),
        "lifecycle_status": value.lifecycle_status.value,
        "created_at": value.created_at.isoformat(),
    }
    if can_read_rows:
        base_path = f"/api/v1/data/{value.table_ref_id}"
        payload["data_endpoints"] = {
            "detail": base_path,
            "schema": f"{base_path}/schema",
            "summary": f"{base_path}/summary",
            "rows": f"{base_path}/rows",
        }
    else:
        payload["data_endpoints"] = None
    return payload


def _table_ref_can_read_rows(value: TableRefModel) -> bool:
    if "READ" not in value.capabilities:
        return False
    return value.lifecycle_status not in {
        LifecycleStatus.RELEASED,
        LifecycleStatus.RETIRED,
        LifecycleStatus.ORPHANED,
    }


def _table_ref_type(value: TableRefModel) -> str:
    if value.role == TableRole.CURRENT:
        return "current_table"
    if value.storage_kind == TableStorageKind.MEMORY:
        return "memory_table"
    if value.storage_kind == TableStorageKind.RUNTIME_SQL:
        return "runtime_sql_table"
    if value.storage_kind == TableStorageKind.EXTERNAL_SQL:
        return "external_sql_table"
    return value.storage_kind.value.lower()


def _table_ref_preview_persistence(value: TableRefModel) -> str:
    if value.storage_kind == TableStorageKind.MEMORY:
        return "memory_only"
    if value.storage_kind == TableStorageKind.RUNTIME_SQL:
        return "workflow_run_sql"
    if value.storage_kind == TableStorageKind.EXTERNAL_SQL:
        return "external_source"
    return "unknown"


def _table_ref_output_slot(value: TableRefModel) -> str | None:
    output_slot = value.opaque_handle.get("output_slot")
    if isinstance(output_slot, str) and output_slot:
        return output_slot
    output_name = value.opaque_handle.get("output_name")
    if isinstance(output_name, str) and output_name:
        return output_name
    return None
