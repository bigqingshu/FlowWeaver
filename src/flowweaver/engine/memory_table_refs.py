from __future__ import annotations

from collections.abc import Sequence

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_table_provider import schema_fingerprint
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

MEMORY_PROVIDER_ID = "memory"


def memory_table_ref(
    *,
    provider_id: str,
    workflow_run_id: str,
    node_run_id: str,
    logical_table_id: str,
    schema: Sequence[FieldSchemaModel],
    role: TableRole,
    version: int,
) -> tuple[str, TableRefModel]:
    schema_copy = list(schema)
    memory_id = new_id()
    return memory_id, TableRefModel(
        table_ref_id=new_id(),
        role=role,
        storage_kind=TableStorageKind.MEMORY,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.WORKING_MUTABLE,
        provider_id=provider_id,
        logical_table_id=logical_table_id,
        opaque_handle={"memory_table_id": memory_id},
        schema=schema_copy,
        schema_fingerprint=schema_fingerprint(schema_copy),
        version=version,
        capabilities={"READ"},
        lifecycle_status=LifecycleStatus.ACTIVE,
        created_by_workflow_run_id=workflow_run_id,
        created_by_node_run_id=node_run_id,
        created_at=utc_now(),
    )


def memory_table_id(table_ref: TableRefModel) -> str:
    resolved_memory_table_id = table_ref.opaque_handle.get("memory_table_id")
    if (
        not isinstance(resolved_memory_table_id, str)
        or not resolved_memory_table_id
    ):
        raise ValueError("table_ref opaque_handle.memory_table_id is required")
    return resolved_memory_table_id


def validate_memory_table_ref(
    table_ref: TableRefModel,
    *,
    provider_id: str,
) -> None:
    if table_ref.provider_id != provider_id:
        raise ValueError("table_ref belongs to a different provider")
    if table_ref.storage_kind != TableStorageKind.MEMORY:
        raise ValueError("MemoryTableProvider only supports MEMORY")
    if table_ref.lifecycle_status in {
        LifecycleStatus.RELEASABLE,
        LifecycleStatus.RELEASED,
        LifecycleStatus.RETIRED,
        LifecycleStatus.ORPHANED,
    }:
        raise ValueError("memory table is not available")
