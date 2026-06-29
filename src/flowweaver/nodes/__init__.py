"""Node registry metadata and first-stage builtin node implementations."""

from flowweaver.nodes.builtin_shared_table import (
    PUBLISH_SHARED_TABLES_NODE_TYPE,
    READ_SHARED_TABLES_NODE_TYPE,
    BuiltinSharedTableNodeRunner,
)
from flowweaver.nodes.builtin_table import BuiltinTableNodeRunner
from flowweaver.nodes.default_registry import (
    create_default_node_registry,
    default_node_definitions,
)
from flowweaver.nodes.permissions import (
    resolve_builtin_node_permissions,
    supports_builtin_node_permissions,
)
from flowweaver.nodes.registry import NodeDefinitionSpec, NodeRegistry

__all__ = [
    "BuiltinSharedTableNodeRunner",
    "BuiltinTableNodeRunner",
    "create_default_node_registry",
    "default_node_definitions",
    "NodeDefinitionSpec",
    "NodeRegistry",
    "PUBLISH_SHARED_TABLES_NODE_TYPE",
    "READ_SHARED_TABLES_NODE_TYPE",
    "resolve_builtin_node_permissions",
    "supports_builtin_node_permissions",
]
