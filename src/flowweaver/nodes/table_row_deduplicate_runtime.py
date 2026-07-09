from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.nodes.table_row_deduplicate_markers import (
    deduplicate_marker_values as deduplicate_marker_values,
)
from flowweaver.protocols.table_ref import TableRefModel


def deduplicate_groups(
    context: BuiltinTableNodeContext,
    *,
    input_ref: TableRefModel,
    key_fields: list[str],
    trim: bool,
    ignore_case: bool,
    empty_key_policy: str,
) -> dict[tuple[Any, ...], dict[str, int]]:
    groups: dict[tuple[Any, ...], dict[str, int]] = {}
    row_number = 1
    for rows in context.iter_row_batches(input_ref):
        for row in rows:
            key = deduplicate_key(
                row,
                key_fields=key_fields,
                trim=trim,
                ignore_case=ignore_case,
                empty_key_policy=empty_key_policy,
            )
            if key is not None:
                group = groups.setdefault(
                    key,
                    {
                        "count": 0,
                        "first": row_number,
                        "last": row_number,
                    },
                )
                group["count"] += 1
                group["last"] = row_number
            row_number += 1
    return groups


def deduplicate_key(
    row: dict[str, Any],
    *,
    key_fields: list[str],
    trim: bool,
    ignore_case: bool,
    empty_key_policy: str,
) -> tuple[Any, ...] | None:
    key_values = tuple(
        _deduplicate_key_value(
            row.get(field_name),
            trim=trim,
            ignore_case=ignore_case,
        )
        for field_name in key_fields
    )
    if empty_key_policy == "skip" and all(
        _is_empty_cell(value)
        for value in key_values
    ):
        return None
    return key_values


def deduplicate_should_keep(
    row_number: int,
    *,
    key: tuple[Any, ...] | None,
    groups: dict[tuple[Any, ...], dict[str, int]],
    keep_policy: str,
) -> bool:
    if key is None:
        return True
    group = groups[key]
    if group["count"] <= 1 or keep_policy == "all":
        return True
    if keep_policy == "first":
        return row_number == group["first"]
    return row_number == group["last"]


def deduplicate_occurrence_index(
    occurrence_counts: dict[tuple[Any, ...], int],
    key: tuple[Any, ...] | None,
) -> int:
    if key is None:
        return 1
    occurrence_counts[key] = occurrence_counts.get(key, 0) + 1
    return occurrence_counts[key]


def deduplicate_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    key_fields: list[str],
    trim: bool,
    ignore_case: bool,
    empty_key_policy: str,
    keep_policy: str,
    output_mode: str,
    add_marker_columns: bool,
    marker_fields: dict[str, str],
    groups: dict[tuple[Any, ...], dict[str, int]],
) -> Iterator[list[dict[str, Any]]]:
    row_number = 1
    occurrence_counts: dict[tuple[Any, ...], int] = {}
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            key = deduplicate_key(
                row,
                key_fields=key_fields,
                trim=trim,
                ignore_case=ignore_case,
                empty_key_policy=empty_key_policy,
            )
            occurrence_index = deduplicate_occurrence_index(
                occurrence_counts,
                key,
            )
            keep_row = deduplicate_should_keep(
                row_number,
                key=key,
                groups=groups,
                keep_policy=keep_policy,
            )
            if output_mode == "mark" or keep_row:
                output_row = dict(row)
                if add_marker_columns:
                    output_row |= deduplicate_marker_values(
                        key=key,
                        groups=groups,
                        occurrence_index=occurrence_index,
                        keep_row=keep_row,
                        marker_fields=marker_fields,
                    )
                output_rows.append(output_row)
            row_number += 1
        yield output_rows


def _deduplicate_key_value(value: Any, *, trim: bool, ignore_case: bool) -> Any:
    normalized = value
    if isinstance(normalized, str):
        if trim:
            normalized = normalized.strip()
        if ignore_case:
            normalized = normalized.lower()
    try:
        hash(normalized)
    except TypeError:
        return ("repr", type(normalized).__name__, repr(normalized))
    return normalized
