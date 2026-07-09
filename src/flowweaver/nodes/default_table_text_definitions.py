from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import (
    EXTRACT_TEXT_NODE_TYPE,
    REPLACE_TEXT_NODE_TYPE,
)
from flowweaver.nodes.default_node_schemas import (
    _extract_text_schema,
    _replace_text_schema,
)
from flowweaver.nodes.default_table_slots import (
    _single_transform_input_table_slots,
    _single_transform_output_table_slots,
)
from flowweaver.nodes.registry import NodeDefinitionSpec, NodePortSpec


def default_table_replace_text_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
        NodeDefinitionSpec(
            node_type=REPLACE_TEXT_NODE_TYPE,
            node_version="1.0",
            display_name="Replace Text",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_replace_text_schema(),
        ),
    )


def default_table_extract_text_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
        NodeDefinitionSpec(
            node_type=EXTRACT_TEXT_NODE_TYPE,
            node_version="1.0",
            display_name="Extract Text",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_extract_text_schema(),
        ),
    )
