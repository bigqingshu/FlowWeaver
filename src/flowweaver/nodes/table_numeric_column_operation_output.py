from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.nodes.table_numeric_column_operation_helpers import (
    numeric_operation_value as _numeric_operation_value,
)
from flowweaver.nodes.table_numeric_column_operation_helpers import (
    numeric_row_selected as _numeric_row_selected,
)
from flowweaver.protocols.table_ref import TableRefModel


def numeric_operation_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    config: dict[str, Any],
    target_field: str,
    operation: str,
    operand_config: dict[str, Any],
    decimal_places: int | None,
    non_number_policy: str,
    divide_zero_policy: str,
    row_selector: dict[str, Any],
    output_field: str,
) -> Iterator[list[dict[str, Any]]]:
    row_number = 1
    sequence_index = 0
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            if not _numeric_row_selected(
                row,
                row_number=row_number,
                selector=row_selector,
            ):
                output_rows.append(dict(row) | {output_field: row.get(target_field)})
                row_number += 1
                continue
            sequence_index += 1
            output_value = _numeric_operation_value(
                row,
                row_number=row_number,
                sequence_index=sequence_index,
                target_field=target_field,
                operation=operation,
                operand_config=operand_config,
                decimal_places=decimal_places,
                non_number_policy=non_number_policy,
                divide_zero_policy=divide_zero_policy,
                config=config,
            )
            output_rows.append(dict(row) | {output_field: output_value})
            row_number += 1
        yield output_rows
