from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_value_source_config import (
    value_source_config as _value_source_config,
)
from flowweaver.nodes.value_sources import ValueSource, ValueSourceError
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def fill_cells_value_source_config(config: dict[str, Any]):
    return _value_source_config(
        config,
        "value_source",
        fallback_key="manual_value",
    )


def fill_cells_selected_rows(
    *,
    start_row: int,
    direction: str,
    count: int | None,
    total_rows: int,
) -> set[int]:
    if total_rows <= 0:
        return set()
    if direction == "down":
        end_row = (
            total_rows
            if count is None
            else min(total_rows, start_row + count - 1)
        )
        return set(range(start_row, end_row + 1))
    end_row = 1 if count is None else max(1, start_row - count + 1)
    return set(range(end_row, start_row + 1))


def fill_cells_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    target_field: str,
    value_source: ValueSource,
    selected_rows: set[int],
    overwrite_rule: str,
) -> Iterator[list[dict[str, Any]]]:
    row_number = 1
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            if row_number in selected_rows and (
                overwrite_rule == "all" or _is_empty_cell(row.get(target_field))
            ):
                try:
                    output_rows.append(row | {target_field: value_source.resolve(row)})
                except ValueSourceError as exc:
                    raise _NodeValidationError(str(exc)) from exc
            else:
                output_rows.append(row)
            row_number += 1
        yield output_rows
