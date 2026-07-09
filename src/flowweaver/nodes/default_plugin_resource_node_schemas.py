from __future__ import annotations

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
