from __future__ import annotations

from collections.abc import Iterable

from flowweaver.nodes.registry_specs import (
    NodeCatalogState as NodeCatalogState,
)
from flowweaver.nodes.registry_specs import (
    NodeConfigFieldSpec as NodeConfigFieldSpec,
)
from flowweaver.nodes.registry_specs import (
    NodeConfigSchemaSpec as NodeConfigSchemaSpec,
)
from flowweaver.nodes.registry_specs import (
    NodeDefinitionSpec as NodeDefinitionSpec,
)
from flowweaver.nodes.registry_specs import (
    NodePortSpec as NodePortSpec,
)
from flowweaver.nodes.registry_specs import (
    NodeTableInputSlotSpec as NodeTableInputSlotSpec,
)
from flowweaver.nodes.registry_specs import (
    NodeTableOutputSlotSpec as NodeTableOutputSlotSpec,
)
from flowweaver.nodes.registry_specs import stable_json_hash as _stable_json_hash


class NodeRegistry:
    def __init__(self) -> None:
        self._definitions: dict[tuple[str, str], NodeDefinitionSpec] = {}
        self._catalog_state_cache: dict[tuple[str, ...], NodeCatalogState] = {}

    def register(self, definition: NodeDefinitionSpec) -> None:
        if definition.registry_key in self._definitions:
            node_type, node_version = definition.registry_key
            raise ValueError(f"Duplicate node registration: {node_type}@{node_version}")
        self._definitions[definition.registry_key] = definition
        self._catalog_state_cache.clear()

    def get(self, node_type: str, node_version: str) -> NodeDefinitionSpec | None:
        return self._definitions.get((node_type, node_version))

    def list_definitions(self) -> list[NodeDefinitionSpec]:
        return sorted(
            self._definitions.values(),
            key=lambda definition: definition.registry_key,
        )

    def catalog_state(
        self,
        *,
        excluded_node_types: Iterable[str] = (),
    ) -> NodeCatalogState:
        excluded = tuple(sorted(set(excluded_node_types)))
        cached = self._catalog_state_cache.get(excluded)
        if cached is not None:
            return cached

        excluded_set = set(excluded)
        catalog_data = [
            definition.to_catalog_data()
            for definition in self.list_definitions()
            if definition.node_type not in excluded_set
        ]
        state = NodeCatalogState(
            catalog_hash=_stable_json_hash(catalog_data),
            node_count=len(catalog_data),
        )
        self._catalog_state_cache[excluded] = state
        return state
