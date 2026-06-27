from __future__ import annotations

from datetime import datetime
from typing import Any

from flowweaver.protocols.base import StrictModel


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


class WorkflowValidateRequest(StrictModel):
    definition: dict[str, Any]


class WorkflowUpdateRequest(StrictModel):
    name: str | None = None
    definition: dict[str, Any] | None = None


class WorkflowDefinitionData(StrictModel):
    workflow_id: str
    name: str
    revision_id: str
    version: int
    definition_hash: str
    definition: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


class WorkflowSummaryView(StrictModel):
    workflow_id: str
    name: str
    current_revision_id: str
    version: int
    status: str
    updated_at: datetime


class WorkflowDetailView(WorkflowDefinitionData):
    pass


class WorkflowRevisionView(StrictModel):
    revision_id: str
    workflow_id: str
    version: int
    definition_hash: str
    definition: dict[str, Any]
    created_at: datetime
    created_by: str | None


class WorkflowRunData(StrictModel):
    workflow_run_id: str
    workflow_id: str
    revision_id: str | None
    workflow_version: int
    definition_hash: str | None
    status: str
    state_version: int
    input_snapshot_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error: dict[str, Any] | None


class WorkflowRunView(WorkflowRunData):
    pass
