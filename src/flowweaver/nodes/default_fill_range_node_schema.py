from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _fill_range_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "start_field": NodeConfigFieldSpec(
                type="string",
                title="Start Field",
                required=True,
            ),
            "end_field": NodeConfigFieldSpec(
                type="string",
                title="End Field",
                description="Defaults to start_field when omitted.",
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
            "overwrite_rule": NodeConfigFieldSpec(
                type="enum",
                title="Overwrite Rule",
                default="all",
                enum=("all", "empty_only"),
            ),
            "max_cells": NodeConfigFieldSpec(
                type="integer",
                title="Max Cells",
                default=100000,
                minimum=1,
            ),
        }
    )
