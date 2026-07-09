from __future__ import annotations

from flowweaver.nodes.default_file_resource_node_schemas import (
    _batch_rename_files_schema as _batch_rename_files_schema,
)
from flowweaver.nodes.default_file_resource_node_schemas import (
    _list_files_schema as _list_files_schema,
)
from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _plugin_node_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "plugin_id": NodeConfigFieldSpec(
                type="string",
                title="Plugin ID",
                required=True,
            ),
            "plugin_version": NodeConfigFieldSpec(
                type="string",
                title="Plugin Version",
            ),
            "params": NodeConfigFieldSpec(
                type="object",
                title="Params",
                description="Plugin parameter object.",
            ),
            "input_bindings": NodeConfigFieldSpec(
                type="object",
                title="Input Bindings",
                description="Plugin input binding object.",
            ),
            "output_bindings": NodeConfigFieldSpec(
                type="object",
                title="Output Bindings",
                description="Plugin output binding object.",
            ),
            "plugin_manifest": NodeConfigFieldSpec(
                type="object",
                title="Plugin Manifest",
                description="Plugin manifest object used for preflight validation.",
            ),
            "execution_mode": NodeConfigFieldSpec(
                type="enum",
                title="Execution Mode",
                default="external_process",
                enum=("in_process", "external_process"),
            ),
            "allow_external_actions": NodeConfigFieldSpec(
                type="boolean",
                title="Allow External Actions",
                default=False,
            ),
            "enable_execute": NodeConfigFieldSpec(
                type="boolean",
                title="Enable Execute",
                default=False,
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
