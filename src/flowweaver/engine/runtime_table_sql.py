from __future__ import annotations

import json
import re
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def schema_fingerprint(schema: Sequence[FieldSchemaModel]) -> str:
    payload = [
        field.model_dump(mode="json", by_alias=True)
        for field in sorted(schema, key=lambda item: item.ordinal)
    ]
    return sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def table_location(table_ref: TableRefModel) -> tuple[Path, str]:
    database_path = table_ref.opaque_handle.get("database_path")
    table_name = table_ref.opaque_handle.get("table_name")
    if not isinstance(database_path, str) or not database_path:
        raise ValueError("table_ref opaque_handle.database_path is required")
    if not isinstance(table_name, str) or not table_name:
        raise ValueError("table_ref opaque_handle.table_name is required")
    return Path(database_path), table_name


def selected_columns(
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


def where_clause(
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
        clauses.append(f"{quote_identifier(str(field))} {sql_operator} ?")
        parameters.append(item.get("value"))
    return f" WHERE {' AND '.join(clauses)}", parameters


def order_clause(
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
        parts.append(f"{quote_identifier(field)} {direction}")
    return f" ORDER BY {', '.join(parts)}"


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def identifier_token(value: str) -> str:
    token = re.sub(r"[^0-9A-Za-z_]+", "_", value).strip("_")
    if not token:
        return "value"
    if token[0].isdigit():
        return f"_{token}"
    return token


def sqlite_type(data_type: str) -> str:
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
