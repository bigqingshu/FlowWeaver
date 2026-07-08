from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _condition_flag_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "flag_name": NodeConfigFieldSpec(
                type="string",
                title="Flag Name",
                required=True,
                default="condition",
            ),
            "condition_type": NodeConfigFieldSpec(
                type="enum",
                title="Condition Type",
                required=True,
                default="row_count",
                enum=("row_count", "field_exists", "field_value"),
            ),
            "field": NodeConfigFieldSpec(
                type="string",
                title="Field",
            ),
            "operator": NodeConfigFieldSpec(
                type="enum",
                title="Operator",
                default="GE",
                enum=(
                    "EQ",
                    "NE",
                    "GT",
                    "GE",
                    "LT",
                    "LE",
                    "CONTAINS",
                    "IS_NULL",
                    "IS_EMPTY",
                ),
            ),
            "value": NodeConfigFieldSpec(
                type="object",
                title="Value",
                default=1,
            ),
            "value_source": NodeConfigFieldSpec(
                type="object",
                title="Value Source",
                description=(
                    "Literal values or same-row field objects are supported by "
                    "runtime."
                ),
            ),
            "value_field": NodeConfigFieldSpec(
                type="string",
                title="Value Field",
                description="Shortcut for same-row field comparison.",
            ),
            "aggregation": NodeConfigFieldSpec(
                type="enum",
                title="Aggregation",
                default="any",
                enum=("any", "all", "first", "count"),
            ),
            "case_sensitive": NodeConfigFieldSpec(
                type="boolean",
                title="Case Sensitive",
                default=True,
            ),
            "true_value": NodeConfigFieldSpec(
                type="object",
                title="True Value",
                default=True,
            ),
            "false_value": NodeConfigFieldSpec(
                type="object",
                title="False Value",
                default=False,
            ),
        }
    )


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


def _loop_start_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "loop_id": NodeConfigFieldSpec(
                type="string",
                title="Loop ID",
                required=True,
                default="loop",
            ),
            "source_type": NodeConfigFieldSpec(
                type="enum",
                title="Source Type",
                default="current_table",
                enum=("current_table", "named_table", "sqlite"),
            ),
            "fields": NodeConfigFieldSpec(
                type="array",
                title="Fields",
                item_type="string",
            ),
            "max_loop_count": NodeConfigFieldSpec(
                type="integer",
                title="Max Loop Count",
                default=1,
                minimum=1,
            ),
            "output_current_as_table": NodeConfigFieldSpec(
                type="boolean",
                title="Output Current As Table",
                default=True,
            ),
            "current_table_name": NodeConfigFieldSpec(
                type="string",
                title="Current Table Name",
                default="current_loop_item",
            ),
        }
    )


def _loop_judge_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "loop_id": NodeConfigFieldSpec(
                type="string",
                title="Loop ID",
                required=True,
                default="loop",
            ),
            "condition_mode": NodeConfigFieldSpec(
                type="enum",
                title="Condition Mode",
                default="always_success",
                enum=("always_success", "row_count", "field_value"),
            ),
            "condition_field": NodeConfigFieldSpec(
                type="string",
                title="Condition Field",
            ),
            "condition_op": NodeConfigFieldSpec(
                type="enum",
                title="Condition Operator",
                default="EQ",
                enum=(
                    "EQ",
                    "NE",
                    "GT",
                    "GE",
                    "LT",
                    "LE",
                    "CONTAINS",
                    "IS_NULL",
                    "IS_EMPTY",
                ),
            ),
            "condition_value": NodeConfigFieldSpec(
                type="object",
                title="Condition Value",
            ),
            "condition_value_source": NodeConfigFieldSpec(
                type="object",
                title="Condition Value Source",
            ),
            "condition_value_field": NodeConfigFieldSpec(
                type="string",
                title="Condition Value Field",
            ),
            "on_success": NodeConfigFieldSpec(
                type="enum",
                title="On Success",
                default="continue_loop",
                enum=("continue_loop", "end_loop"),
            ),
            "on_fail": NodeConfigFieldSpec(
                type="enum",
                title="On Fail",
                default="end_loop",
                enum=("continue_loop", "end_loop"),
            ),
            "result_table_name": NodeConfigFieldSpec(
                type="string",
                title="Result Table Name",
                default="loop_result",
            ),
        }
    )


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
