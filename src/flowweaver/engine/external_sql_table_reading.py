from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from flowweaver.protocols.table_ref import TableRefModel


def count_external_sql_rows(database_path: Path, source_sql: str) -> int:
    with connect_external_sql_database(database_path) as connection:
        return int(
            connection.execute(f"SELECT COUNT(*) FROM {source_sql}").fetchone()[0]
        )


def read_external_sql_rows(
    *,
    table_ref: TableRefModel,
    database_path: Path,
    source_sql: str,
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

    selected_columns = _selected_columns(table_ref, columns)
    selected_sql = ", ".join(
        quote_external_sql_identifier(column) for column in selected_columns
    )
    order_clause = _order_clause(table_ref, order_by)
    query = (
        f"SELECT {selected_sql} FROM {source_sql}"
        f"{order_clause} LIMIT ? OFFSET ?"
    )
    with connect_external_sql_database(database_path) as connection:
        cursor = connection.execute(query, [limit, offset])
        return [dict(row) for row in cursor.fetchall()]


def connect_external_sql_database(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def quote_external_sql_identifier(identifier: str) -> str:
    if "\x00" in identifier:
        raise ValueError("identifier must not contain NUL")
    return '"' + identifier.replace('"', '""') + '"'


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
        clauses.append(f"{quote_external_sql_identifier(column)} {direction}")
    return " ORDER BY " + ", ".join(clauses)
