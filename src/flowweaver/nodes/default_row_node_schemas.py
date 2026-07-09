from __future__ import annotations

from flowweaver.nodes.default_row_deduplicate_node_schemas import (
    _deduplicate_rows_schema as _deduplicate_rows_schema,
)
from flowweaver.nodes.default_row_edit_node_schemas import (
    _copy_rows_schema as _copy_rows_schema,
)
from flowweaver.nodes.default_row_edit_node_schemas import (
    _delete_rows_schema as _delete_rows_schema,
)
from flowweaver.nodes.default_row_transform_node_schemas import (
    _unpivot_rows_schema as _unpivot_rows_schema,
)
from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _advanced_filter_rows_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "logic": NodeConfigFieldSpec(
                type="enum",
                title="Logic",
                default="and",
                enum=("and", "or"),
            ),
            "conditions": NodeConfigFieldSpec(
                type="array",
                title="Conditions",
                item_type="object",
                description=(
                    "Each condition supports field, operator, value, "
                    "value_source, value_field, and case_sensitive."
                ),
            ),
            "output_fields": NodeConfigFieldSpec(
                type="array",
                title="Output Fields",
                item_type="string",
            ),
            "result_limit": NodeConfigFieldSpec(
                type="integer",
                title="Result Limit",
                minimum=0,
            ),
            "max_intermediate": NodeConfigFieldSpec(
                type="integer",
                title="Max Intermediate",
                minimum=1,
            ),
            "remove_duplicates": NodeConfigFieldSpec(
                type="boolean",
                title="Remove Duplicates",
                default=False,
            ),
        }
    )
