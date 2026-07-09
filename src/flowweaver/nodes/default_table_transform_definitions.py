from __future__ import annotations

from flowweaver.nodes.default_table_basic_column_definitions import (
    default_table_basic_column_node_definitions,
)
from flowweaver.nodes.default_table_fill_definitions import (
    default_table_fill_node_definitions,
)
from flowweaver.nodes.default_table_lookup_merge_definitions import (
    default_table_lookup_merge_node_definitions,
)
from flowweaver.nodes.default_table_numeric_datetime_definitions import (
    default_table_numeric_datetime_node_definitions,
)
from flowweaver.nodes.default_table_row_definitions import (
    default_table_row_node_definitions,
)
from flowweaver.nodes.default_table_text_definitions import (
    default_table_extract_text_node_definitions,
    default_table_replace_text_node_definitions,
)
from flowweaver.nodes.registry import NodeDefinitionSpec


def default_table_transform_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
        *default_table_basic_column_node_definitions(),
        *default_table_fill_node_definitions(),
        *default_table_replace_text_node_definitions(),
        *default_table_row_node_definitions(),
        *default_table_extract_text_node_definitions(),
        *default_table_lookup_merge_node_definitions(),
        *default_table_numeric_datetime_node_definitions(),
    )
