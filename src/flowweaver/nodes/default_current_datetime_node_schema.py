from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _add_current_datetime_column_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
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
                default="current_datetime",
            ),
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
            ),
            "time_mode": NodeConfigFieldSpec(
                type="enum",
                title="Time Mode",
                default="fixed",
                enum=("fixed", "per_row"),
            ),
            "format_mode": NodeConfigFieldSpec(
                type="enum",
                title="Format Mode",
                default="iso",
                enum=("iso", "strftime", "template"),
            ),
            "template": NodeConfigFieldSpec(
                type="string",
                title="Template",
                default="{datetime}",
            ),
            "strftime_template": NodeConfigFieldSpec(
                type="string",
                title="Strftime Template",
                default="%Y-%m-%d %H:%M:%S",
            ),
        }
    )
