from __future__ import annotations

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
