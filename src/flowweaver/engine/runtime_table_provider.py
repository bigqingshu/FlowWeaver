from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from flowweaver.engine import runtime_table_refs as _runtime_table_refs
from flowweaver.engine.runtime_table_connections import (
    connect_runtime_table as _connect_runtime_table,
)
from flowweaver.engine.runtime_table_connections import (
    validate_runtime_table_ref as _validate_runtime_table_ref,
)
from flowweaver.engine.runtime_table_reading import (
    count_runtime_rows as _count_runtime_rows,
)
from flowweaver.engine.runtime_table_reading import (
    read_runtime_rows as _read_runtime_rows,
)
from flowweaver.engine.runtime_table_rows import (
    runtime_insert_rows_statement as _runtime_insert_rows_statement,
)
from flowweaver.engine.runtime_table_sql import (
    schema_fingerprint as schema_fingerprint,
)
from flowweaver.engine.runtime_table_writing import (
    create_runtime_table_on_connection as _create_runtime_table_on_connection,
)
from flowweaver.engine.runtime_table_writing import (
    drop_runtime_table_on_connection as _drop_runtime_table_on_connection,
)
from flowweaver.engine.runtime_table_writing import (
    publish_runtime_staging_on_connection as _publish_runtime_staging_on_connection,
)
from flowweaver.engine.runtime_table_writing import (
    runtime_table_columns_sql as _runtime_table_columns_sql,
)
from flowweaver.engine.table_provider_protocol import TableProvider as TableProvider
from flowweaver.protocols.enums import TableRole
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

SQLITE_RUNTIME_PROVIDER_ID = "sqlite_runtime"


class SQLiteRuntimeTableProvider:
    provider_id = SQLITE_RUNTIME_PROVIDER_ID

    def __init__(
        self,
        runtime_root: str | Path = Path("runtime") / "workflow_runs",
        *,
        busy_timeout_ms: int = 5000,
    ) -> None:
        self._runtime_root = Path(runtime_root)
        self._busy_timeout_ms = busy_timeout_ms

    def database_path_for_run(self, workflow_run_id: str) -> Path:
        return _runtime_table_refs.runtime_database_path(
            self._runtime_root,
            workflow_run_id,
        )

    def create_staging_table(
        self,
        *,
        workflow_run_id: str,
        node_run_id: str,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        role: TableRole = TableRole.CURRENT,
        version: int = 1,
    ) -> TableRefModel:
        table_ref = _runtime_table_refs.runtime_staging_table_ref(
            runtime_root=self._runtime_root,
            provider_id=self.provider_id,
            workflow_run_id=workflow_run_id,
            node_run_id=node_run_id,
            output_name=output_name,
            schema=schema,
            role=role,
            version=version,
        )
        self.create_table(table_ref)
        return table_ref

    def published_ref_from_staging(
        self,
        staging_ref: TableRefModel,
        *,
        version: int | None = None,
    ) -> TableRefModel:
        return _runtime_table_refs.published_runtime_table_ref_from_staging(
            staging_ref,
            provider_id=self.provider_id,
            version=version,
        )

    def get_schema(self, table_ref: TableRefModel) -> list[FieldSchemaModel]:
        _validate_runtime_table_ref(table_ref, provider_id=self.provider_id)
        return list(table_ref.schema)

    def count_rows(self, table_ref: TableRefModel) -> int:
        return _count_runtime_rows(
            table_ref,
            provider_id=self.provider_id,
            busy_timeout_ms=self._busy_timeout_ms,
        )

    def read_rows(
        self,
        table_ref: TableRefModel,
        offset: int,
        limit: int,
        columns: list[str] | None = None,
        order_by: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        return _read_runtime_rows(
            table_ref,
            provider_id=self.provider_id,
            busy_timeout_ms=self._busy_timeout_ms,
            offset=offset,
            limit=limit,
            columns=columns,
            order_by=order_by,
            filters=filters,
        )

    def create_table(self, table_ref: TableRefModel) -> None:
        _validate_runtime_table_ref(table_ref, provider_id=self.provider_id)
        if not _runtime_table_columns_sql(table_ref.schema):
            raise ValueError("runtime tables require at least one schema field")
        with self._connect(table_ref) as connection:
            _create_runtime_table_on_connection(
                connection,
                table_ref,
                if_not_exists=True,
            )

    def insert_rows(
        self,
        table_ref: TableRefModel,
        rows: Sequence[dict[str, Any]],
    ) -> None:
        statement = _runtime_insert_rows_statement(table_ref, rows)
        if statement is None:
            return
        with self._connect(table_ref) as connection:
            connection.executemany(statement.sql, statement.values)

    def drop_table(self, table_ref: TableRefModel) -> None:
        with self._connect(table_ref) as connection:
            _drop_runtime_table_on_connection(connection, table_ref)

    def publish_staging(
        self,
        staging_ref: TableRefModel,
        published_ref: TableRefModel,
    ) -> None:
        with self._connect(staging_ref) as connection:
            _publish_runtime_staging_on_connection(
                connection,
                staging_ref=staging_ref,
                published_ref=published_ref,
            )

    def _connect(self, table_ref: TableRefModel) -> sqlite3.Connection:
        return _connect_runtime_table(
            table_ref,
            provider_id=self.provider_id,
            busy_timeout_ms=self._busy_timeout_ms,
        )
