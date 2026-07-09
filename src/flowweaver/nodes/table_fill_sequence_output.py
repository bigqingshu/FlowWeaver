from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_fill_sequence_selection import (
    fill_sequence_selected_index as _fill_sequence_selected_index,
)
from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.nodes.table_ops import replace_field_schema
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def fill_sequence_output_schema(
    schema: list[FieldSchemaModel],
    *,
    target_field: str,
    formatted: bool,
) -> list[FieldSchemaModel]:
    if not formatted:
        return schema
    return replace_field_schema(
        schema,
        target_field,
        data_type="TEXT",
        nullable=True,
    )


def format_sequence_value(
    value: float,
    *,
    zero_pad: int,
    prefix: str,
    suffix: str,
) -> Any:
    normalized = _normalize_sequence_number(value)
    if not prefix and not suffix and zero_pad <= 0:
        return normalized
    text = str(normalized)
    if zero_pad > 0:
        text = text.zfill(zero_pad)
    return f"{prefix}{text}{suffix}"


def fill_sequence_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    target_field: str,
    selector: dict[str, Any],
    start_value: float,
    step: float,
    overwrite_rule: str,
    zero_pad: int,
    prefix: str,
    suffix: str,
) -> Iterator[list[dict[str, Any]]]:
    row_number = 1
    sequence_index = 0
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            selected_index = _fill_sequence_selected_index(
                row,
                row_number=row_number,
                selector=selector,
            )
            should_fill = selected_index is not None and (
                overwrite_rule == "all" or _is_empty_cell(row.get(target_field))
            )
            if should_fill:
                assert selected_index is not None
                if selected_index <= 0:
                    sequence_index += 1
                    selected_index = sequence_index
                output_rows.append(
                    dict(row)
                    | {
                        target_field: format_sequence_value(
                            start_value + (selected_index - 1) * step,
                            zero_pad=zero_pad,
                            prefix=prefix,
                            suffix=suffix,
                        )
                    }
                )
            else:
                output_rows.append(dict(row))
            row_number += 1
        yield output_rows


def _normalize_sequence_number(value: float) -> int | float:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value
