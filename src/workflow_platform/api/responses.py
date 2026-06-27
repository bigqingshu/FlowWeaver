from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from workflow_platform.common.ids import new_id
from workflow_platform.engine.runtime_store import WorkflowDefinition, WorkflowRun


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
            "version": value.version,
            "definition": value.definition,
            "created_at": value.created_at.isoformat(),
            "updated_at": value.updated_at.isoformat(),
        }
    if isinstance(value, WorkflowRun):
        return {
            "workflow_run_id": value.workflow_run_id,
            "workflow_id": value.workflow_id,
            "workflow_version": value.workflow_version,
            "status": value.status,
            "input_snapshot_id": value.input_snapshot_id,
            "started_at": value.started_at.isoformat() if value.started_at else None,
            "finished_at": value.finished_at.isoformat() if value.finished_at else None,
            "error": value.error,
        }
    return value
