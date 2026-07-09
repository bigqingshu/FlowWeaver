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
from flowweaver.engine.runtime_table_rows import (
    runtime_insert_rows_statement as _runtime_insert_rows_statement,
)
from flowweaver.engine.runtime_table_sql import (
    order_clause as _order_clause,
)
from flowweaver.engine.runtime_table_sql import (
    quote_identifier as _quote_identifier,
)
from flowweaver.engine.runtime_table_sql import (
    schema_fingerprint as schema_fingerprint,
)
from flowweaver.engine.runtime_table_sql import (
    selected_columns as _selected_columns,
)
from flowweaver.engine.runtime_table_sql import (
    sqlite_type as _sqlite_type,
)
from flowweaver.engine.runtime_table_sql import (
    table_location as _table_location,
)
from flowweaver.engine.runtime_table_sql import (
    where_clause as _where_clause,
)
from flowweaver.engine.table_provider_protocol import TableProvider as TableProvider
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableRole,
)
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
        _, table_name = _table_location(table_ref)
        with self._connect(table_ref) as connection:
            return int(
                connection.execute(
                    f"SELECT COUNT(*) FROM {_quote_identifier(table_name)}"
                ).fetchone()[0]
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
        if offset < 0:
            raise ValueError("offset must be non-negative")
        if limit < 0:
            raise ValueError("limit must be non-negative")
        _, table_name = _table_location(table_ref)
        selected_columns = _selected_columns(table_ref, columns)
        where_clause, parameters = _where_clause(table_ref, filters)
        order_clause = _order_clause(table_ref, order_by)
        selected_sql = ", ".join(
            _quote_identifier(column) for column in selected_columns
        )
        query = (
            f"SELECT {selected_sql} "
            f"FROM {_quote_identifier(table_name)}"
            f"{where_clause}{order_clause} LIMIT ? OFFSET ?"
        )
        with self._connect(table_ref) as connection:
            cursor = connection.execute(query, [*parameters, limit, offset])
            return [dict(row) for row in cursor.fetchall()]

    def create_table(self, table_ref: TableRefModel) -> None:
        _validate_runtime_table_ref(table_ref, provider_id=self.provider_id)
        _, table_name = _table_location(table_ref)
        columns = ", ".join(
            f"{_quote_identifier(field.name)} {_sqlite_type(field.data_type)}"
            for field in table_ref.schema
        )
        if not columns:
            raise ValueError("runtime tables require at least one schema field")
        with self._connect(table_ref) as connection:
            connection.execute(
                f"CREATE TABLE IF NOT EXISTS "
                f"{_quote_identifier(table_name)} ({columns})"
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
        _, table_name = _table_location(table_ref)
        with self._connect(table_ref) as connection:
            connection.execute(f"DROP TABLE IF EXISTS {_quote_identifier(table_name)}")

    def publish_staging(
        self,
        staging_ref: TableRefModel,
        published_ref: TableRefModel,
    ) -> None:
        if staging_ref.lifecycle_status != LifecycleStatus.STAGING:
            raise ValueError("publish_staging requires a STAGING source")
        if published_ref.lifecycle_status != LifecycleStatus.PUBLISHED:
            raise ValueError("publish_staging requires a PUBLISHED target")
        staging_database, staging_table = _table_location(staging_ref)
        published_database, published_table = _table_location(published_ref)
        if staging_database != published_database:
            raise ValueError(
                "staging and published tables must share a runtime database"
            )
        if staging_ref.schema_fingerprint != published_ref.schema_fingerprint:
            raise ValueError("published table schema must match staging schema")
        quoted_columns = ", ".join(
            _quote_identifier(field.name) for field in staging_ref.schema
        )
        with self._connect(staging_ref) as connection:
            connection.execute("BEGIN")
            connection.execute(
                f"DROP TABLE IF EXISTS {_quote_identifier(published_table)}"
            )
            self._create_table_on_connection(connection, published_ref)
            connection.execute(
                f"INSERT INTO {_quote_identifier(published_table)} "
                f"({quoted_columns}) "
                f"SELECT {quoted_columns} FROM {_quote_identifier(staging_table)}"
            )
            connection.execute("COMMIT")

    def _create_table_on_connection(
        self,
        connection: sqlite3.Connection,
        table_ref: TableRefModel,
    ) -> None:
        _, table_name = _table_location(table_ref)
        columns = ", ".join(
            f"{_quote_identifier(field.name)} {_sqlite_type(field.data_type)}"
            for field in table_ref.schema
        )
        connection.execute(
            f"CREATE TABLE {_quote_identifier(table_name)} ({columns})"
        )

    def _connect(self, table_ref: TableRefModel) -> sqlite3.Connection:
        return _connect_runtime_table(
            table_ref,
            provider_id=self.provider_id,
            busy_timeout_ms=self._busy_timeout_ms,
        )
