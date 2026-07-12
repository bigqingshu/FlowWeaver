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
    LIST_FILES_NODE_TYPE,
    PLUGIN_NODE_TYPE,
)
from flowweaver.nodes.default_batch_rename_files_node_schema import (
    _batch_rename_files_schema,
)
from flowweaver.nodes.default_list_files_node_schema import _list_files_schema
from flowweaver.nodes.default_node_schemas import (
    _plugin_node_schema,
    _publish_shared_tables_schema,
    _read_shared_tables_schema,
    _sql_mapping_schema,
)
from flowweaver.nodes.default_table_slots import _source_output_table_slot
from flowweaver.nodes.registry import NodeDefinitionSpec, NodePortSpec


def default_resource_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
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
            category="plugin",
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
            plugin_id="flowweaver.dev_test",
            provider_type="dev_test",
            category="development",
            ui_visibility="hidden",
            output_ports=(NodePortSpec("out"),),
        ),
        NodeDefinitionSpec(
            node_type=FAULT_TEST_NODE_TYPE,
            node_version="1.0",
            display_name="Fault Test",
            plugin_id="flowweaver.dev_test",
            provider_type="dev_test",
            category="development",
            ui_visibility="hidden",
            output_ports=(NodePortSpec("out"),),
        ),
    )
