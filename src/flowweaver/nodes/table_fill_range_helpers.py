from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any

from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import find_field
from flowweaver.nodes.value_sources import ValueSource, ValueSourceError
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def field_range(
    schema: list[FieldSchemaModel],
    *,
    start_field: str,
    end_field: str,
    node_type: str,
) -> list[str]:
    start_schema = find_field(schema, start_field)
    if start_schema is None:
        raise _NodeValidationError(f"Field does not exist: {start_field}")
    end_schema = find_field(schema, end_field)
    if end_schema is None:
        raise _NodeValidationError(f"Field does not exist: {end_field}")
    if start_schema.ordinal > end_schema.ordinal:
        raise _NodeValidationError(
            f"{node_type} start_field must not be after end_field"
        )
    return [
        field.name
        for field in schema
        if start_schema.ordinal <= field.ordinal <= end_schema.ordinal
    ]


def fill_range_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    start_row: int,
    end_row: int,
    target_fields: Sequence[str],
    value_source: ValueSource,
    overwrite_rule: str,
) -> Iterator[list[dict[str, Any]]]:
    row_number = 1
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            if start_row <= row_number <= end_row:
                try:
                    fill_value = value_source.resolve(row)
                except ValueSourceError as exc:
                    raise _NodeValidationError(str(exc)) from exc
                output_row = dict(row)
                for field in target_fields:
                    if overwrite_rule == "all" or _is_empty_cell(
                        output_row.get(field)
                    ):
                        output_row[field] = fill_value
                output_rows.append(output_row)
            else:
                output_rows.append(row)
            row_number += 1
        yield output_rows
