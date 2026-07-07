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
from flowweaver.nodes.builtin_table import (
    ADD_COLUMNS_NODE_TYPE,
    COPY_COLUMN_NODE_TYPE,
    DELETE_COLUMNS_NODE_TYPE,
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
    SAVE_MEMORY_TABLE_NODE_TYPE,
)
from flowweaver.nodes.registry import (
    NodeConfigFieldSpec,
    NodeConfigSchemaSpec,
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
        NodeDefinitionSpec(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_version="1.0",
            display_name="Generate Test Table",
            output_ports=(NodePortSpec("out"),),
            config_schema=_generate_test_table_schema(),
        ),
        NodeDefinitionSpec(
            node_type=FILTER_ROWS_NODE_TYPE,
            node_version="1.0",
            display_name="Filter Rows",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_filter_rows_schema(),
        ),
        NodeDefinitionSpec(
            node_type=ADD_COLUMNS_NODE_TYPE,
            node_version="1.0",
            display_name="Add Column",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_add_columns_schema(),
        ),
        NodeDefinitionSpec(
            node_type=DELETE_COLUMNS_NODE_TYPE,
            node_version="1.0",
            display_name="Delete Columns",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_delete_columns_schema(),
        ),
        NodeDefinitionSpec(
            node_type=COPY_COLUMN_NODE_TYPE,
            node_version="1.0",
            display_name="Copy Column",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_copy_column_schema(),
        ),
        NodeDefinitionSpec(
            node_type=SAVE_MEMORY_TABLE_NODE_TYPE,
            node_version="1.0",
            display_name="Save Memory Table",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"), NodePortSpec("memory")),
            config_schema=_save_memory_table_schema(),
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


def _add_columns_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "column_name": NodeConfigFieldSpec(
                type="string",
                title="Column Name",
                required=True,
                default="new_column",
            ),
            "default_value": NodeConfigFieldSpec(
                type="string",
                title="Default Value",
                default="",
                description=(
                    "Runtime parses this value according to data_type for "
                    "INTEGER, FLOAT, and BOOLEAN columns."
                ),
            ),
            "data_type": NodeConfigFieldSpec(
                type="enum",
                title="Data Type",
                required=True,
                default="TEXT",
                enum=("TEXT", "INTEGER", "FLOAT", "BOOLEAN"),
            ),
        }
    )


def _delete_columns_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "columns": NodeConfigFieldSpec(
                type="array",
                title="Columns",
                required=True,
                item_type="string",
                description="Column names to remove from the output table.",
            ),
        }
    )


def _copy_column_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "source_field": NodeConfigFieldSpec(
                type="string",
                title="Source Field",
                required=True,
            ),
            "output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Output Mode",
                required=True,
                default="new_field",
                enum=("new_field", "overwrite"),
            ),
            "new_field": NodeConfigFieldSpec(
                type="string",
                title="New Field",
                default="copied_column",
            ),
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
                description="Required when output_mode is overwrite.",
            ),
            "trim_value": NodeConfigFieldSpec(
                type="boolean",
                title="Trim Value",
                default=False,
            ),
            "empty_default": NodeConfigFieldSpec(
                type="object",
                title="Empty Default",
                description="Value used when the source value is null or empty.",
            ),
        }
    )


def _save_memory_table_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "table_name": NodeConfigFieldSpec(
                type="string",
                title="Table Name",
                required=True,
                default="memory_table",
            ),
            "mode": NodeConfigFieldSpec(
                type="enum",
                title="Mode",
                required=True,
                default="overwrite",
                enum=("overwrite",),
            ),
        }
    )


def _sql_mapping_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "database_path": NodeConfigFieldSpec(
                type="string",
                title="Database Path",
                required=True,
            ),
            "table_name": NodeConfigFieldSpec(
                type="string",
                title="Table Name",
                description="Use table_name or query, not both.",
            ),
            "query": NodeConfigFieldSpec(
                type="string",
                title="Query",
                description=(
                    "Read-only SELECT query. Use query or table_name, not both."
                ),
            ),
            "logical_table_id": NodeConfigFieldSpec(
                type="string",
                title="Logical Table",
                description="Optional workflow-facing table name.",
            ),
            "schema": NodeConfigFieldSpec(
                type="array",
                title="Schema",
                item_type="object",
                description=(
                    "Optional list of field objects. When omitted, runtime infers "
                    "table schema where possible."
                ),
            ),
        }
    )


def _publish_shared_tables_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "share_name": NodeConfigFieldSpec(
                type="string",
                title="Share Name",
                required=True,
            ),
            "export_names": NodeConfigFieldSpec(
                type="array",
                title="Export Names",
                required=True,
                item_type="string",
            ),
            "retention_seconds": NodeConfigFieldSpec(
                type="integer",
                title="Retention Seconds",
                minimum=1,
            ),
        }
    )


def _read_shared_tables_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "share_name": NodeConfigFieldSpec(
                type="string",
                title="Share Name",
                required=True,
            ),
            "version_policy": NodeConfigFieldSpec(
                type="enum",
                title="Version Policy",
                required=True,
                enum=("LATEST", "EXACT_VERSION"),
            ),
            "exact_version": NodeConfigFieldSpec(
                type="integer",
                title="Exact Version",
                minimum=1,
            ),
            "selected_members": NodeConfigFieldSpec(
                type="array",
                title="Selected Members",
                item_type="string",
            ),
        }
    )
