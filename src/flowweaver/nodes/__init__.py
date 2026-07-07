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
from flowweaver.nodes.registry import NodeDefinitionSpec, NodeRegistry
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeHandler,
    BuiltinTableNodeHandlerRegistry,
    BuiltinTableNodeValidationError,
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
    "PUBLISH_SHARED_TABLES_NODE_TYPE",
    "READ_SHARED_TABLES_NODE_TYPE",
]
