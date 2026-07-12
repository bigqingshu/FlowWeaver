from __future__ import annotations

from collections.abc import Iterable, MutableMapping, Sequence
from typing import Any

from flowweaver.engine.memory_table_building import (
    build_memory_table_from_batches as _build_memory_table_from_batches,
)
from flowweaver.engine.memory_table_refs import (
    MEMORY_PROVIDER_ID as MEMORY_PROVIDER_ID,
)
from flowweaver.engine.memory_table_refs import memory_table_id as _memory_table_id
from flowweaver.engine.memory_table_refs import memory_table_ref as _memory_table_ref
from flowweaver.engine.memory_table_refs import (
    validate_memory_table_ref as _validate_memory_table_ref,
)
from flowweaver.engine.memory_table_rows import ordered_rows as _ordered_rows
from flowweaver.engine.memory_table_rows import selected_columns as _selected_columns
from flowweaver.engine.memory_table_storage import (
    GLOBAL_MEMORY_TABLES as _GLOBAL_MEMORY_TABLES,
)
from flowweaver.engine.memory_table_storage import (
    GLOBAL_MEMORY_TABLES_LOCK as _GLOBAL_MEMORY_TABLES_LOCK,
)
from flowweaver.engine.memory_table_storage import MemoryTable as _MemoryTable
from flowweaver.protocols.enums import TableRole, TableStorageKind
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


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
        return self.create_memory_table_from_batches(
            workflow_run_id=workflow_run_id,
            node_run_id=node_run_id,
            logical_table_id=logical_table_id,
            schema=schema,
            row_batches=(rows,),
            role=role,
            version=version,
        )

    def create_memory_table_from_batches(
        self,
        *,
        workflow_run_id: str,
        node_run_id: str,
        logical_table_id: str,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
        role: TableRole = TableRole.AUXILIARY,
        version: int = 1,
    ) -> TableRefModel:
        memory_table_id, table_ref = _memory_table_ref(
            provider_id=self.provider_id,
            workflow_run_id=workflow_run_id,
            node_run_id=node_run_id,
            logical_table_id=logical_table_id,
            schema=schema,
            role=role,
            version=version,
        )
        memory_table = _build_memory_table_from_batches(
            table_ref.schema,
            row_batches,
        )
        with self._lock:
            self._tables[memory_table_id] = memory_table
        return table_ref

    def replace_rows(
        self,
        table_ref: TableRefModel,
        rows: Sequence[dict[str, Any]],
    ) -> None:
        self.replace_row_batches(table_ref, (rows,))

    def replace_row_batches(
        self,
        table_ref: TableRefModel,
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> None:
        self._validate_ref(table_ref)
        memory_table_id = _memory_table_id(table_ref)
        memory_table = _build_memory_table_from_batches(
            table_ref.schema,
            row_batches,
        )
        with self._lock:
            if memory_table_id not in self._tables:
                raise ValueError("memory table is not available")
            self._tables[memory_table_id] = memory_table

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
        if table_ref.provider_id != self.provider_id:
            raise ValueError("table_ref belongs to a different provider")
        if table_ref.storage_kind != TableStorageKind.MEMORY:
            raise ValueError("MemoryTableProvider only supports MEMORY")
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
        _validate_memory_table_ref(table_ref, provider_id=self.provider_id)
