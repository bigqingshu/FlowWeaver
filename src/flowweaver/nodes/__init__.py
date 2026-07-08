"""Node registry metadata and first-stage builtin node implementations."""

from flowweaver.nodes.builtin_shared_table import (
    PUBLISH_SHARED_TABLES_NODE_TYPE,
    READ_SHARED_TABLES_NODE_TYPE,
    BuiltinSharedTableNodeRunner,
)
from flowweaver.nodes.builtin_sql import SQL_MAPPING_NODE_TYPE, SqlMappingNodeRunner
from flowweaver.nodes.builtin_table import BuiltinTableNodeRunner
from flowweaver.nodes.default_registry import (
    create_default_node_registry,
    default_node_definitions,
)
from flowweaver.nodes.registry import (
    NodeDefinitionSpec,
    NodeRegistry,
    NodeTableInputSlotSpec,
    NodeTableOutputSlotSpec,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeHandler,
    BuiltinTableNodeHandlerRegistry,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.value_sources import (
    VALUE_SOURCE_LITERAL,
    VALUE_SOURCE_ROW_FIELD,
    ValueSource,
    ValueSourceError,
    parse_value_source,
    resolve_value_source,
)

__all__ = [
    "BuiltinSharedTableNodeRunner",
    "BuiltinTableNodeContext",
    "BuiltinTableNodeHandler",
    "BuiltinTableNodeHandlerRegistry",
    "BuiltinTableNodeValidationError",
    "BuiltinTableNodeRunner",
    "SQL_MAPPING_NODE_TYPE",
    "SqlMappingNodeRunner",
    "create_default_node_registry",
    "default_node_definitions",
    "NodeDefinitionSpec",
    "NodeRegistry",
    "NodeTableInputSlotSpec",
    "NodeTableOutputSlotSpec",
    "parse_value_source",
    "PUBLISH_SHARED_TABLES_NODE_TYPE",
    "READ_SHARED_TABLES_NODE_TYPE",
    "resolve_value_source",
    "VALUE_SOURCE_LITERAL",
    "VALUE_SOURCE_ROW_FIELD",
    "ValueSource",
    "ValueSourceError",
]
