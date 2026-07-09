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
