from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.nodes.table_row_unpivot_output import (
    unpivot_output_rows as unpivot_output_rows,
)
from flowweaver.nodes.table_row_unpivot_selection import (
    unpivot_row_selected as unpivot_row_selected,
)
from flowweaver.protocols.table_ref import TableRefModel


def unpivot_rows_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    config: dict[str, Any],
    row_selector: dict[str, int],
) -> Iterator[list[dict[str, Any]]]:
    row_number = 1
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            if unpivot_row_selected(row_number, row_selector):
                output_rows.extend(
                    unpivot_output_rows(
                        row,
                        row_number=row_number,
                        config=config,
                    )
                )
            row_number += 1
        yield output_rows
