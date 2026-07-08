from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import (
    ADVANCED_FILTER_ROWS_NODE_TYPE,
    DEDUPLICATE_ROWS_NODE_TYPE,
    UNPIVOT_ROWS_NODE_TYPE,
)
from flowweaver.nodes.table_node_common import (
    is_empty_cell as _is_empty_cell,
)
from flowweaver.nodes.table_node_common import (
    require_fields as _require_fields,
)
from flowweaver.nodes.table_node_config import (
    bool_config as _bool_config,
)
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
)
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_non_negative_int_config as _optional_non_negative_int_config,
)
from flowweaver.nodes.table_node_config import (
    optional_positive_int_config as _optional_positive_int_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_list_config as _optional_string_list_config,
)
from flowweaver.nodes.table_node_config import (
    positive_int_config as _positive_int_config,
)
from flowweaver.nodes.table_node_config import (
    string_list_config as _string_list_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import (
    primary_input_ref as _primary_input_ref,
)
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_ops import (
    append_field,
    find_field,
    has_field,
    reorder_fields,
)
from flowweaver.nodes.table_row_condition_helpers import (
    condition_cell_matches as _condition_cell_matches,
)
from flowweaver.nodes.table_row_condition_helpers import (
    normalize_condition_operator as _normalize_condition_operator,
)
from flowweaver.nodes.table_row_condition_helpers import (
    value_source_from_mapping as _value_source_from_mapping,
)
from flowweaver.nodes.table_row_edit_nodes import (
    CopyRowsNodeHandler as CopyRowsNodeHandler,
)
from flowweaver.nodes.table_row_edit_nodes import (
    DeleteRowsNodeHandler as DeleteRowsNodeHandler,
)
from flowweaver.nodes.value_sources import ValueSourceError
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class UnpivotRowsNodeHandler:
    node_type = UNPIVOT_ROWS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = _primary_input_ref(
            task,
            context,
            node_type=self.node_type,
        )
        config = _unpivot_rows_config(task.config, input_ref=input_ref)
        output_schema = _unpivot_rows_output_schema(
            input_ref.schema,
            keep_fields=config["keep_fields"],
            output_value_field=config["output_value_field"],
            source_field_name=config["source_field_name"],
            original_row_field=config["original_row_field"],
            status_field=config["status_field"],
        )
        row_selector = _unpivot_row_selector(
            task.config,
            total_rows=context.count_rows(input_ref),
        )

        def output_batches():
            row_number = 1
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    if _unpivot_row_selected(row_number, row_selector):
                        output_rows.extend(
                            _unpivot_output_rows(
                                row,
                                row_number=row_number,
                                config=config,
                            )
                        )
                    row_number += 1
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )


class DeduplicateRowsNodeHandler:
    node_type = DEDUPLICATE_ROWS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = _primary_input_ref(
            task,
            context,
            node_type=self.node_type,
        )
        key_fields = _deduplicate_key_fields(task.config, input_ref)
        trim = _bool_config(task.config, "trim", default=False)
        ignore_case = _bool_config(task.config, "ignore_case", default=False)
        empty_key_policy = _enum_config(
            task.config,
            "empty_key_policy",
            default="include",
            allowed={"include", "skip"},
            node_type=self.node_type,
        )
        keep_policy = _enum_config(
            task.config,
            "keep_policy",
            default="first",
            allowed={"first", "last", "all"},
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="dedupe",
            allowed={"dedupe", "mark"},
            node_type=self.node_type,
        )
        add_marker_columns = _bool_config(
            task.config,
            "add_marker_columns",
            default=output_mode == "mark",
        )
        if output_mode == "mark" and not add_marker_columns:
            raise _NodeValidationError(
                "DeduplicateRowsNode output_mode=mark requires marker columns"
            )
        marker_fields = _deduplicate_marker_fields(task.config)
        output_schema = (
            _deduplicate_output_schema(input_ref.schema, marker_fields)
            if add_marker_columns
            else input_ref.schema
        )
        groups = _deduplicate_groups(
            context,
            input_ref=input_ref,
            key_fields=key_fields,
            trim=trim,
            ignore_case=ignore_case,
            empty_key_policy=empty_key_policy,
        )

        def output_batches():
            row_number = 1
            occurrence_counts: dict[tuple[Any, ...], int] = {}
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    key = _deduplicate_key(
                        row,
                        key_fields=key_fields,
                        trim=trim,
                        ignore_case=ignore_case,
                        empty_key_policy=empty_key_policy,
                    )
                    occurrence_index = _deduplicate_occurrence_index(
                        occurrence_counts,
                        key,
                    )
                    keep_row = _deduplicate_should_keep(
                        row_number,
                        key=key,
                        groups=groups,
                        keep_policy=keep_policy,
                    )
                    if output_mode == "mark" or keep_row:
                        output_row = dict(row)
                        if add_marker_columns:
                            output_row |= _deduplicate_marker_values(
                                key=key,
                                groups=groups,
                                occurrence_index=occurrence_index,
                                keep_row=keep_row,
                                marker_fields=marker_fields,
                            )
                        output_rows.append(output_row)
                    row_number += 1
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )


class AdvancedFilterRowsNodeHandler:
    node_type = ADVANCED_FILTER_ROWS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = _primary_input_ref(
            task,
            context,
            node_type=self.node_type,
        )
        logic = _enum_config(
            task.config,
            "logic",
            default="and",
            allowed={"and", "or"},
            node_type=self.node_type,
        )
        conditions = _advanced_filter_conditions(task.config, input_ref)
        output_fields = _advanced_filter_output_fields(task.config, input_ref)
        output_schema = reorder_fields(
            input_ref.schema,
            output_fields,
            include_unlisted=False,
        )
        result_limit = _optional_non_negative_int_config(
            task.config,
            "result_limit",
            node_type=self.node_type,
        )
        max_intermediate = _optional_positive_int_config(
            task.config,
            "max_intermediate",
            node_type=self.node_type,
        )
        remove_duplicates = _bool_config(
            task.config,
            "remove_duplicates",
            default=False,
        )

        def output_batches():
            output_count = 0
            matched_count = 0
            seen_rows: set[tuple[Any, ...]] = set()
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    try:
                        if not _advanced_filter_row_matches(
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
                    if (
                        max_intermediate is not None
                        and matched_count > max_intermediate
                    ):
                        raise _NodeValidationError(
                            "AdvancedFilterRowsNode matched rows exceed "
                            "max_intermediate"
                        )
                    if result_limit is not None and output_count >= result_limit:
                        if output_rows:
                            yield output_rows
                        return
                    output_rows.append(output_row)
                    output_count += 1
                if output_rows:
                    yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )


def _unpivot_rows_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> dict[str, Any]:
    value_fields = _string_list_config(
        config,
        "value_fields",
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    keep_fields = _optional_string_list_config(
        config,
        "keep_fields",
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    _require_fields(input_ref.schema, value_fields + keep_fields)
    output_value_field = _optional_node_string_config(
        config,
        "output_value_field",
        default="value",
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    output_source_field = _bool_config(
        config,
        "output_source_field",
        default=True,
    )
    source_field_name = (
        _optional_node_string_config(
            config,
            "source_field_name",
            default="source_field",
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        if output_source_field
        else None
    )
    output_original_row = _bool_config(
        config,
        "output_original_row",
        default=False,
    )
    original_row_field = (
        _optional_node_string_config(
            config,
            "original_row_field",
            default="original_row",
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        if output_original_row
        else None
    )
    output_status = _bool_config(config, "output_status", default=False)
    status_field = (
        _optional_node_string_config(
            config,
            "status_field",
            default="mapping_status",
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        if output_status
        else None
    )
    output_field_names = [
        field
        for field in [
            output_value_field,
            source_field_name,
            original_row_field,
            status_field,
        ]
        if field is not None
    ]
    conflicts = sorted(set(keep_fields) & set(output_field_names))
    if conflicts:
        raise _NodeValidationError(
            f"UnpivotRowsNode output fields conflict with keep_fields: "
            f"{', '.join(conflicts)}"
        )
    duplicates = sorted(
        field
        for field in set(output_field_names)
        if output_field_names.count(field) > 1
    )
    if duplicates:
        raise _NodeValidationError(
            f"UnpivotRowsNode output fields are duplicated: {', '.join(duplicates)}"
        )
    return {
        "value_fields": value_fields,
        "keep_fields": keep_fields,
        "output_value_field": output_value_field,
        "source_field_name": source_field_name,
        "original_row_field": original_row_field,
        "status_field": status_field,
        "empty_mode": _enum_config(
            config,
            "empty_mode",
            default="skip",
            allowed={"skip", "empty", "fixed"},
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        ),
        "empty_fixed": config.get("empty_fixed"),
        "trim_value": _bool_config(config, "trim_value", default=False),
    }


def _unpivot_rows_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    keep_fields: list[str],
    output_value_field: str,
    source_field_name: str | None,
    original_row_field: str | None,
    status_field: str | None,
) -> list[FieldSchemaModel]:
    schema: list[FieldSchemaModel] = []
    fields_by_name = {field.name: field for field in input_schema}
    for field_name in keep_fields:
        field = fields_by_name[field_name]
        schema.append(field.model_copy(update={"ordinal": len(schema)}))
    schema = append_field(
        schema,
        name=output_value_field,
        data_type="TEXT",
        nullable=True,
    )
    if source_field_name is not None:
        schema = append_field(
            schema,
            name=source_field_name,
            data_type="TEXT",
            nullable=False,
        )
    if original_row_field is not None:
        schema = append_field(
            schema,
            name=original_row_field,
            data_type="INTEGER",
            nullable=False,
        )
    if status_field is not None:
        schema = append_field(
            schema,
            name=status_field,
            data_type="TEXT",
            nullable=False,
        )
    return schema


def _unpivot_row_selector(
    config: dict[str, Any],
    *,
    total_rows: int,
) -> dict[str, int]:
    start_row = _positive_int_config(
        config,
        "start_row",
        default=1,
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    if total_rows > 0 and start_row > total_rows:
        raise _NodeValidationError("UnpivotRowsNode config.start_row is out of range")
    end_mode = _enum_config(
        config,
        "end_mode",
        default="to_end",
        allowed={"to_end", "count", "end_row"},
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    if total_rows <= 0:
        return {"start_row": 1, "end_row": 0}
    if end_mode == "count":
        count = _positive_int_config(
            config,
            "count",
            default=1,
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        end_row = min(total_rows, start_row + count - 1)
    elif end_mode == "end_row":
        end_row = _positive_int_config(
            config,
            "end_row",
            default=total_rows,
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        if end_row > total_rows:
            raise _NodeValidationError("UnpivotRowsNode config.end_row is out of range")
        if start_row > end_row:
            raise _NodeValidationError("UnpivotRowsNode start_row must be <= end_row")
    else:
        end_row = total_rows
    return {"start_row": start_row, "end_row": end_row}


def _unpivot_row_selected(
    row_number: int,
    row_selector: dict[str, int],
) -> bool:
    return row_selector["start_row"] <= row_number <= row_selector["end_row"]


def _unpivot_output_rows(
    row: dict[str, Any],
    *,
    row_number: int,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    output_rows: list[dict[str, Any]] = []
    base_row = {
        field: row.get(field)
        for field in config["keep_fields"]
    }
    for value_field in config["value_fields"]:
        value = row.get(value_field)
        if config["trim_value"] and isinstance(value, str):
            value = value.strip()
        status = "mapped"
        if _is_empty_cell(value):
            if config["empty_mode"] == "skip":
                continue
            if config["empty_mode"] == "fixed":
                value = config["empty_fixed"]
                status = "empty_fixed"
            else:
                status = "empty"
        output_row = dict(base_row)
        output_row[config["output_value_field"]] = value
        if config["source_field_name"] is not None:
            output_row[config["source_field_name"]] = value_field
        if config["original_row_field"] is not None:
            output_row[config["original_row_field"]] = row_number
        if config["status_field"] is not None:
            output_row[config["status_field"]] = status
        output_rows.append(output_row)
    return output_rows


def _deduplicate_key_fields(
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


def _deduplicate_groups(
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
            key = _deduplicate_key(
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


def _deduplicate_key(
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


def _deduplicate_should_keep(
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


def _deduplicate_occurrence_index(
    occurrence_counts: dict[tuple[Any, ...], int],
    key: tuple[Any, ...] | None,
) -> int:
    if key is None:
        return 1
    occurrence_counts[key] = occurrence_counts.get(key, 0) + 1
    return occurrence_counts[key]


def _deduplicate_marker_fields(config: dict[str, Any]) -> dict[str, str]:
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


def _deduplicate_output_schema(
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


def _deduplicate_marker_values(
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


def _advanced_filter_conditions(
    config: dict[str, Any],
    input_ref: TableRefModel,
) -> list[dict[str, Any]]:
    raw_conditions = config.get("conditions", [])
    if raw_conditions is None:
        raw_conditions = []
    if not isinstance(raw_conditions, list):
        raise _NodeValidationError(
            "AdvancedFilterRowsNode config.conditions must be a list"
        )
    conditions: list[dict[str, Any]] = []
    for index, item in enumerate(raw_conditions):
        if not isinstance(item, dict):
            raise _NodeValidationError(
                "AdvancedFilterRowsNode config.conditions must contain objects"
            )
        field = item.get("field")
        if not isinstance(field, str) or not field.strip():
            raise _NodeValidationError(
                f"AdvancedFilterRowsNode conditions[{index}].field is required"
            )
        field = field.strip()
        if find_field(input_ref.schema, field) is None:
            raise _NodeValidationError(f"Field does not exist: {field}")
        operator = _normalize_condition_operator(
            item.get("operator", item.get("op")),
            node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
            key=f"conditions[{index}].operator",
        )
        value_source = _value_source_from_mapping(
            item,
            value_key="value",
            value_source_key="value_source",
            value_field_key="value_field",
            node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
        )
        if (
            value_source.field is not None
            and find_field(input_ref.schema, value_source.field) is None
        ):
            raise _NodeValidationError(f"Field does not exist: {value_source.field}")
        case_sensitive = item.get("case_sensitive", True)
        if not isinstance(case_sensitive, bool):
            raise _NodeValidationError(
                "AdvancedFilterRowsNode condition.case_sensitive must be a boolean"
            )
        conditions.append(
            {
                "field": field,
                "operator": operator,
                "value_source": value_source,
                "case_sensitive": case_sensitive,
            }
        )
    return conditions


def _advanced_filter_output_fields(
    config: dict[str, Any],
    input_ref: TableRefModel,
) -> list[str]:
    raw_output_fields = config.get("output_fields")
    if raw_output_fields is None or raw_output_fields == []:
        return [field.name for field in input_ref.schema]
    output_fields = _string_list_config(
        config,
        "output_fields",
        node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
    )
    missing_fields = [
        field_name
        for field_name in output_fields
        if not has_field(input_ref.schema, field_name)
    ]
    if missing_fields:
        raise _NodeValidationError(
            f"Fields do not exist: {', '.join(missing_fields)}"
        )
    return output_fields


def _advanced_filter_row_matches(
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
