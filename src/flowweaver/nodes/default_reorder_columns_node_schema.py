from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _reorder_columns_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "order": NodeConfigFieldSpec(
                type="array",
                title="Order",
                required=True,
                item_type="string",
                description="Target column order.",
            ),
            "missing_policy": NodeConfigFieldSpec(
                type="enum",
                title="Missing Policy",
                default="error",
                enum=("error", "skip", "warn"),
            ),
            "unlisted_policy": NodeConfigFieldSpec(
                type="enum",
                title="Unlisted Policy",
                default="append",
                enum=("append", "drop", "error"),
            ),
        }
    )
