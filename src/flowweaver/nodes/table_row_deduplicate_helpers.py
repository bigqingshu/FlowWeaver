from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import DEDUPLICATE_ROWS_NODE_TYPE
from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import string_list_config as _string_list_config
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import append_field, has_field
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def deduplicate_key_fields(
    config: dict[str, Any],
    input_ref: TableRefModel,
) -> list[str]:
    dedupe_mode = _enum_config(
        config,
        "dedupe_mode",
        default="key_fields",
        allowed={"key_fields", "entire_row"},
        node_type=DEDUPLICATE_ROWS_NODE_TYPE,
    )
    if dedupe_mode == "entire_row":
        return [field.name for field in input_ref.schema]
    key_fields = _string_list_config(
        config,
        "key_fields",
        node_type=DEDUPLICATE_ROWS_NODE_TYPE,
    )
    missing_fields = [
        field_name
        for field_name in key_fields
        if not has_field(input_ref.schema, field_name)
    ]
    if missing_fields:
        raise _NodeValidationError(
            f"Fields do not exist: {', '.join(missing_fields)}"
        )
    return key_fields


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


def deduplicate_marker_fields(config: dict[str, Any]) -> dict[str, str]:
    return {
        "group": _optional_node_string_config(
            config,
            "duplicate_group_field",
            default="_duplicate_group",
            node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        ),
        "status": _optional_node_string_config(
            config,
            "duplicate_status_field",
            default="_duplicate_status",
            node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        ),
        "index": _optional_node_string_config(
            config,
            "duplicate_index_field",
            default="_duplicate_index",
            node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        ),
        "count": _optional_node_string_config(
            config,
            "duplicate_count_field",
            default="_duplicate_count",
            node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        ),
        "keep": _optional_node_string_config(
            config,
            "keep_flag_field",
            default="_keep_row",
            node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        ),
    }


def deduplicate_output_schema(
    input_schema: list[FieldSchemaModel],
    marker_fields: dict[str, str],
) -> list[FieldSchemaModel]:
    marker_names = list(marker_fields.values())
    duplicate_marker_names = [
        field_name
        for index, field_name in enumerate(marker_names)
        if field_name in marker_names[:index]
    ]
    if duplicate_marker_names:
        raise _NodeValidationError(
            f"DeduplicateRowsNode marker fields are duplicated: "
            f"{', '.join(duplicate_marker_names)}"
        )
    existing_marker_fields = [
        field_name
        for field_name in marker_names
        if has_field(input_schema, field_name)
    ]
    if existing_marker_fields:
        raise _NodeValidationError(
            f"Fields already exist: {', '.join(existing_marker_fields)}"
        )
    schema = append_field(
        input_schema,
        name=marker_fields["group"],
        data_type="TEXT",
        nullable=True,
    )
    schema = append_field(
        schema,
        name=marker_fields["status"],
        data_type="TEXT",
        nullable=False,
    )
    schema = append_field(
        schema,
        name=marker_fields["index"],
        data_type="INTEGER",
        nullable=False,
    )
    schema = append_field(
        schema,
        name=marker_fields["count"],
        data_type="INTEGER",
        nullable=False,
    )
    return append_field(
        schema,
        name=marker_fields["keep"],
        data_type="BOOLEAN",
        nullable=False,
    )


def deduplicate_marker_values(
    *,
    key: tuple[Any, ...] | None,
    groups: dict[tuple[Any, ...], dict[str, int]],
    occurrence_index: int,
    keep_row: bool,
    marker_fields: dict[str, str],
) -> dict[str, Any]:
    if key is None:
        return {
            marker_fields["group"]: None,
            marker_fields["status"]: "skipped_empty_key",
            marker_fields["index"]: occurrence_index,
            marker_fields["count"]: 1,
            marker_fields["keep"]: True,
        }
    group = groups[key]
    group_count = group["count"]
    if group_count <= 1:
        status = "unique"
    elif keep_row:
        status = "kept"
    else:
        status = "duplicate"
    return {
        marker_fields["group"]: f"group-{group['first']}",
        marker_fields["status"]: status,
        marker_fields["index"]: occurrence_index,
        marker_fields["count"]: group_count,
        marker_fields["keep"]: keep_row,
    }
