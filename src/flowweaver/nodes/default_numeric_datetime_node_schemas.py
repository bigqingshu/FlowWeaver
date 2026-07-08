from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _numeric_column_operation_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
                required=True,
            ),
            "operation": NodeConfigFieldSpec(
                type="enum",
                title="Operation",
                required=True,
                default="add",
                enum=(
                    "add",
                    "subtract",
                    "multiply",
                    "divide",
                    "sequence",
                    "round",
                    "floor",
                    "ceil",
                ),
            ),
            "operand_source": NodeConfigFieldSpec(
                type="enum",
                title="Operand Source",
                default="literal",
                enum=("literal", "row_field", "row_number", "sequence"),
            ),
            "operand_value": NodeConfigFieldSpec(
                type="object",
                title="Operand Value",
                default=0,
            ),
            "operand_field": NodeConfigFieldSpec(
                type="string",
                title="Operand Field",
            ),
            "output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Output Mode",
                default="overwrite",
                enum=("overwrite", "new_field"),
            ),
            "output_field": NodeConfigFieldSpec(
                type="string",
                title="Output Field",
            ),
            "non_number_policy": NodeConfigFieldSpec(
                type="enum",
                title="Non Number Policy",
                default="error",
                enum=("error", "empty", "fixed", "keep_original"),
            ),
            "non_number_fixed": NodeConfigFieldSpec(
                type="object",
                title="Non Number Fixed",
            ),
            "divide_zero_policy": NodeConfigFieldSpec(
                type="enum",
                title="Divide Zero Policy",
                default="error",
                enum=("error", "empty", "fixed", "keep_original"),
            ),
            "divide_zero_fixed": NodeConfigFieldSpec(
                type="object",
                title="Divide Zero Fixed",
            ),
            "decimal_places": NodeConfigFieldSpec(
                type="integer",
                title="Decimal Places",
                minimum=0,
            ),
            "range_mode": NodeConfigFieldSpec(
                type="enum",
                title="Range Mode",
                default="all",
                enum=("all", "row_range", "reference_non_empty"),
            ),
            "start_row": NodeConfigFieldSpec(
                type="integer",
                title="Start Row",
                default=1,
                minimum=1,
            ),
            "end_row": NodeConfigFieldSpec(
                type="integer",
                title="End Row",
                minimum=1,
            ),
            "reference_field": NodeConfigFieldSpec(
                type="string",
                title="Reference Field",
            ),
            "sequence_start": NodeConfigFieldSpec(
                type="object",
                title="Sequence Start",
                default=1,
            ),
            "sequence_step": NodeConfigFieldSpec(
                type="object",
                title="Sequence Step",
                default=1,
            ),
        }
    )


def _add_current_datetime_column_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Output Mode",
                required=True,
                default="new_field",
                enum=("new_field", "overwrite"),
            ),
            "new_field": NodeConfigFieldSpec(
                type="string",
                title="New Field",
                default="current_datetime",
            ),
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
            ),
            "time_mode": NodeConfigFieldSpec(
                type="enum",
                title="Time Mode",
                default="fixed",
                enum=("fixed", "per_row"),
            ),
            "format_mode": NodeConfigFieldSpec(
                type="enum",
                title="Format Mode",
                default="iso",
                enum=("iso", "strftime", "template"),
            ),
            "template": NodeConfigFieldSpec(
                type="string",
                title="Template",
                default="{datetime}",
            ),
            "strftime_template": NodeConfigFieldSpec(
                type="string",
                title="Strftime Template",
                default="%Y-%m-%d %H:%M:%S",
            ),
        }
    )


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
