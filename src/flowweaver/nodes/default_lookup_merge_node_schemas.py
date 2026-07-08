from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _lookup_matched_field_name_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "source_field": NodeConfigFieldSpec(
                type="string",
                title="Source Field",
                required=True,
            ),
            "lookup_fields": NodeConfigFieldSpec(
                type="array",
                title="Lookup Fields",
                required=True,
                item_type="string",
            ),
            "match_mode": NodeConfigFieldSpec(
                type="enum",
                title="Match Mode",
                default="equals",
                enum=("equals",),
            ),
            "output_field": NodeConfigFieldSpec(
                type="string",
                title="Output Field",
                default="matched_field",
            ),
            "output_match_value": NodeConfigFieldSpec(
                type="boolean",
                title="Output Match Value",
                default=False,
            ),
            "match_value_field": NodeConfigFieldSpec(
                type="string",
                title="Match Value Field",
                default="matched_value",
            ),
            "output_match_row": NodeConfigFieldSpec(
                type="boolean",
                title="Output Match Row",
                default=False,
            ),
            "match_row_field": NodeConfigFieldSpec(
                type="string",
                title="Match Row Field",
                default="matched_row",
            ),
            "output_status": NodeConfigFieldSpec(
                type="boolean",
                title="Output Status",
                default=True,
            ),
            "status_field": NodeConfigFieldSpec(
                type="string",
                title="Status Field",
                default="match_status",
            ),
            "multi_match_policy": NodeConfigFieldSpec(
                type="enum",
                title="Multi Match Policy",
                default="first",
                enum=("first", "last", "error"),
            ),
            "no_match_value": NodeConfigFieldSpec(
                type="object",
                title="No Match Value",
                default="",
            ),
        }
    )


def _merge_columns_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "fields": NodeConfigFieldSpec(
                type="array",
                title="Fields",
                required=True,
                item_type="string",
            ),
            "separators": NodeConfigFieldSpec(
                type="array",
                title="Separators",
                item_type="string",
                description=(
                    "One separator is repeated between all fields; field_count - 1 "
                    "separators are also supported."
                ),
            ),
            "output_field": NodeConfigFieldSpec(
                type="string",
                title="Output Field",
                default="merged",
            ),
            "skip_empty": NodeConfigFieldSpec(
                type="boolean",
                title="Skip Empty",
                default=False,
            ),
            "trim_value": NodeConfigFieldSpec(
                type="boolean",
                title="Trim Value",
                default=False,
            ),
            "empty_placeholder": NodeConfigFieldSpec(
                type="object",
                title="Empty Placeholder",
                default="",
            ),
            "conflict_mode": NodeConfigFieldSpec(
                type="enum",
                title="Conflict Mode",
                default="error",
                enum=("error", "overwrite"),
            ),
        }
    )
