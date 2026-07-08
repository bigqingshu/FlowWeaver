from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import (
    SAVE_MEMORY_TABLE_NODE_TYPE,
    SAVE_RUN_TABLE_NODE_TYPE,
    WRITE_BACK_TABLE_NODE_TYPE,
    WRITE_SELECTED_COLUMNS_NODE_TYPE,
)
from flowweaver.nodes.default_node_schemas import (
    _save_memory_table_schema,
    _save_run_table_schema,
    _write_back_table_schema,
    _write_selected_columns_schema,
)
from flowweaver.nodes.default_table_slots import (
    _auxiliary_output_table_slot,
    _current_output_table_slot,
    _input_table_slot,
)
from flowweaver.nodes.registry import NodeDefinitionSpec, NodePortSpec


def default_write_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
        NodeDefinitionSpec(
            node_type=SAVE_MEMORY_TABLE_NODE_TYPE,
            node_version="1.0",
            display_name="Save Memory Table",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"), NodePortSpec("memory")),
            input_table_slots=(
                _input_table_slot(
                    "in",
                    display_name="Input table",
                    description="Table to pass through and save as memory output.",
                ),
            ),
            output_table_slots=(
                _current_output_table_slot(
                    "out",
                    display_name="Current table",
                    description="Original current table passed to the main chain.",
                ),
                _auxiliary_output_table_slot(
                    "memory",
                    display_name="Memory table",
                    description="Auxiliary memory table saved by the node.",
                    allow_new_memory=True,
                    allow_existing_memory=True,
                ),
            ),
            config_schema=_save_memory_table_schema(),
        ),
        NodeDefinitionSpec(
            node_type=SAVE_RUN_TABLE_NODE_TYPE,
            node_version="1.0",
            display_name="Save Run Table",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"), NodePortSpec("transit")),
            config_schema=_save_run_table_schema(),
        ),
        NodeDefinitionSpec(
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            node_version="1.0",
            display_name="Write Selected Columns",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_write_selected_columns_schema(),
        ),
        NodeDefinitionSpec(
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
            node_version="1.0",
            display_name="Write Back Table",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_write_back_table_schema(),
        ),
    )
