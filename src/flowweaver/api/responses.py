from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from flowweaver.api.runtime_model_responses import runtime_model_to_jsonable
from flowweaver.api.table_ref_responses import table_ref_to_jsonable
from flowweaver.common.ids import new_id
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
    runtime_model_payload = runtime_model_to_jsonable(value)
    if runtime_model_payload is not None:
        return runtime_model_payload
    if isinstance(value, TableRefModel):
        return table_ref_to_jsonable(value)
    return value
