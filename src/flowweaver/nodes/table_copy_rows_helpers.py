from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def copy_row_source_row(
    context: BuiltinTableNodeContext,
    *,
    input_ref: TableRefModel,
    source_row_number: int,
) -> dict[str, Any]:
    row_number = 1
    for rows in context.iter_row_batches(input_ref):
        for row in rows:
            if row_number == source_row_number:
                return dict(row)
            row_number += 1
    raise _NodeValidationError("CopyRowsNode config.source_row is out of range")


def copy_row_batches(
    source_row: dict[str, Any],
    *,
    copy_count: int,
    batch_size: int,
) -> Iterator[list[dict[str, Any]]]:
    remaining = copy_count
    while remaining > 0:
        current_batch_size = min(remaining, batch_size)
        yield [
            dict(source_row)
            for _ in range(current_batch_size)
        ]
        remaining -= current_batch_size


def copy_rows_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    source_row: dict[str, Any],
    copy_count: int,
    insert_mode: str,
    insert_row: int,
) -> Iterator[list[dict[str, Any]]]:
    if insert_mode == "prepend":
        yield from copy_row_batches(
            source_row,
            copy_count=copy_count,
            batch_size=context.row_batch_size,
        )
    row_number = 1
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            if insert_mode == "before_row" and row_number == insert_row:
                if output_rows:
                    yield output_rows
                    output_rows = []
                yield from copy_row_batches(
                    source_row,
                    copy_count=copy_count,
                    batch_size=context.row_batch_size,
                )
            output_rows.append(row)
            if insert_mode == "after_row" and row_number == insert_row:
                if output_rows:
                    yield output_rows
                    output_rows = []
                yield from copy_row_batches(
                    source_row,
                    copy_count=copy_count,
                    batch_size=context.row_batch_size,
                )
            row_number += 1
        if output_rows:
            yield output_rows
    if insert_mode == "append":
        yield from copy_row_batches(
            source_row,
            copy_count=copy_count,
            batch_size=context.row_batch_size,
        )
