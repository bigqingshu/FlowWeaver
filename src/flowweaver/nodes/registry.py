from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NodePortSpec:
    name: str
    required: bool = False


@dataclass(frozen=True)
class NodeConfigFieldSpec:
    type: str
    title: str | None = None
    required: bool = False
    default: Any | None = None
    minimum: int | float | None = None
    enum: tuple[str, ...] = ()
    item_type: str | None = None
    description: str | None = None

    def to_schema(self) -> dict[str, Any]:
        schema: dict[str, Any] = {"type": self.type}
        if self.title is not None:
            schema["title"] = self.title
        if self.required:
            schema["required"] = True
        if self.default is not None:
            schema["default"] = self.default
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.enum:
            schema["enum"] = list(self.enum)
        if self.item_type is not None:
            schema["items"] = {"type": self.item_type}
        if self.description is not None:
            schema["description"] = self.description
        return schema


@dataclass(frozen=True)
class NodeConfigSchemaSpec:
    properties: dict[str, NodeConfigFieldSpec]
    type: str = "object"

    def to_schema(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "properties": {
                name: field.to_schema()
                for name, field in self.properties.items()
            },
        }


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
    config_schema_version: str = "1.0"
    config_schema: NodeConfigSchemaSpec | None = None

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
