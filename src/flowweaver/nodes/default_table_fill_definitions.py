from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import (
    FILL_CELLS_NODE_TYPE,
    FILL_RANGE_NODE_TYPE,
    FILL_SEQUENCE_NODE_TYPE,
)
from flowweaver.nodes.default_fill_cells_node_schema import (
    _fill_cells_schema,
)
from flowweaver.nodes.default_fill_range_node_schema import (
    _fill_range_schema,
)
from flowweaver.nodes.default_fill_sequence_node_schema import (
    _fill_sequence_schema,
)
from flowweaver.nodes.default_table_slots import (
    _single_transform_input_table_slots,
    _single_transform_output_table_slots,
)
from flowweaver.nodes.registry import NodeDefinitionSpec, NodePortSpec


def default_table_fill_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
        NodeDefinitionSpec(
            node_type=FILL_CELLS_NODE_TYPE,
            node_version="1.0",
            display_name="Fill Cells",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_fill_cells_schema(),
        ),
        NodeDefinitionSpec(
            node_type=FILL_RANGE_NODE_TYPE,
            node_version="1.0",
            display_name="Fill Range",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_fill_range_schema(),
        ),
        NodeDefinitionSpec(
            node_type=FILL_SEQUENCE_NODE_TYPE,
            node_version="1.0",
            display_name="Fill Sequence",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_fill_sequence_schema(),
        ),
    )
