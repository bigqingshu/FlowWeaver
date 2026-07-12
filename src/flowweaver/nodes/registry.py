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
        self._catalog_state_cache: dict[
            tuple[tuple[str, ...], tuple[str, ...] | None],
            NodeCatalogState,
        ] = {}

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
        ui_visibilities: Iterable[str] | None = None,
    ) -> NodeCatalogState:
        excluded = tuple(sorted(set(excluded_node_types)))
        visible = (
            tuple(sorted(set(ui_visibilities))) if ui_visibilities is not None else None
        )
        cache_key = (excluded, visible)
        cached = self._catalog_state_cache.get(cache_key)
        if cached is not None:
            return cached

        excluded_set = set(excluded)
        visible_set = set(visible) if visible is not None else None
        catalog_data = [
            definition.to_catalog_data()
            for definition in self.list_definitions()
            if definition.node_type not in excluded_set
            and (visible_set is None or definition.ui_visibility in visible_set)
        ]
        state = NodeCatalogState(
            catalog_hash=_stable_json_hash(catalog_data),
            node_count=len(catalog_data),
        )
        self._catalog_state_cache[cache_key] = state
        return state
