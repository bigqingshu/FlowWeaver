from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

SQLITE_RUNTIME_PROVIDER_ID = "sqlite_runtime"


class TableProvider(Protocol):
    provider_id: str

    def get_schema(self, table_ref: TableRefModel) -> list[FieldSchemaModel]:
        ...

    def count_rows(self, table_ref: TableRefModel) -> int:
        ...

    def read_rows(
        self,
        table_ref: TableRefModel,
        offset: int,
        limit: int,
        columns: list[str] | None = None,
        order_by: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        ...

    def create_table(self, table_ref: TableRefModel) -> None:
        ...

    def drop_table(self, table_ref: TableRefModel) -> None:
        ...

    def publish_staging(
        self,
        staging_ref: TableRefModel,
        published_ref: TableRefModel,
    ) -> None:
        ...


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
        return self._runtime_root / f"{_identifier_token(workflow_run_id)}.db"

    def create_staging_table(
        self,
        *,
        workflow_run_id: str,
        node_run_id: str,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
    ) -> TableRefModel:
        table_name = (
            f"stg_{_identifier_token(node_run_id)}_{_identifier_token(output_name)}"
        )
        table_ref = TableRefModel(
            table_ref_id=new_id(),
            role=TableRole.CURRENT,
            storage_kind=TableStorageKind.RUNTIME_SQL,
            scope=TableScope.WORKFLOW_SCOPE,
            mutability=TableMutability.WORKING_MUTABLE,
            provider_id=self.provider_id,
            logical_table_id=output_name,
            opaque_handle={
                "database_path": self.database_path_for_run(workflow_run_id).as_posix(),
                "table_name": table_name,
            },
            schema=list(schema),
            schema_fingerprint=schema_fingerprint(schema),
            version=1,
            capabilities={"READ", "APPEND"},
            lifecycle_status=LifecycleStatus.STAGING,
            created_by_workflow_run_id=workflow_run_id,
            created_by_node_run_id=node_run_id,
            created_at=utc_now(),
        )
        self.create_table(table_ref)
        return table_ref

    def published_ref_from_staging(
        self,
        staging_ref: TableRefModel,
        *,
        version: int | None = None,
    ) -> TableRefModel:
        database_path, staging_table = _table_location(staging_ref)
        published_version = staging_ref.version + 1 if version is None else version
        published_table = (
            f"pub_{_identifier_token(staging_table)}_v{published_version}"
        )
        return TableRefModel(
            table_ref_id=new_id(),
            role=staging_ref.role,
            storage_kind=staging_ref.storage_kind,
            scope=staging_ref.scope,
            mutability=TableMutability.PUBLISHED_IMMUTABLE,
            provider_id=self.provider_id,
            resource_profile_id=staging_ref.resource_profile_id,
            mount_id=staging_ref.mount_id,
            logical_table_id=staging_ref.logical_table_id,
            opaque_handle={
                "database_path": database_path.as_posix(),
                "table_name": published_table,
            },
            schema=staging_ref.schema,
            schema_fingerprint=staging_ref.schema_fingerprint,
            version=published_version,
            capabilities={"READ"},
            lifecycle_status=LifecycleStatus.PUBLISHED,
            created_by_workflow_run_id=staging_ref.created_by_workflow_run_id,
            created_by_node_run_id=staging_ref.created_by_node_run_id,
            created_at=utc_now(),
        )

    def get_schema(self, table_ref: TableRefModel) -> list[FieldSchemaModel]:
        self._validate_ref(table_ref)
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
        self._validate_ref(table_ref)
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
        if not rows:
            return
        if (
            table_ref.lifecycle_status != LifecycleStatus.STAGING
            or table_ref.mutability != TableMutability.WORKING_MUTABLE
        ):
            raise ValueError("only STAGING working tables can be written")
        _, table_name = _table_location(table_ref)
        schema_columns = [field.name for field in table_ref.schema]
        for row in rows:
            unknown_columns = set(row) - set(schema_columns)
            if unknown_columns:
                raise ValueError(
                    f"row contains columns not declared in schema: "
                    f"{sorted(unknown_columns)}"
                )
        placeholders = ", ".join("?" for _ in schema_columns)
        quoted_columns = ", ".join(
            _quote_identifier(column) for column in schema_columns
        )
        values = [
            [row.get(column) for column in schema_columns]
            for row in rows
        ]
        with self._connect(table_ref) as connection:
            connection.executemany(
                (
                    f"INSERT INTO {_quote_identifier(table_name)} "
                    f"({quoted_columns}) VALUES ({placeholders})"
                ),
                values,
            )

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
        self._validate_ref(table_ref)
        database_path, _ = _table_location(table_ref)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {self._busy_timeout_ms}")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    def _validate_ref(self, table_ref: TableRefModel) -> None:
        if table_ref.provider_id != self.provider_id:
            raise ValueError("table_ref belongs to a different provider")
        if table_ref.storage_kind != TableStorageKind.RUNTIME_SQL:
            raise ValueError("SQLiteRuntimeTableProvider only supports RUNTIME_SQL")


def schema_fingerprint(schema: Sequence[FieldSchemaModel]) -> str:
    payload = [
        field.model_dump(mode="json", by_alias=True)
        for field in sorted(schema, key=lambda item: item.ordinal)
    ]
    return sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _table_location(table_ref: TableRefModel) -> tuple[Path, str]:
    database_path = table_ref.opaque_handle.get("database_path")
    table_name = table_ref.opaque_handle.get("table_name")
    if not isinstance(database_path, str) or not database_path:
        raise ValueError("table_ref opaque_handle.database_path is required")
    if not isinstance(table_name, str) or not table_name:
        raise ValueError("table_ref opaque_handle.table_name is required")
    return Path(database_path), table_name


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


def _where_clause(
    table_ref: TableRefModel,
    filters: list[dict[str, Any]] | None,
) -> tuple[str, list[Any]]:
    if not filters:
        return "", []
    schema_columns = {field.name for field in table_ref.schema}
    clauses: list[str] = []
    parameters: list[Any] = []
    for item in filters:
        field = item.get("field")
        operator = item.get("operator", "eq")
        if field not in schema_columns:
            raise ValueError(f"unknown filter field: {field}")
        sql_operator = _FILTER_OPERATORS.get(str(operator).lower())
        if sql_operator is None:
            raise ValueError(f"unsupported filter operator: {operator}")
        clauses.append(f"{_quote_identifier(str(field))} {sql_operator} ?")
        parameters.append(item.get("value"))
    return f" WHERE {' AND '.join(clauses)}", parameters


def _order_clause(
    table_ref: TableRefModel,
    order_by: list[str] | None,
) -> str:
    if not order_by:
        return ""
    schema_columns = {field.name for field in table_ref.schema}
    parts: list[str] = []
    for item in order_by:
        direction = "ASC"
        field = item
        if item.startswith("-"):
            direction = "DESC"
            field = item[1:]
        if field not in schema_columns:
            raise ValueError(f"unknown order_by field: {field}")
        parts.append(f"{_quote_identifier(field)} {direction}")
    return f" ORDER BY {', '.join(parts)}"


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _identifier_token(value: str) -> str:
    token = re.sub(r"[^0-9A-Za-z_]+", "_", value).strip("_")
    if not token:
        return "value"
    if token[0].isdigit():
        return f"_{token}"
    return token


def _sqlite_type(data_type: str) -> str:
    normalized = data_type.upper()
    if normalized in {"INT", "INTEGER", "BOOL", "BOOLEAN"}:
        return "INTEGER"
    if normalized in {"FLOAT", "REAL", "DOUBLE", "NUMBER", "NUMERIC", "DECIMAL"}:
        return "REAL"
    if normalized in {"TEXT", "STRING", "STR"}:
        return "TEXT"
    return "TEXT"


_FILTER_OPERATORS = {
    "eq": "=",
    "=": "=",
    "==": "=",
    "ne": "!=",
    "!=": "!=",
    "gt": ">",
    ">": ">",
    "gte": ">=",
    ">=": ">=",
    "lt": "<",
    "<": "<",
    "lte": "<=",
    "<=": "<=",
}
