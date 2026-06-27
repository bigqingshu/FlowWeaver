from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from flowweaver.protocols.base import StrictModel
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)


class FieldSchemaModel(StrictModel):
    field_id: str
    name: str
    data_type: str
    nullable: bool
    ordinal: int


class TableRefModel(StrictModel):
    table_ref_id: str
    role: TableRole
    storage_kind: TableStorageKind
    scope: TableScope
    mutability: TableMutability

    provider_id: str
    resource_profile_id: str | None = None
    mount_id: str | None = None
    logical_table_id: str
    opaque_handle: dict[str, Any]

    schema_: list[FieldSchemaModel] = Field(alias="schema")
    schema_fingerprint: str
    version: int
    capabilities: set[str]

    lifecycle_status: LifecycleStatus
    created_by_workflow_run_id: str
    created_by_node_run_id: str
    created_at: datetime

    @property
    def schema(self) -> list[FieldSchemaModel]:
        return self.schema_
