from __future__ import annotations

from typing import Any

from flowweaver.protocols.enums import LifecycleStatus, TableRole, TableStorageKind
from flowweaver.protocols.table_ref import TableRefModel


def table_ref_summary_to_jsonable(
    value: TableRefModel,
    *,
    source_node_instance_id: str | None = None,
) -> dict[str, Any]:
    can_read_rows = _table_ref_can_read_rows(value)
    output_slot = _table_ref_output_slot(value)
    return {
        "table_ref_id": value.table_ref_id,
        "workflow_run_id": value.created_by_workflow_run_id,
        "node_run_id": value.created_by_node_run_id,
        "source_node_run_id": value.created_by_node_run_id,
        "source_node_instance_id": source_node_instance_id,
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
        "schema_fingerprint": value.schema_fingerprint,
        "version": value.version,
        "capabilities": sorted(value.capabilities),
        "lifecycle_status": value.lifecycle_status.value,
        "created_at": value.created_at.isoformat(),
    }


def table_ref_to_jsonable(
    value: TableRefModel,
    *,
    source_node_instance_id: str | None = None,
) -> dict[str, Any]:
    payload = table_ref_summary_to_jsonable(
        value,
        source_node_instance_id=source_node_instance_id,
    )
    payload["schema"] = [field.model_dump(mode="json") for field in value.schema]
    can_read_rows = payload["can_read_rows"]
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
        LifecycleStatus.RELEASABLE,
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
