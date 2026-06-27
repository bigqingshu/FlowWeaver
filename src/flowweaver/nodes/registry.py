from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NodePortSpec:
    name: str
    required: bool = False


@dataclass(frozen=True)
class NodeDefinitionSpec:
    node_type: str
    node_version: str
    display_name: str
    input_ports: tuple[NodePortSpec, ...] = ()
    output_ports: tuple[NodePortSpec, ...] = ()
    execution_mode: str = "PROCESS_POOL"
    default_timeout_seconds: int = 60
    retry_safe: bool = False
    implementation_path: str | None = None

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.node_type, self.node_version)


class NodeRegistry:
    def __init__(self) -> None:
        self._definitions: dict[tuple[str, str], NodeDefinitionSpec] = {}

    def register(self, definition: NodeDefinitionSpec) -> None:
        if definition.registry_key in self._definitions:
            node_type, node_version = definition.registry_key
            raise ValueError(f"Duplicate node registration: {node_type}@{node_version}")
        self._definitions[definition.registry_key] = definition

    def get(self, node_type: str, node_version: str) -> NodeDefinitionSpec | None:
        return self._definitions.get((node_type, node_version))

    def list_definitions(self) -> list[NodeDefinitionSpec]:
        return sorted(
            self._definitions.values(),
            key=lambda definition: definition.registry_key,
        )
