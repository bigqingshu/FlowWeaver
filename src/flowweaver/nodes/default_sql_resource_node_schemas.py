from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _sql_mapping_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "source_mode": NodeConfigFieldSpec(
                type="enum",
                title="Source Mode",
                required=True,
                default="table",
                enum=("table", "all_tables", "query"),
            ),
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
                    "table schema where possible. Not available in all_tables mode."
                ),
            ),
        }
    )
