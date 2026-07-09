from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_row_condition_helpers import (
    condition_cell_matches as _condition_cell_matches,
)
from flowweaver.nodes.value_sources import ValueSourceError
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def advanced_filter_row_matches(
    row: dict[str, Any],
    *,
    conditions: list[dict[str, Any]],
    logic: str,
) -> bool:
    if not conditions:
        return True
    if logic == "and":
        for condition in conditions:
            if not _advanced_filter_condition_matches(row, condition):
                return False
        return True
    for condition in conditions:
        if _advanced_filter_condition_matches(row, condition):
            return True
    return False


def advanced_filter_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    conditions: list[dict[str, Any]],
    logic: str,
    output_fields: list[str],
    result_limit: int | None,
    max_intermediate: int | None,
    remove_duplicates: bool,
) -> Iterator[list[dict[str, Any]]]:
    output_count = 0
    matched_count = 0
    seen_rows: set[tuple[Any, ...]] = set()
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            try:
                if not advanced_filter_row_matches(
                    row,
                    conditions=conditions,
                    logic=logic,
                ):
                    continue
            except ValueSourceError as exc:
                raise _NodeValidationError(str(exc)) from exc
            output_row = {
                field_name: row.get(field_name)
                for field_name in output_fields
            }
            if remove_duplicates:
                output_key = tuple(
                    output_row.get(field)
                    for field in output_fields
                )
                if output_key in seen_rows:
                    continue
                seen_rows.add(output_key)
            matched_count += 1
            if max_intermediate is not None and matched_count > max_intermediate:
                raise _NodeValidationError(
                    "AdvancedFilterRowsNode matched rows exceed max_intermediate"
                )
            if result_limit is not None and output_count >= result_limit:
                if output_rows:
                    yield output_rows
                return
            output_rows.append(output_row)
            output_count += 1
        if output_rows:
            yield output_rows


def _advanced_filter_condition_matches(
    row: dict[str, Any],
    condition: dict[str, Any],
) -> bool:
    value = condition["value_source"].resolve(row)
    return _condition_cell_matches(
        row.get(condition["field"]),
        operator=condition["operator"],
        value=value,
        case_sensitive=condition["case_sensitive"],
    )
