from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import (
    ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
    LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
    MERGE_COLUMNS_NODE_TYPE,
    NUMERIC_COLUMN_OPERATION_NODE_TYPE,
    PARSE_DATETIME_NODE_TYPE,
)
from flowweaver.nodes.default_node_schemas import (
    _add_current_datetime_column_schema,
    _lookup_matched_field_name_schema,
    _merge_columns_schema,
    _numeric_column_operation_schema,
    _parse_datetime_schema,
)
from flowweaver.nodes.default_table_basic_column_definitions import (
    default_table_basic_column_node_definitions,
)
from flowweaver.nodes.default_table_fill_definitions import (
    default_table_fill_node_definitions,
)
from flowweaver.nodes.default_table_row_definitions import (
    default_table_row_node_definitions,
)
from flowweaver.nodes.default_table_slots import (
    _current_output_table_slot,
    _input_table_slot,
    _single_transform_input_table_slots,
    _single_transform_output_table_slots,
)
from flowweaver.nodes.default_table_text_definitions import (
    default_table_extract_text_node_definitions,
    default_table_replace_text_node_definitions,
)
from flowweaver.nodes.registry import NodeDefinitionSpec, NodePortSpec


def default_table_transform_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
        *default_table_basic_column_node_definitions(),
        *default_table_fill_node_definitions(),
        *default_table_replace_text_node_definitions(),
        *default_table_row_node_definitions(),
        *default_table_extract_text_node_definitions(),
        NodeDefinitionSpec(
            node_type=LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
            node_version="1.0",
            display_name="Lookup Matched Field Name",
            input_ports=(
                NodePortSpec("in", required=True),
                NodePortSpec("lookup", required=True),
            ),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=(
                _input_table_slot(
                    "in",
                    display_name="Main table",
                    description="Main table to annotate with lookup results.",
                ),
                _input_table_slot(
                    "lookup",
                    display_name="Lookup table",
                    description="Reference table used for field-name lookup.",
                ),
            ),
            output_table_slots=(
                _current_output_table_slot(
                    "out",
                    display_name="Current table",
                    description="Main workflow table after lookup matching.",
                ),
            ),
            config_schema=_lookup_matched_field_name_schema(),
        ),
        NodeDefinitionSpec(
            node_type=MERGE_COLUMNS_NODE_TYPE,
            node_version="1.0",
            display_name="Merge Columns",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_merge_columns_schema(),
        ),
        NodeDefinitionSpec(
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
            node_version="1.0",
            display_name="Numeric Column Operation",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_numeric_column_operation_schema(),
        ),
        NodeDefinitionSpec(
            node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
            node_version="1.0",
            display_name="Add Current DateTime Column",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_add_current_datetime_column_schema(),
        ),
        NodeDefinitionSpec(
            node_type=PARSE_DATETIME_NODE_TYPE,
            node_version="1.0",
            display_name="Parse DateTime",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            input_table_slots=_single_transform_input_table_slots(),
            output_table_slots=_single_transform_output_table_slots(),
            config_schema=_parse_datetime_schema(),
        ),
    )
