from __future__ import annotations

from typing import Protocol

from flowweaver.nodes.default_control_definitions import (
    default_control_node_definitions,
)
from flowweaver.nodes.default_resource_definitions import (
    default_resource_node_definitions,
)
from flowweaver.nodes.default_table_transform_definitions import (
    default_table_transform_node_definitions,
)
from flowweaver.nodes.default_write_definitions import default_write_node_definitions
from flowweaver.nodes.registry import NodeDefinitionSpec, NodeRegistry


class NodeDefinitionCatalog(Protocol):
    def node_definitions(self) -> tuple[NodeDefinitionSpec, ...]:
        ...


def create_default_node_registry(
    plugin_catalog: NodeDefinitionCatalog | None = None,
) -> NodeRegistry:
    registry = NodeRegistry()
    for definition in default_node_definitions():
        registry.register(definition)
    if plugin_catalog is not None:
        for definition in plugin_catalog.node_definitions():
            registry.register(definition)
    return registry


def default_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
        *default_table_transform_node_definitions(),
        *default_control_node_definitions(),
        *default_write_node_definitions(),
        *default_resource_node_definitions(),
    )
