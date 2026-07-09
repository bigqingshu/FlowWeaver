from __future__ import annotations

from flowweaver.nodes.default_add_columns_node_schema import (
    _add_columns_schema as _add_columns_schema,
)
from flowweaver.nodes.default_copy_column_node_schema import (
    _copy_column_schema as _copy_column_schema,
)
from flowweaver.nodes.default_delete_columns_node_schema import (
    _delete_columns_schema as _delete_columns_schema,
)
from flowweaver.nodes.default_fill_cells_node_schema import (
    _fill_cells_schema as _fill_cells_schema,
)
from flowweaver.nodes.default_fill_range_node_schema import (
    _fill_range_schema as _fill_range_schema,
)
from flowweaver.nodes.default_fill_sequence_node_schema import (
    _fill_sequence_schema as _fill_sequence_schema,
)
from flowweaver.nodes.default_rename_columns_node_schema import (
    _rename_columns_schema as _rename_columns_schema,
)
from flowweaver.nodes.default_reorder_columns_node_schema import (
    _reorder_columns_schema as _reorder_columns_schema,
)
from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _generate_test_table_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "rows": NodeConfigFieldSpec(
                type="integer",
                title="Rows",
                required=True,
                default=3,
                minimum=0,
            ),
            "seed": NodeConfigFieldSpec(
                type="integer",
                title="Seed",
                default=0,
                minimum=0,
            ),
            "columns": NodeConfigFieldSpec(
                type="array",
                title="Columns",
                default=["row_id", "amount"],
                item_type="string",
                description=(
                    "Runtime also accepts column objects; first UI schema phase "
                    "treats this as a string list."
                ),
            ),
        }
    )


def _filter_rows_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "field": NodeConfigFieldSpec(
                type="string",
                title="Field",
                required=True,
            ),
            "operator": NodeConfigFieldSpec(
                type="enum",
                title="Operator",
                required=True,
                enum=("EQ", "NE", "GT", "GE", "LT", "LE", "CONTAINS", "IS_NULL"),
            ),
            "value": NodeConfigFieldSpec(
                type="object",
                title="Value",
                description=(
                    "Optional comparison value; runtime accepts JSON scalar values."
                ),
            ),
        }
    )
