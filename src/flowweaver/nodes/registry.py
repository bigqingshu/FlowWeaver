from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


@dataclass(frozen=True)
class NodePortSpec:
    name: str
    required: bool = False

    def to_catalog_data(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "required": self.required,
        }


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

    def to_catalog_data(self, *, ui_visibility: str = "visible") -> dict[str, Any]:
        return {
            "node_type": self.node_type,
            "node_version": self.node_version,
            "display_name": self.display_name,
            "input_ports": [port.to_catalog_data() for port in self.input_ports],
            "output_ports": [port.to_catalog_data() for port in self.output_ports],
            "execution_mode": self.execution_mode,
            "default_timeout_seconds": self.default_timeout_seconds,
            "retry_safe": self.retry_safe,
            "ui_visibility": ui_visibility,
            "config_schema_version": self.config_schema_version,
            "config_schema": (
                self.config_schema.to_schema()
                if self.config_schema is not None
                else None
            ),
        }


@dataclass(frozen=True)
class NodeCatalogState:
    catalog_hash: str
    node_count: int


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


def _stable_json_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(payload.encode("utf-8")).hexdigest()
