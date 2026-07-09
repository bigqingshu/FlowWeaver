from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_lookup_matched_field_outputs import (
    LookupMatchedOutputFields,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def lookup_matched_field_index(
    context: BuiltinTableNodeContext,
    *,
    lookup_ref: TableRefModel,
    lookup_fields: list[str],
    match_mode: str,
) -> dict[Any, list[dict[str, Any]]]:
    if match_mode != "equals":
        raise _NodeValidationError(
            f"Unsupported LookupMatchedFieldNameNode match_mode: {match_mode}"
        )
    index: dict[Any, list[dict[str, Any]]] = {}
    row_number = 1
    for rows in context.iter_row_batches(lookup_ref):
        for row in rows:
            for field_name in lookup_fields:
                value = row.get(field_name)
                try:
                    hash(value)
                except TypeError:
                    value = ("repr", type(value).__name__, repr(value))
                index.setdefault(value, []).append(
                    {
                        "field": field_name,
                        "value": row.get(field_name),
                        "row": row_number,
                    }
                )
            row_number += 1
    return index


def lookup_matched_select_match(
    matches: list[dict[str, Any]],
    *,
    multi_match_policy: str,
) -> dict[str, Any] | None:
    if not matches:
        return None
    if multi_match_policy == "last":
        return matches[-1]
    return matches[0]


def lookup_matched_values(
    match: dict[str, Any] | None,
    *,
    match_count: int,
    output_fields: LookupMatchedOutputFields,
    no_match_value: Any,
) -> dict[str, Any]:
    if match is None:
        values: dict[str, Any] = {
            output_fields["field"]: no_match_value,
        }
        if output_fields["value"] is not None:
            values[output_fields["value"]] = no_match_value
        if output_fields["row"] is not None:
            values[output_fields["row"]] = None
        if output_fields["status"] is not None:
            values[output_fields["status"]] = "not_matched"
        return values
    values = {
        output_fields["field"]: match["field"],
    }
    if output_fields["value"] is not None:
        values[output_fields["value"]] = match["value"]
    if output_fields["row"] is not None:
        values[output_fields["row"]] = match["row"]
    if output_fields["status"] is not None:
        values[output_fields["status"]] = (
            "multiple_matched"
            if match_count > 1
            else "matched"
        )
    return values


def lookup_matched_output_batches(
    context: BuiltinTableNodeContext,
    main_ref: TableRefModel,
    *,
    source_field: str,
    lookup_index: dict[Any, list[dict[str, Any]]],
    multi_match_policy: str,
    output_fields: LookupMatchedOutputFields,
    no_match_value: Any,
) -> Iterator[list[dict[str, Any]]]:
    for rows in context.iter_row_batches(main_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            matches = lookup_index.get(row.get(source_field), [])
            if len(matches) > 1 and multi_match_policy == "error":
                raise _NodeValidationError(
                    "LookupMatchedFieldNameNode found multiple matches"
                )
            match = lookup_matched_select_match(
                matches,
                multi_match_policy=multi_match_policy,
            )
            output_rows.append(
                dict(row)
                | lookup_matched_values(
                    match,
                    match_count=len(matches),
                    output_fields=output_fields,
                    no_match_value=no_match_value,
                )
            )
        yield output_rows
