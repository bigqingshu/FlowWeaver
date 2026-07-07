from __future__ import annotations

from collections.abc import MutableMapping, Sequence
from dataclasses import dataclass
from threading import RLock
from typing import Any

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


@dataclass
class _MemoryTable:
    schema: list[FieldSchemaModel]
    rows: list[dict[str, Any]]


_GLOBAL_MEMORY_TABLES: dict[str, _MemoryTable] = {}
_GLOBAL_MEMORY_TABLES_LOCK = RLock()


class MemoryTableProvider:
    provider_id = MEMORY_PROVIDER_ID

    def __init__(
        self,
        tables: MutableMapping[str, _MemoryTable] | None = None,
        lock: Any | None = None,
    ) -> None:
        self._tables = tables if tables is not None else _GLOBAL_MEMORY_TABLES
        self._lock = lock if lock is not None else _GLOBAL_MEMORY_TABLES_LOCK

    def create_memory_table(
        self,
        *,
        workflow_run_id: str,
        node_run_id: str,
        logical_table_id: str,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
        role: TableRole = TableRole.AUXILIARY,
        version: int = 1,
    ) -> TableRefModel:
        schema_copy = list(schema)
        memory_table_id = new_id()
        table_ref = TableRefModel(
            table_ref_id=new_id(),
            role=role,
            storage_kind=TableStorageKind.MEMORY,
            scope=TableScope.WORKFLOW_SCOPE,
            mutability=TableMutability.WORKING_MUTABLE,
            provider_id=self.provider_id,
            logical_table_id=logical_table_id,
            opaque_handle={"memory_table_id": memory_table_id},
            schema=schema_copy,
            schema_fingerprint=schema_fingerprint(schema_copy),
            version=version,
            capabilities={"READ"},
            lifecycle_status=LifecycleStatus.ACTIVE,
            created_by_workflow_run_id=workflow_run_id,
            created_by_node_run_id=node_run_id,
            created_at=utc_now(),
        )
        cleaned_rows = _normalize_rows(schema_copy, rows)
        with self._lock:
            self._tables[memory_table_id] = _MemoryTable(
                schema=schema_copy,
                rows=cleaned_rows,
            )
        return table_ref

    def get_schema(self, table_ref: TableRefModel) -> list[FieldSchemaModel]:
        return list(self._load_table(table_ref).schema)

    def count_rows(self, table_ref: TableRefModel) -> int:
        return len(self._load_table(table_ref).rows)

    def read_rows(
        self,
        table_ref: TableRefModel,
        offset: int,
        limit: int,
        columns: list[str] | None = None,
        order_by: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        if offset < 0:
            raise ValueError("offset must be non-negative")
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if filters:
            raise ValueError("MemoryTableProvider does not support filters yet")
        table = self._load_table(table_ref)
        selected_columns = _selected_columns(table_ref, columns)
        rows = _ordered_rows(table_ref, list(table.rows), order_by)
        return [
            {column: row.get(column) for column in selected_columns}
            for row in rows[offset : offset + limit]
        ]

    def create_table(self, table_ref: TableRefModel) -> None:
        self._validate_ref(table_ref)
        memory_table_id = _memory_table_id(table_ref)
        with self._lock:
            self._tables.setdefault(
                memory_table_id,
                _MemoryTable(schema=list(table_ref.schema), rows=[]),
            )

    def drop_table(self, table_ref: TableRefModel) -> None:
        self._validate_ref(table_ref)
        memory_table_id = _memory_table_id(table_ref)
        with self._lock:
            self._tables.pop(memory_table_id, None)

    def publish_staging(
        self,
        staging_ref: TableRefModel,
        published_ref: TableRefModel,
    ) -> None:
        raise ValueError("MemoryTableProvider does not support publish_staging")

    def _load_table(self, table_ref: TableRefModel) -> _MemoryTable:
        self._validate_ref(table_ref)
        memory_table_id = _memory_table_id(table_ref)
        with self._lock:
            table = self._tables.get(memory_table_id)
            if table is None:
                raise ValueError("memory table is not available")
            return _MemoryTable(
                schema=list(table.schema),
                rows=[dict(row) for row in table.rows],
            )

    def _validate_ref(self, table_ref: TableRefModel) -> None:
        if table_ref.provider_id != self.provider_id:
            raise ValueError("table_ref belongs to a different provider")
        if table_ref.storage_kind != TableStorageKind.MEMORY:
            raise ValueError("MemoryTableProvider only supports MEMORY")
        if table_ref.lifecycle_status in {
            LifecycleStatus.RELEASED,
            LifecycleStatus.RETIRED,
            LifecycleStatus.ORPHANED,
        }:
            raise ValueError("memory table is not available")


def _memory_table_id(table_ref: TableRefModel) -> str:
    memory_table_id = table_ref.opaque_handle.get("memory_table_id")
    if not isinstance(memory_table_id, str) or not memory_table_id:
        raise ValueError("table_ref opaque_handle.memory_table_id is required")
    return memory_table_id


def _normalize_rows(
    schema: Sequence[FieldSchemaModel],
    rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    schema_columns = [field.name for field in schema]
    schema_column_set = set(schema_columns)
    cleaned_rows: list[dict[str, Any]] = []
    for row in rows:
        unknown_columns = set(row) - schema_column_set
        if unknown_columns:
            raise ValueError(
                "row contains columns not declared in schema: "
                f"{sorted(unknown_columns)}"
            )
        cleaned_rows.append({column: row.get(column) for column in schema_columns})
    return cleaned_rows


def _selected_columns(
    table_ref: TableRefModel,
    columns: list[str] | None,
) -> list[str]:
    schema_columns = [field.name for field in table_ref.schema]
    if columns is None:
        return schema_columns
    unknown_columns = set(columns) - set(schema_columns)
    if unknown_columns:
        raise ValueError(f"unknown columns requested: {sorted(unknown_columns)}")
    return columns


def _ordered_rows(
    table_ref: TableRefModel,
    rows: list[dict[str, Any]],
    order_by: list[str] | None,
) -> list[dict[str, Any]]:
    if not order_by:
        return rows
    schema_columns = {field.name for field in table_ref.schema}
    ordered = rows
    for item in reversed(order_by):
        reverse = item.startswith("-")
        field = item[1:] if reverse else item
        if field not in schema_columns:
            raise ValueError(f"unknown order_by field: {field}")
        ordered = sorted(
            ordered,
            key=lambda row: (row.get(field) is None, row.get(field)),
            reverse=reverse,
        )
    return ordered
