from __future__ import annotations

from flowweaver.nodes.default_row_edit_node_schemas import (
    _copy_rows_schema as _copy_rows_schema,
)
from flowweaver.nodes.default_row_edit_node_schemas import (
    _delete_rows_schema as _delete_rows_schema,
)
from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _unpivot_rows_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "value_fields": NodeConfigFieldSpec(
                type="array",
                title="Value Fields",
                required=True,
                item_type="string",
            ),
            "keep_fields": NodeConfigFieldSpec(
                type="array",
                title="Keep Fields",
                item_type="string",
            ),
            "output_value_field": NodeConfigFieldSpec(
                type="string",
                title="Output Value Field",
                default="value",
            ),
            "output_source_field": NodeConfigFieldSpec(
                type="boolean",
                title="Output Source Field",
                default=True,
            ),
            "source_field_name": NodeConfigFieldSpec(
                type="string",
                title="Source Field Name",
                default="source_field",
            ),
            "output_original_row": NodeConfigFieldSpec(
                type="boolean",
                title="Output Original Row",
                default=False,
            ),
            "original_row_field": NodeConfigFieldSpec(
                type="string",
                title="Original Row Field",
                default="original_row",
            ),
            "output_status": NodeConfigFieldSpec(
                type="boolean",
                title="Output Status",
                default=False,
            ),
            "status_field": NodeConfigFieldSpec(
                type="string",
                title="Status Field",
                default="mapping_status",
            ),
            "empty_mode": NodeConfigFieldSpec(
                type="enum",
                title="Empty Mode",
                default="skip",
                enum=("skip", "empty", "fixed"),
            ),
            "empty_fixed": NodeConfigFieldSpec(
                type="object",
                title="Empty Fixed",
            ),
            "trim_value": NodeConfigFieldSpec(
                type="boolean",
                title="Trim Value",
                default=False,
            ),
            "start_row": NodeConfigFieldSpec(
                type="integer",
                title="Start Row",
                default=1,
                minimum=1,
            ),
            "end_mode": NodeConfigFieldSpec(
                type="enum",
                title="End Mode",
                default="to_end",
                enum=("to_end", "count", "end_row"),
            ),
            "count": NodeConfigFieldSpec(
                type="integer",
                title="Count",
                minimum=1,
            ),
            "end_row": NodeConfigFieldSpec(
                type="integer",
                title="End Row",
                minimum=1,
            ),
        }
    )


def _deduplicate_rows_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "dedupe_mode": NodeConfigFieldSpec(
                type="enum",
                title="Dedupe Mode",
                required=True,
                default="key_fields",
                enum=("key_fields", "entire_row"),
            ),
            "key_fields": NodeConfigFieldSpec(
                type="array",
                title="Key Fields",
                item_type="string",
                description="Field names used as the duplicate key.",
            ),
            "trim": NodeConfigFieldSpec(
                type="boolean",
                title="Trim",
                default=False,
            ),
            "ignore_case": NodeConfigFieldSpec(
                type="boolean",
                title="Ignore Case",
                default=False,
            ),
            "empty_key_policy": NodeConfigFieldSpec(
                type="enum",
                title="Empty Key Policy",
                default="include",
                enum=("include", "skip"),
            ),
            "keep_policy": NodeConfigFieldSpec(
                type="enum",
                title="Keep Policy",
                default="first",
                enum=("first", "last", "all"),
            ),
            "output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Output Mode",
                default="dedupe",
                enum=("dedupe", "mark"),
            ),
            "add_marker_columns": NodeConfigFieldSpec(
                type="boolean",
                title="Add Marker Columns",
                default=False,
            ),
            "duplicate_group_field": NodeConfigFieldSpec(
                type="string",
                title="Duplicate Group Field",
                default="_duplicate_group",
            ),
            "duplicate_status_field": NodeConfigFieldSpec(
                type="string",
                title="Duplicate Status Field",
                default="_duplicate_status",
            ),
            "duplicate_index_field": NodeConfigFieldSpec(
                type="string",
                title="Duplicate Index Field",
                default="_duplicate_index",
            ),
            "duplicate_count_field": NodeConfigFieldSpec(
                type="string",
                title="Duplicate Count Field",
                default="_duplicate_count",
            ),
            "keep_flag_field": NodeConfigFieldSpec(
                type="string",
                title="Keep Flag Field",
                default="_keep_row",
            ),
        }
    )


def _advanced_filter_rows_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "logic": NodeConfigFieldSpec(
                type="enum",
                title="Logic",
                default="and",
                enum=("and", "or"),
            ),
            "conditions": NodeConfigFieldSpec(
                type="array",
                title="Conditions",
                item_type="object",
                description=(
                    "Each condition supports field, operator, value, "
                    "value_source, value_field, and case_sensitive."
                ),
            ),
            "output_fields": NodeConfigFieldSpec(
                type="array",
                title="Output Fields",
                item_type="string",
            ),
            "result_limit": NodeConfigFieldSpec(
                type="integer",
                title="Result Limit",
                minimum=0,
            ),
            "max_intermediate": NodeConfigFieldSpec(
                type="integer",
                title="Max Intermediate",
                minimum=1,
            ),
            "remove_duplicates": NodeConfigFieldSpec(
                type="boolean",
                title="Remove Duplicates",
                default=False,
            ),
        }
    )
