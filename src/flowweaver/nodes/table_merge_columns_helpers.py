from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import append_field, has_field, replace_field_schema
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def merge_columns_separators(
    config: dict[str, Any],
    *,
    field_count: int,
) -> list[str]:
    separator_count = max(0, field_count - 1)
    raw_separators = config.get("separators", [""] * separator_count)
    if isinstance(raw_separators, str):
        return [raw_separators] * separator_count
    if not isinstance(raw_separators, list):
        raise _NodeValidationError("MergeColumnsNode config.separators must be a list")
    if separator_count == 0:
        return []
    if len(raw_separators) == 1:
        separator = raw_separators[0]
        if not isinstance(separator, str):
            raise _NodeValidationError(
                "MergeColumnsNode config.separators must contain strings"
            )
        return [separator] * separator_count
    if len(raw_separators) != separator_count:
        raise _NodeValidationError(
            "MergeColumnsNode config.separators must contain one separator or "
            "field_count - 1 separators"
        )
    separators: list[str] = []
    for separator in raw_separators:
        if not isinstance(separator, str):
            raise _NodeValidationError(
                "MergeColumnsNode config.separators must contain strings"
            )
        separators.append(separator)
    return separators


def merge_columns_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    output_field: str,
    conflict_mode: str,
) -> list[FieldSchemaModel]:
    if has_field(input_schema, output_field):
        if conflict_mode == "error":
            raise _NodeValidationError(f"Field already exists: {output_field}")
        return replace_field_schema(
            input_schema,
            output_field,
            data_type="TEXT",
            nullable=True,
        )
    return append_field(
        input_schema,
        name=output_field,
        data_type="TEXT",
        nullable=True,
    )


def merge_columns_value(
    row: dict[str, Any],
    *,
    fields: list[str],
    separators: list[str],
    skip_empty: bool,
    trim_value: bool,
    empty_placeholder: Any,
) -> str:
    values: list[str] = []
    for field_name in fields:
        value = row.get(field_name)
        if value is None:
            text_value = ""
        else:
            text_value = str(value)
        if trim_value:
            text_value = text_value.strip()
        if _is_empty_cell(text_value):
            if skip_empty:
                continue
            text_value = "" if empty_placeholder is None else str(empty_placeholder)
        values.append(text_value)
    if skip_empty:
        separator = separators[0] if separators else ""
        return separator.join(values)
    merged = ""
    for index, value in enumerate(values):
        if index > 0:
            merged += separators[index - 1]
        merged += value
    return merged


def merge_columns_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    output_field: str,
    fields: list[str],
    separators: list[str],
    skip_empty: bool,
    trim_value: bool,
    empty_placeholder: Any,
) -> Iterator[list[dict[str, Any]]]:
    for rows in context.iter_row_batches(input_ref):
        yield [
            row
            | {
                output_field: merge_columns_value(
                    row,
                    fields=fields,
                    separators=separators,
                    skip_empty=skip_empty,
                    trim_value=trim_value,
                    empty_placeholder=empty_placeholder,
                )
            }
            for row in rows
        ]
