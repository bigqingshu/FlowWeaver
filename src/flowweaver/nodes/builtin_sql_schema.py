from __future__ import annotations

import sqlite3
from pathlib import Path

from flowweaver.protocols.table_ref import FieldSchemaModel


def infer_schema(
    *,
    database_path: Path,
    table_name: str | None,
    query: str | None,
) -> list[FieldSchemaModel]:
    if table_name is not None:
        return _infer_table_schema(database_path, table_name)
    assert query is not None
    return _infer_query_schema(database_path, query)


def normalize_query(query: str) -> str:
    normalized_query = query.strip()
    if not normalized_query.lower().startswith("select "):
        raise ValueError("config.query must be a SELECT statement")
    if ";" in normalized_query:
        raise ValueError("config.query must not contain semicolons")
    return normalized_query


def normalize_data_type(value: str) -> str:
    normalized = value.upper()
    if "INT" in normalized:
        return "INTEGER"
    if any(token in normalized for token in ("REAL", "FLOA", "DOUB", "NUM")):
        return "FLOAT"
    if "BOOL" in normalized:
        return "BOOLEAN"
    return "TEXT"


def _infer_table_schema(database_path: Path, table_name: str) -> list[FieldSchemaModel]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            f"PRAGMA table_info({_quote_sql_string(table_name)})"
        ).fetchall()
    if not rows:
        raise ValueError(f"table does not exist or has no columns: {table_name}")
    return [
        FieldSchemaModel(
            field_id=str(row[1]),
            name=str(row[1]),
            data_type=normalize_data_type(str(row[2] or "TEXT")),
            nullable=not bool(row[3]),
            ordinal=index,
        )
        for index, row in enumerate(rows)
    ]


def _infer_query_schema(database_path: Path, query: str) -> list[FieldSchemaModel]:
    normalized_query = normalize_query(query)
    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(f"SELECT * FROM ({normalized_query}) LIMIT 0")
        columns = [item[0] for item in cursor.description or []]
    if not columns:
        raise ValueError("query must return at least one column")
    return [
        FieldSchemaModel(
            field_id=str(column),
            name=str(column),
            data_type="TEXT",
            nullable=True,
            ordinal=index,
        )
        for index, column in enumerate(columns)
    ]


def _quote_sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
