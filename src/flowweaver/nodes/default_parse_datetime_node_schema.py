from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _parse_datetime_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "source_field": NodeConfigFieldSpec(
                type="string",
                title="Source Field",
                required=True,
            ),
            "time_source_field": NodeConfigFieldSpec(
                type="string",
                title="Time Source Field",
            ),
            "use_separate_time_field": NodeConfigFieldSpec(
                type="boolean",
                title="Use Separate Time Field",
                default=False,
            ),
            "parse_type": NodeConfigFieldSpec(
                type="enum",
                title="Parse Type",
                default="datetime",
                enum=("date", "time", "datetime"),
            ),
            "input_structure": NodeConfigFieldSpec(
                type="enum",
                title="Input Structure",
                default="auto",
                enum=("auto", "strptime"),
            ),
            "input_format": NodeConfigFieldSpec(
                type="string",
                title="Input Format",
            ),
            "date_order": NodeConfigFieldSpec(
                type="enum",
                title="Date Order",
                default="ymd",
                enum=("ymd", "mdy", "dmy"),
            ),
            "output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Output Mode",
                default="new_field",
                enum=("new_field", "overwrite_source", "overwrite"),
            ),
            "new_field": NodeConfigFieldSpec(
                type="string",
                title="New Field",
                default="parsed_datetime",
            ),
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
            ),
            "output_template": NodeConfigFieldSpec(
                type="string",
                title="Output Template",
                default="%Y-%m-%d",
            ),
            "time_output_template": NodeConfigFieldSpec(
                type="string",
                title="Time Output Template",
                default="%H:%M:%S",
            ),
            "datetime_output_template": NodeConfigFieldSpec(
                type="string",
                title="DateTime Output Template",
                default="%Y-%m-%d %H:%M:%S",
            ),
            "output_status": NodeConfigFieldSpec(
                type="boolean",
                title="Output Status",
                default=True,
            ),
            "status_field": NodeConfigFieldSpec(
                type="string",
                title="Status Field",
                default="parse_status",
            ),
            "unmatched_mode": NodeConfigFieldSpec(
                type="enum",
                title="Unmatched Mode",
                default="empty",
                enum=("empty", "keep_original", "fixed"),
            ),
            "unmatched_fixed": NodeConfigFieldSpec(
                type="object",
                title="Unmatched Fixed",
            ),
        }
    )
