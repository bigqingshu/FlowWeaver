from __future__ import annotations

from flowweaver.node_executor.builtin_fault import (
    DELAY_TEST_NODE_TYPE,
    FAULT_TEST_NODE_TYPE,
)
from flowweaver.nodes.builtin_shared_table import (
    PUBLISH_SHARED_TABLES_NODE_TYPE,
    READ_SHARED_TABLES_NODE_TYPE,
)
from flowweaver.nodes.builtin_sql import SQL_MAPPING_NODE_TYPE
from flowweaver.nodes.builtin_table_node_types import (
    BATCH_RENAME_FILES_NODE_TYPE,
    CONDITION_FLAG_NODE_TYPE,
    CONDITIONAL_JUMP_NODE_TYPE,
    JUMP_ANCHOR_NODE_TYPE,
    LIST_FILES_NODE_TYPE,
    LOOP_JUDGE_NODE_TYPE,
    LOOP_START_NODE_TYPE,
    PLUGIN_NODE_TYPE,
    SAVE_MEMORY_TABLE_NODE_TYPE,
    SAVE_RUN_TABLE_NODE_TYPE,
    SUB_WORKFLOW_NODE_TYPE,
    UNCONDITIONAL_JUMP_NODE_TYPE,
    WRITE_BACK_TABLE_NODE_TYPE,
    WRITE_SELECTED_COLUMNS_NODE_TYPE,
)
from flowweaver.nodes.default_node_schemas import (
    _batch_rename_files_schema,
    _condition_flag_schema,
    _conditional_jump_schema,
    _jump_anchor_schema,
    _list_files_schema,
    _loop_judge_schema,
    _loop_start_schema,
    _plugin_node_schema,
    _publish_shared_tables_schema,
    _read_shared_tables_schema,
    _save_memory_table_schema,
    _save_run_table_schema,
    _sql_mapping_schema,
    _subworkflow_schema,
    _unconditional_jump_schema,
    _write_back_table_schema,
    _write_selected_columns_schema,
)
from flowweaver.nodes.default_table_slots import (
    _auxiliary_output_table_slot as _auxiliary_output_table_slot,
)
from flowweaver.nodes.default_table_slots import (
    _current_output_table_slot as _current_output_table_slot,
)
from flowweaver.nodes.default_table_slots import (
    _input_table_slot as _input_table_slot,
)
from flowweaver.nodes.default_table_slots import (
    _single_transform_input_table_slots as _single_transform_input_table_slots,
)
from flowweaver.nodes.default_table_slots import (
    _single_transform_output_table_slots as _single_transform_output_table_slots,
)
from flowweaver.nodes.default_table_slots import (
    _source_output_table_slot as _source_output_table_slot,
)
from flowweaver.nodes.default_table_transform_definitions import (
    default_table_transform_node_definitions,
)
from flowweaver.nodes.registry import (
    NodeDefinitionSpec,
    NodePortSpec,
    NodeRegistry,
)


def create_default_node_registry() -> NodeRegistry:
    registry = NodeRegistry()
    for definition in default_node_definitions():
        registry.register(definition)
    return registry


def default_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
        *default_table_transform_node_definitions(),
        NodeDefinitionSpec(
            node_type=CONDITION_FLAG_NODE_TYPE,
            node_version="1.0",
            display_name="Condition Flag",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_condition_flag_schema(),
        ),
        NodeDefinitionSpec(
            node_type=JUMP_ANCHOR_NODE_TYPE,
            node_version="1.0",
            display_name="Jump Anchor",
            output_ports=(NodePortSpec("status"),),
            config_schema=_jump_anchor_schema(),
        ),
        NodeDefinitionSpec(
            node_type=UNCONDITIONAL_JUMP_NODE_TYPE,
            node_version="1.0",
            display_name="Unconditional Jump",
            input_ports=(NodePortSpec("in"),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_unconditional_jump_schema(),
        ),
        NodeDefinitionSpec(
            node_type=CONDITIONAL_JUMP_NODE_TYPE,
            node_version="1.0",
            display_name="Conditional Jump",
            input_ports=(NodePortSpec("condition", required=True),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_conditional_jump_schema(),
        ),
        NodeDefinitionSpec(
            node_type=LOOP_START_NODE_TYPE,
            node_version="1.0",
            display_name="Loop Start",
            input_ports=(NodePortSpec("in"),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_loop_start_schema(),
        ),
        NodeDefinitionSpec(
            node_type=LOOP_JUDGE_NODE_TYPE,
            node_version="1.0",
            display_name="Loop Judge",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_loop_judge_schema(),
        ),
        NodeDefinitionSpec(
            node_type=SUB_WORKFLOW_NODE_TYPE,
            node_version="1.0",
            display_name="Sub Workflow",
            input_ports=(NodePortSpec("in"),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_subworkflow_schema(),
        ),
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
        NodeDefinitionSpec(
            node_type=LIST_FILES_NODE_TYPE,
            node_version="1.0",
            display_name="List Files",
            output_ports=(NodePortSpec("out"),),
            output_table_slots=(
                _source_output_table_slot(
                    "out",
                    display_name="File list table",
                    description="Generated file metadata table.",
                ),
            ),
            config_schema=_list_files_schema(),
        ),
        NodeDefinitionSpec(
            node_type=BATCH_RENAME_FILES_NODE_TYPE,
            node_version="1.0",
            display_name="Batch Rename Files",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_batch_rename_files_schema(),
        ),
        NodeDefinitionSpec(
            node_type=PLUGIN_NODE_TYPE,
            node_version="1.0",
            display_name="Plugin Node",
            input_ports=(NodePortSpec("in"),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_plugin_node_schema(),
        ),
        NodeDefinitionSpec(
            node_type=PUBLISH_SHARED_TABLES_NODE_TYPE,
            node_version="1.0",
            display_name="Publish Shared Tables",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_publish_shared_tables_schema(),
        ),
        NodeDefinitionSpec(
            node_type=READ_SHARED_TABLES_NODE_TYPE,
            node_version="1.0",
            display_name="Read Shared Tables",
            output_ports=(NodePortSpec("out"),),
            config_schema=_read_shared_tables_schema(),
        ),
        NodeDefinitionSpec(
            node_type=SQL_MAPPING_NODE_TYPE,
            node_version="1.0",
            display_name="SQL Mapping",
            output_ports=(NodePortSpec("out"),),
            config_schema=_sql_mapping_schema(),
        ),
        NodeDefinitionSpec(
            node_type=DELAY_TEST_NODE_TYPE,
            node_version="1.0",
            display_name="Delay Test",
            output_ports=(NodePortSpec("out"),),
        ),
        NodeDefinitionSpec(
            node_type=FAULT_TEST_NODE_TYPE,
            node_version="1.0",
            display_name="Fault Test",
            output_ports=(NodePortSpec("out"),),
        ),
    )




