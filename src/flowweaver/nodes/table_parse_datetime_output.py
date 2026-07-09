from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.nodes.table_parse_datetime_helpers import (
    format_parsed_datetime as _format_parsed_datetime,
)
from flowweaver.nodes.table_parse_datetime_helpers import (
    parse_datetime_unmatched_value as _parse_datetime_unmatched_value,
)
from flowweaver.nodes.table_parse_datetime_helpers import (
    parse_datetime_value as _parse_datetime_value,
)
from flowweaver.protocols.table_ref import TableRefModel


def parse_datetime_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    config: dict[str, Any],
    source_field: str,
    time_source_field: str | None,
    parse_type: str,
    input_structure: str,
    output_field: str,
    status_field: str | None,
    unmatched_mode: str,
) -> Iterator[list[dict[str, Any]]]:
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            raw_value = row.get(source_field)
            if time_source_field is not None:
                raw_value = f"{raw_value} {row.get(time_source_field)}"
            parsed = _parse_datetime_value(
                raw_value,
                config=config,
                parse_type=parse_type,
                input_structure=input_structure,
            )
            status = "parsed" if parsed is not None else "failed"
            output_value = (
                _format_parsed_datetime(
                    parsed,
                    config=config,
                    parse_type=parse_type,
                )
                if parsed is not None
                else _parse_datetime_unmatched_value(
                    raw_value,
                    config=config,
                    unmatched_mode=unmatched_mode,
                )
            )
            output_row = dict(row) | {output_field: output_value}
            if status_field is not None:
                output_row[status_field] = status
            output_rows.append(output_row)
        yield output_rows
