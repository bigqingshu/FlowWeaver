from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import (
    ADVANCED_FILTER_ROWS_NODE_TYPE,
    COPY_ROWS_NODE_TYPE,
    DEDUPLICATE_ROWS_NODE_TYPE,
    DELETE_ROWS_NODE_TYPE,
    UNPIVOT_ROWS_NODE_TYPE,
)
from flowweaver.nodes.default_node_schemas import (
    _advanced_filter_rows_schema,
    _copy_rows_schema,
    _deduplicate_rows_schema,
    _delete_rows_schema,
    _unpivot_rows_schema,
)
from flowweaver.nodes.default_table_slots import (
    _single_transform_input_table_slots,
    _single_transform_output_table_slots,
)
from flowweaver.nodes.registry import NodeDefinitionSpec, NodePortSpec


def default_table_row_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
        NodeDefinitionSpec(
            node_type=DELETE_ROWS_NODE_TYPE,
            node_version="1.0",
            display_name="Delete Rows",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_delete_rows_schema(),
        ),
        NodeDefinitionSpec(
            node_type=COPY_ROWS_NODE_TYPE,
            node_version="1.0",
            display_name="Copy Rows",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_copy_rows_schema(),
        ),
        NodeDefinitionSpec(
            node_type=UNPIVOT_ROWS_NODE_TYPE,
            node_version="1.0",
            display_name="Unpivot Rows",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_unpivot_rows_schema(),
        ),
        NodeDefinitionSpec(
            node_type=DEDUPLICATE_ROWS_NODE_TYPE,
            node_version="1.0",
            display_name="Deduplicate Rows",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_deduplicate_rows_schema(),
        ),
        NodeDefinitionSpec(
            node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
            node_version="1.0",
            display_name="Advanced Filter Rows",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_advanced_filter_rows_schema(),
        ),
    )
