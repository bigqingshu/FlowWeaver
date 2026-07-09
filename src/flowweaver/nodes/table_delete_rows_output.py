from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_delete_rows_predicates import DeleteRowsPredicate
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.value_sources import ValueSourceError
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def delete_rows_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    should_delete: DeleteRowsPredicate,
) -> Iterator[list[dict[str, Any]]]:
    row_number = 1
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            try:
                if not should_delete(row_number, row):
                    output_rows.append(row)
            except ValueSourceError as exc:
                raise _NodeValidationError(str(exc)) from exc
            row_number += 1
        yield output_rows
