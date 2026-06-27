from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from flowweaver.common.ids import new_id
from flowweaver.engine.runtime_store import (
    NodeRun,
    RuntimeEventLog,
    WorkflowDefinition,
    WorkflowProcess,
    WorkflowRevision,
    WorkflowRun,
)


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
            "input_snapshot_id": value.input_snapshot_id,
            "started_at": value.started_at.isoformat() if value.started_at else None,
            "finished_at": value.finished_at.isoformat() if value.finished_at else None,
            "error": value.error,
        }
    if isinstance(value, WorkflowProcess):
        return {
            "process_id": value.process_id,
            "workflow_run_id": value.workflow_run_id,
            "os_pid": value.os_pid,
            "status": value.status,
            "started_at": value.started_at.isoformat(),
            "last_heartbeat_at": (
                value.last_heartbeat_at.isoformat()
                if value.last_heartbeat_at
                else None
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
    return value
