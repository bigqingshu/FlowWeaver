from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import (
    CONDITION_FLAG_NODE_TYPE,
    CONDITIONAL_JUMP_NODE_TYPE,
    JUMP_ANCHOR_NODE_TYPE,
    LOOP_JUDGE_NODE_TYPE,
    LOOP_START_NODE_TYPE,
    SUB_WORKFLOW_NODE_TYPE,
    UNCONDITIONAL_JUMP_NODE_TYPE,
)
from flowweaver.nodes.default_node_schemas import (
    _condition_flag_schema,
    _conditional_jump_schema,
    _jump_anchor_schema,
    _loop_judge_schema,
    _loop_start_schema,
    _subworkflow_schema,
    _unconditional_jump_schema,
)
from flowweaver.nodes.registry import NodeDefinitionSpec, NodePortSpec


def default_control_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
        NodeDefinitionSpec(
            node_type=CONDITION_FLAG_NODE_TYPE,
            node_version="1.0",
            display_name="Condition Flag",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_condition_flag_schema(),
        ),
        NodeDefinitionSpec(
            node_type=JUMP_ANCHOR_NODE_TYPE,
            node_version="1.0",
            display_name="Jump Anchor",
            output_ports=(NodePortSpec("status"),),
            config_schema=_jump_anchor_schema(),
        ),
        NodeDefinitionSpec(
            node_type=UNCONDITIONAL_JUMP_NODE_TYPE,
            node_version="1.0",
            display_name="Unconditional Jump",
            input_ports=(NodePortSpec("in"),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_unconditional_jump_schema(),
        ),
        NodeDefinitionSpec(
            node_type=CONDITIONAL_JUMP_NODE_TYPE,
            node_version="1.0",
            display_name="Conditional Jump",
            input_ports=(NodePortSpec("condition", required=True),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_conditional_jump_schema(),
        ),
        NodeDefinitionSpec(
            node_type=LOOP_START_NODE_TYPE,
            node_version="1.0",
            display_name="Loop Start",
            input_ports=(NodePortSpec("in"),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_loop_start_schema(),
        ),
        NodeDefinitionSpec(
            node_type=LOOP_JUDGE_NODE_TYPE,
            node_version="1.0",
            display_name="Loop Judge",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_loop_judge_schema(),
        ),
        NodeDefinitionSpec(
            node_type=SUB_WORKFLOW_NODE_TYPE,
            node_version="1.0",
            display_name="Sub Workflow",
            input_ports=(NodePortSpec("in"),),
            output_ports=(NodePortSpec("status"),),
            config_schema=_subworkflow_schema(),
        ),
    )
