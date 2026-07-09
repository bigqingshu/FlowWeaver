from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _condition_flag_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "flag_name": NodeConfigFieldSpec(
                type="string",
                title="Flag Name",
                required=True,
                default="condition",
            ),
            "condition_type": NodeConfigFieldSpec(
                type="enum",
                title="Condition Type",
                required=True,
                default="row_count",
                enum=("row_count", "field_exists", "field_value"),
            ),
            "field": NodeConfigFieldSpec(
                type="string",
                title="Field",
            ),
            "operator": NodeConfigFieldSpec(
                type="enum",
                title="Operator",
                default="GE",
                enum=(
                    "EQ",
                    "NE",
                    "GT",
                    "GE",
                    "LT",
                    "LE",
                    "CONTAINS",
                    "IS_NULL",
                    "IS_EMPTY",
                ),
            ),
            "value": NodeConfigFieldSpec(
                type="object",
                title="Value",
                default=1,
            ),
            "value_source": NodeConfigFieldSpec(
                type="object",
                title="Value Source",
                description=(
                    "Literal values or same-row field objects are supported by "
                    "runtime."
                ),
            ),
            "value_field": NodeConfigFieldSpec(
                type="string",
                title="Value Field",
                description="Shortcut for same-row field comparison.",
            ),
            "aggregation": NodeConfigFieldSpec(
                type="enum",
                title="Aggregation",
                default="any",
                enum=("any", "all", "first", "count"),
            ),
            "case_sensitive": NodeConfigFieldSpec(
                type="boolean",
                title="Case Sensitive",
                default=True,
            ),
            "true_value": NodeConfigFieldSpec(
                type="object",
                title="True Value",
                default=True,
            ),
            "false_value": NodeConfigFieldSpec(
                type="object",
                title="False Value",
                default=False,
            ),
        }
    )
