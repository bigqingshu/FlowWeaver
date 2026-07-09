from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


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
