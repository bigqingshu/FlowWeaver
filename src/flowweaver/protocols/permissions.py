from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.protocols.base import StrictModel
from flowweaver.protocols.enums import AuditLevel, PermissionAction


class PermissionScopeModel(StrictModel):
    action: PermissionAction
    resource_type: str
    resource_id: str
    fields: list[str] | None = None
    write_mode: str | None = None
    constraints: dict[str, Any] = {}


class PermissionRequestModel(StrictModel):
    request_id: str = Field(default_factory=new_id)
    workflow_run_id: str
    node_run_id: str
    node_instance_id: str
    node_type: str
    scopes: list[PermissionScopeModel]
    requested_at: datetime = Field(default_factory=utc_now)
    reason: str | None = None
    audit_level: AuditLevel = AuditLevel.STANDARD


class PermissionGrantModel(StrictModel):
    permission_handle_id: str = Field(default_factory=new_id)
    request_id: str
    workflow_run_id: str
    node_run_id: str
    scopes: list[PermissionScopeModel]
    granted: bool
    issued_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    denial_reason: str | None = None
    audit_level: AuditLevel = AuditLevel.STANDARD


class AuditEventModel(StrictModel):
    event_id: str = Field(default_factory=new_id)
    event_type: str
    timestamp: datetime = Field(default_factory=utc_now)
    workflow_run_id: str | None = None
    node_run_id: str | None = None
    subject_type: str
    subject_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    action: PermissionAction | str | None = None
    result: str
    audit_level: AuditLevel = AuditLevel.STANDARD
    summary: dict[str, Any] = {}
