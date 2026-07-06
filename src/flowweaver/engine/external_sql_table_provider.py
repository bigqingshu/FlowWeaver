from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from flowweaver.protocols.enums import TableStorageKind
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

EXTERNAL_SQL_PROVIDER_ID = "external_sql"


class SQLiteExternalSqlTableProvider:
    provider_id = EXTERNAL_SQL_PROVIDER_ID

    def get_schema(self, table_ref: TableRefModel) -> list[FieldSchemaModel]:
        self._validate_ref(table_ref)
        return list(table_ref.schema)

    def count_rows(self, table_ref: TableRefModel) -> int:
        database_path, source_sql = self._source(table_ref)
        with self._connect(database_path) as connection:
            return int(
                connection.execute(
                    f"SELECT COUNT(*) FROM {source_sql}"
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
        if filters:
            raise ValueError("external SQL provider does not support filters yet")
        database_path, source_sql = self._source(table_ref)
        selected_columns = _selected_columns(table_ref, columns)
        selected_sql = ", ".join(
            _quote_identifier(column) for column in selected_columns
        )
        order_clause = _order_clause(table_ref, order_by)
        query = (
            f"SELECT {selected_sql} FROM {source_sql}"
            f"{order_clause} LIMIT ? OFFSET ?"
        )
        with self._connect(database_path) as connection:
            cursor = connection.execute(query, [limit, offset])
            return [dict(row) for row in cursor.fetchall()]

    def create_table(self, table_ref: TableRefModel) -> None:
        raise ValueError("external SQL provider is read-only")

    def drop_table(self, table_ref: TableRefModel) -> None:
        raise ValueError("external SQL provider is read-only")

    def publish_staging(
        self,
        staging_ref: TableRefModel,
        published_ref: TableRefModel,
    ) -> None:
        raise ValueError("external SQL provider is read-only")

    def _source(self, table_ref: TableRefModel) -> tuple[Path, str]:
        self._validate_ref(table_ref)
        database_path_value = table_ref.opaque_handle.get("database_path")
        if not isinstance(database_path_value, str) or not database_path_value:
            raise ValueError(
                "external SQL table_ref opaque_handle.database_path is required"
            )
        database_path = Path(database_path_value)
        if not database_path.exists():
            raise ValueError("external SQL database does not exist")

        table_name = table_ref.opaque_handle.get("table_name")
        query = table_ref.opaque_handle.get("query")
        if isinstance(table_name, str) and table_name and query is None:
            return database_path, _quote_identifier(table_name)
        if isinstance(query, str) and query and table_name is None:
            normalized_query = query.strip()
            if not normalized_query.lower().startswith("select "):
                raise ValueError("external SQL query must be a SELECT statement")
            if ";" in normalized_query:
                raise ValueError("external SQL query must not contain semicolons")
            return database_path, f"({normalized_query}) AS external_source"
        raise ValueError(
            "external SQL table_ref requires exactly one of table_name or query"
        )

    def _connect(self, database_path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _validate_ref(self, table_ref: TableRefModel) -> None:
        if table_ref.provider_id != self.provider_id:
            raise ValueError("table_ref belongs to a different provider")
        if table_ref.storage_kind != TableStorageKind.EXTERNAL_SQL:
            raise ValueError("external SQL provider only supports EXTERNAL_SQL")


def _selected_columns(
    table_ref: TableRefModel,
    columns: list[str] | None,
) -> list[str]:
    schema_columns = {field.name for field in table_ref.schema}
    selected_columns = columns or [field.name for field in table_ref.schema]
    unknown_columns = set(selected_columns) - schema_columns
    if unknown_columns:
        raise ValueError(f"unknown columns requested: {sorted(unknown_columns)}")
    return selected_columns


def _order_clause(
    table_ref: TableRefModel,
    order_by: list[str] | None,
) -> str:
    if not order_by:
        return ""
    schema_columns = {field.name for field in table_ref.schema}
    clauses: list[str] = []
    for item in order_by:
        direction = "ASC"
        column = item
        if item.startswith("-"):
            direction = "DESC"
            column = item[1:]
        if column not in schema_columns:
            raise ValueError(f"unknown order_by column: {column}")
        clauses.append(f"{_quote_identifier(column)} {direction}")
    return " ORDER BY " + ", ".join(clauses)


def _quote_identifier(identifier: str) -> str:
    if "\x00" in identifier:
        raise ValueError("identifier must not contain NUL")
    return '"' + identifier.replace('"', '""') + '"'
