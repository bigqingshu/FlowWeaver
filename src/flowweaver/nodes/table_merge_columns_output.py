from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.protocols.table_ref import TableRefModel


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
