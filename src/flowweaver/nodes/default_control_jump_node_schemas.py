from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _jump_anchor_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "anchor_name": NodeConfigFieldSpec(
                type="string",
                title="Anchor Name",
                required=True,
                default="anchor",
            ),
            "description": NodeConfigFieldSpec(
                type="string",
                title="Description",
                default="",
            ),
            "allow_multiple_hits": NodeConfigFieldSpec(
                type="boolean",
                title="Allow Multiple Hits",
                default=False,
                description=(
                    "Recorded for future real scheduling; preview execution only "
                    "publishes a control status table."
                ),
            ),
        }
    )


def _unconditional_jump_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "target_mode": NodeConfigFieldSpec(
                type="enum",
                title="Target Mode",
                required=True,
                default="anchor",
                enum=("anchor", "node"),
            ),
            "target_anchor": NodeConfigFieldSpec(
                type="string",
                title="Target Anchor",
                description="Required when target_mode is anchor.",
            ),
            "target_node_id": NodeConfigFieldSpec(
                type="string",
                title="Target Node ID",
                description="Required when target_mode is node.",
            ),
            "reason": NodeConfigFieldSpec(
                type="string",
                title="Reason",
                default="",
            ),
        }
    )


def _conditional_jump_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "condition_field": NodeConfigFieldSpec(
                type="string",
                title="Condition Field",
                required=True,
                default="result",
            ),
            "true_target_mode": NodeConfigFieldSpec(
                type="enum",
                title="True Target Mode",
                default="anchor",
                enum=("anchor", "node"),
            ),
            "true_target_anchor": NodeConfigFieldSpec(
                type="string",
                title="True Target Anchor",
                description="Required when the true branch targets an anchor.",
            ),
            "true_target_node_id": NodeConfigFieldSpec(
                type="string",
                title="True Target Node ID",
                description="Required when the true branch targets a node.",
            ),
            "false_target_mode": NodeConfigFieldSpec(
                type="enum",
                title="False Target Mode",
                default="anchor",
                enum=("anchor", "node"),
            ),
            "false_target_anchor": NodeConfigFieldSpec(
                type="string",
                title="False Target Anchor",
                description="Required when the false branch targets an anchor.",
            ),
            "false_target_node_id": NodeConfigFieldSpec(
                type="string",
                title="False Target Node ID",
                description="Required when the false branch targets a node.",
            ),
            "default_branch": NodeConfigFieldSpec(
                type="enum",
                title="Default Branch",
                default="false",
                enum=("true", "false"),
                description=(
                    "Branch used when the condition value is missing or cannot "
                    "be parsed as true/false."
                ),
            ),
        }
    )
