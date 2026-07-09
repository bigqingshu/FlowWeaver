from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _fill_cells_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
                required=True,
            ),
            "value_source": NodeConfigFieldSpec(
                type="object",
                title="Value Source",
                description=(
                    "Literal values or row_field objects are supported by runtime."
                ),
            ),
            "manual_value": NodeConfigFieldSpec(
                type="object",
                title="Manual Value",
                description="Fallback literal value when value_source is omitted.",
            ),
            "start_row": NodeConfigFieldSpec(
                type="integer",
                title="Start Row",
                default=1,
                minimum=1,
            ),
            "direction": NodeConfigFieldSpec(
                type="enum",
                title="Direction",
                default="down",
                enum=("down", "up"),
            ),
            "count": NodeConfigFieldSpec(
                type="integer",
                title="Count",
                minimum=1,
            ),
            "overwrite_rule": NodeConfigFieldSpec(
                type="enum",
                title="Overwrite Rule",
                default="all",
                enum=("all", "empty_only"),
            ),
        }
    )
