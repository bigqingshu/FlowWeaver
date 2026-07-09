from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def normalize_rows(
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


def ordered_rows(
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
