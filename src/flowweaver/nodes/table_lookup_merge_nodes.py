from __future__ import annotations

from typing import Any, TypedDict

from flowweaver.nodes.builtin_table_node_types import (
    LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
    MERGE_COLUMNS_NODE_TYPE,
)
from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_config import (
    bool_config as _bool_config,
)
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
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
    replace_field_schema,
)
from flowweaver.protocols.enums import TableStorageKind
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class _LookupMatchedOutputFields(TypedDict):
    field: str
    value: str | None
    row: str | None
    status: str | None


class LookupMatchedFieldNameNodeHandler:
    node_type = LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        allowed_storage_kinds = (
            TableStorageKind.RUNTIME_SQL,
            TableStorageKind.MEMORY,
        )
        if task.input_slot_bindings:
            main_ref = context.require_input_slot(
                task,
                "in",
                node_type=self.node_type,
                allowed_storage_kinds=allowed_storage_kinds,
            )
            lookup_ref = context.require_input_slot(
                task,
                "lookup",
                node_type=self.node_type,
                allowed_storage_kinds=allowed_storage_kinds,
            )
        else:
            if len(task.input_refs) != 2:
                raise _NodeValidationError(
                    "LookupMatchedFieldNameNode requires main and lookup input_refs"
                )
            main_ref = context.input_ref(task.input_refs[0])
            lookup_ref = context.input_ref(task.input_refs[1])
        source_field = _node_string_config(
            task.config,
            "source_field",
            node_type=self.node_type,
        )
        if find_field(main_ref.schema, source_field) is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        lookup_fields = _string_list_config(
            task.config,
            "lookup_fields",
            node_type=self.node_type,
        )
        missing_lookup_fields = [
            field_name
            for field_name in lookup_fields
            if not has_field(lookup_ref.schema, field_name)
        ]
        if missing_lookup_fields:
            raise _NodeValidationError(
                f"Fields do not exist: {', '.join(missing_lookup_fields)}"
            )
        match_mode = _enum_config(
            task.config,
            "match_mode",
            default="equals",
            allowed={"equals"},
            node_type=self.node_type,
        )
        multi_match_policy = _enum_config(
            task.config,
            "multi_match_policy",
            default="first",
            allowed={"first", "last", "error"},
            node_type=self.node_type,
        )
        output_fields = _lookup_matched_output_fields(task.config)
        output_schema = _lookup_matched_output_schema(main_ref.schema, output_fields)
        no_match_value = task.config.get("no_match_value", "")
        lookup_index = _lookup_matched_field_index(
            context,
            lookup_ref=lookup_ref,
            lookup_fields=lookup_fields,
            match_mode=match_mode,
        )

        def output_batches():
            for rows in context.iter_row_batches(main_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    matches = lookup_index.get(row.get(source_field), [])
                    if len(matches) > 1 and multi_match_policy == "error":
                        raise _NodeValidationError(
                            "LookupMatchedFieldNameNode found multiple matches"
                        )
                    match = _lookup_matched_select_match(
                        matches,
                        multi_match_policy=multi_match_policy,
                    )
                    output_rows.append(
                        dict(row)
                        | _lookup_matched_values(
                            match,
                            match_count=len(matches),
                            output_fields=output_fields,
                            no_match_value=no_match_value,
                        )
                    )
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=output_schema,
                row_batches=output_batches(),
            )
        ]


class MergeColumnsNodeHandler:
    node_type = MERGE_COLUMNS_NODE_TYPE

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
        fields = _string_list_config(
            task.config,
            "fields",
            node_type=self.node_type,
        )
        missing_fields = [
            field_name
            for field_name in fields
            if not has_field(input_ref.schema, field_name)
        ]
        if missing_fields:
            raise _NodeValidationError(
                f"Fields do not exist: {', '.join(missing_fields)}"
            )
        separators = _merge_columns_separators(task.config, field_count=len(fields))
        output_field = _optional_node_string_config(
            task.config,
            "output_field",
            default="merged",
            node_type=self.node_type,
        )
        conflict_mode = _enum_config(
            task.config,
            "conflict_mode",
            default="error",
            allowed={"error", "overwrite"},
            node_type=self.node_type,
        )
        output_schema = _merge_columns_output_schema(
            input_ref.schema,
            output_field=output_field,
            conflict_mode=conflict_mode,
        )
        skip_empty = _bool_config(task.config, "skip_empty", default=False)
        trim_value = _bool_config(task.config, "trim_value", default=False)
        empty_placeholder = task.config.get("empty_placeholder", "")

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                yield [
                    row
                    | {
                        output_field: _merge_columns_value(
                            row,
                            fields=fields,
                            separators=separators,
                            skip_empty=skip_empty,
                            trim_value=trim_value,
                            empty_placeholder=empty_placeholder,
                        )
                    }
                    for row in rows
                ]

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )


def _lookup_matched_output_fields(config: dict[str, Any]) -> _LookupMatchedOutputFields:
    output_fields: _LookupMatchedOutputFields = {
        "field": _optional_node_string_config(
            config,
            "output_field",
            default="matched_field",
            node_type=LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
        ),
        "value": None,
        "row": None,
        "status": None,
    }
    if _bool_config(config, "output_match_value", default=False):
        output_fields["value"] = _optional_node_string_config(
            config,
            "match_value_field",
            default="matched_value",
            node_type=LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
        )
    if _bool_config(config, "output_match_row", default=False):
        output_fields["row"] = _optional_node_string_config(
            config,
            "match_row_field",
            default="matched_row",
            node_type=LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
        )
    if _bool_config(config, "output_status", default=True):
        output_fields["status"] = _optional_node_string_config(
            config,
            "status_field",
            default="match_status",
            node_type=LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
        )
    return output_fields


def _lookup_matched_output_schema(
    input_schema: list[FieldSchemaModel],
    output_fields: _LookupMatchedOutputFields,
) -> list[FieldSchemaModel]:
    field_names_to_add = [
        field_name
        for field_name in (
            output_fields["field"],
            output_fields["value"],
            output_fields["row"],
            output_fields["status"],
        )
        if field_name is not None
    ]
    duplicate_field_names = [
        field_name
        for index, field_name in enumerate(field_names_to_add)
        if field_name in field_names_to_add[:index]
    ]
    if duplicate_field_names:
        raise _NodeValidationError(
            f"LookupMatchedFieldNameNode output fields are duplicated: "
            f"{', '.join(duplicate_field_names)}"
        )
    existing_fields = [
        field_name
        for field_name in field_names_to_add
        if has_field(input_schema, field_name)
    ]
    if existing_fields:
        raise _NodeValidationError(
            f"Fields already exist: {', '.join(existing_fields)}"
        )
    schema = list(input_schema)
    schema = append_field(
        schema,
        name=output_fields["field"],
        data_type="TEXT",
        nullable=True,
    )
    if output_fields["value"] is not None:
        schema = append_field(
            schema,
            name=output_fields["value"],
            data_type="TEXT",
            nullable=True,
        )
    if output_fields["row"] is not None:
        schema = append_field(
            schema,
            name=output_fields["row"],
            data_type="INTEGER",
            nullable=True,
        )
    if output_fields["status"] is not None:
        schema = append_field(
            schema,
            name=output_fields["status"],
            data_type="TEXT",
            nullable=False,
        )
    return schema


def _lookup_matched_field_index(
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


def _lookup_matched_select_match(
    matches: list[dict[str, Any]],
    *,
    multi_match_policy: str,
) -> dict[str, Any] | None:
    if not matches:
        return None
    if multi_match_policy == "last":
        return matches[-1]
    return matches[0]


def _lookup_matched_values(
    match: dict[str, Any] | None,
    *,
    match_count: int,
    output_fields: _LookupMatchedOutputFields,
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


def _merge_columns_separators(
    config: dict[str, Any],
    *,
    field_count: int,
) -> list[str]:
    separator_count = max(0, field_count - 1)
    raw_separators = config.get("separators", [""] * separator_count)
    if isinstance(raw_separators, str):
        return [raw_separators] * separator_count
    if not isinstance(raw_separators, list):
        raise _NodeValidationError("MergeColumnsNode config.separators must be a list")
    if separator_count == 0:
        return []
    if len(raw_separators) == 1:
        separator = raw_separators[0]
        if not isinstance(separator, str):
            raise _NodeValidationError(
                "MergeColumnsNode config.separators must contain strings"
            )
        return [separator] * separator_count
    if len(raw_separators) != separator_count:
        raise _NodeValidationError(
            "MergeColumnsNode config.separators must contain one separator or "
            "field_count - 1 separators"
        )
    separators: list[str] = []
    for separator in raw_separators:
        if not isinstance(separator, str):
            raise _NodeValidationError(
                "MergeColumnsNode config.separators must contain strings"
            )
        separators.append(separator)
    return separators


def _merge_columns_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    output_field: str,
    conflict_mode: str,
) -> list[FieldSchemaModel]:
    if has_field(input_schema, output_field):
        if conflict_mode == "error":
            raise _NodeValidationError(f"Field already exists: {output_field}")
        return replace_field_schema(
            input_schema,
            output_field,
            data_type="TEXT",
            nullable=True,
        )
    return append_field(
        input_schema,
        name=output_field,
        data_type="TEXT",
        nullable=True,
    )


def _merge_columns_value(
    row: dict[str, Any],
    *,
    fields: list[str],
    separators: list[str],
    skip_empty: bool,
    trim_value: bool,
    empty_placeholder: Any,
) -> str:
    values: list[str] = []
    for field_name in fields:
        value = row.get(field_name)
        if value is None:
            text_value = ""
        else:
            text_value = str(value)
        if trim_value:
            text_value = text_value.strip()
        if _is_empty_cell(text_value):
            if skip_empty:
                continue
            text_value = "" if empty_placeholder is None else str(empty_placeholder)
        values.append(text_value)
    if skip_empty:
        separator = separators[0] if separators else ""
        return separator.join(values)
    merged = ""
    for index, value in enumerate(values):
        if index > 0:
            merged += separators[index - 1]
        merged += value
    return merged
