from __future__ import annotations

from datetime import datetime
from typing import Any

from workflow_platform.protocols.base import StrictModel


class APIErrorModel(StrictModel):
    error_code: str
    message: str
    details: dict[str, Any] = {}
    retryable: bool = False


class APIResponseModel(StrictModel):
    ok: bool
    data: Any
    error: APIErrorModel | None
    request_id: str


class WorkflowCreateRequest(StrictModel):
    name: str
    definition: dict[str, Any]


class WorkflowUpdateRequest(StrictModel):
    name: str | None = None
    definition: dict[str, Any] | None = None


class WorkflowDefinitionData(StrictModel):
    workflow_id: str
    name: str
    version: int
    definition: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WorkflowRunData(StrictModel):
    workflow_run_id: str
    workflow_id: str
    workflow_version: int
    status: str
    input_snapshot_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error: dict[str, Any] | None
