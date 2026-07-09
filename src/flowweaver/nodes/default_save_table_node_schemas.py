from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


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


def _save_run_table_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "transit_name": NodeConfigFieldSpec(
                type="string",
                title="Transit Name",
                default="run_table",
                description="Workflow-run local name for this intermediate table.",
            ),
            "save_memory": NodeConfigFieldSpec(
                type="boolean",
                title="Save Memory",
                default=True,
                description=(
                    "When false, runtime only passes the current input table through."
                ),
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
