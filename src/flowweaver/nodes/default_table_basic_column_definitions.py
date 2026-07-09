from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import (
    ADD_COLUMNS_NODE_TYPE,
    COPY_COLUMN_NODE_TYPE,
    DELETE_COLUMNS_NODE_TYPE,
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
    RENAME_COLUMNS_NODE_TYPE,
    REORDER_COLUMNS_NODE_TYPE,
)
from flowweaver.nodes.default_node_schemas import (
    _add_columns_schema,
    _copy_column_schema,
    _delete_columns_schema,
    _filter_rows_schema,
    _generate_test_table_schema,
    _rename_columns_schema,
    _reorder_columns_schema,
)
from flowweaver.nodes.default_table_slots import (
    _single_transform_input_table_slots,
    _single_transform_output_table_slots,
    _source_output_table_slot,
)
from flowweaver.nodes.registry import NodeDefinitionSpec, NodePortSpec


def default_table_basic_column_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
        NodeDefinitionSpec(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_version="1.0",
            display_name="Generate Test Table",
            output_ports=(NodePortSpec("out"),),
            output_table_slots=(
                _source_output_table_slot(
                    "out",
                    display_name="Current table",
                    description="Generated table for the main workflow chain.",
                ),
            ),
            config_schema=_generate_test_table_schema(),
        ),
        NodeDefinitionSpec(
            node_type=FILTER_ROWS_NODE_TYPE,
            node_version="1.0",
            display_name="Filter Rows",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_filter_rows_schema(),
        ),
        NodeDefinitionSpec(
            node_type=ADD_COLUMNS_NODE_TYPE,
            node_version="1.0",
            display_name="Add Column",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_add_columns_schema(),
        ),
        NodeDefinitionSpec(
            node_type=DELETE_COLUMNS_NODE_TYPE,
            node_version="1.0",
            display_name="Delete Columns",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_delete_columns_schema(),
        ),
        NodeDefinitionSpec(
            node_type=COPY_COLUMN_NODE_TYPE,
            node_version="1.0",
            display_name="Copy Column",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_copy_column_schema(),
        ),
        NodeDefinitionSpec(
            node_type=REORDER_COLUMNS_NODE_TYPE,
            node_version="1.0",
            display_name="Reorder Columns",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_reorder_columns_schema(),
        ),
        NodeDefinitionSpec(
            node_type=RENAME_COLUMNS_NODE_TYPE,
            node_version="1.0",
            display_name="Rename Columns",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_rename_columns_schema(),
        ),
    )
