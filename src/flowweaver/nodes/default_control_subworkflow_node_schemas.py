from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _subworkflow_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "group_name": NodeConfigFieldSpec(
                type="string",
                title="Group Name",
                required=True,
                default="subworkflow",
            ),
            "subworkflow_ref": NodeConfigFieldSpec(
                type="string",
                title="Subworkflow Ref",
                description=(
                    "Optional workflow/template identifier recorded by the "
                    "preview plan."
                ),
            ),
            "nodes": NodeConfigFieldSpec(
                type="array",
                title="Nodes",
                item_type="object",
                description="Embedded child-node definitions for preview metadata.",
            ),
            "input_source_type": NodeConfigFieldSpec(
                type="enum",
                title="Input Source Type",
                default="current_table",
                enum=("current_table", "named_inputs", "none"),
            ),
            "input_mapping": NodeConfigFieldSpec(
                type="array",
                title="Input Mapping",
                item_type="object",
                description="Objects describing parent input to child input mapping.",
            ),
            "input_defaults": NodeConfigFieldSpec(
                type="object",
                title="Input Defaults",
            ),
            "missing_input_policy": NodeConfigFieldSpec(
                type="enum",
                title="Missing Input Policy",
                default="error",
                enum=("error", "skip", "use_default"),
            ),
            "transit_scope": NodeConfigFieldSpec(
                type="enum",
                title="Transit Scope",
                default="isolated",
                enum=("isolated", "inherited"),
            ),
            "allow_loop_nodes": NodeConfigFieldSpec(
                type="boolean",
                title="Allow Loop Nodes",
                default=False,
            ),
            "main_output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Main Output Mode",
                default="status_only",
                enum=("status_only", "passthrough", "named_outputs"),
            ),
            "save_to_transit": NodeConfigFieldSpec(
                type="boolean",
                title="Save To Transit",
                default=False,
            ),
            "output_transit_name": NodeConfigFieldSpec(
                type="string",
                title="Output Transit Name",
                description="Required when save_to_transit is true.",
            ),
        }
    )
