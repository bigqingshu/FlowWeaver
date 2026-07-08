from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from flowweaver.protocols.enums import TableRole, TableStorageKind


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
class NodeTableInputSlotSpec:
    name: str
    display_name: str | None = None
    description: str | None = None
    required: bool = False
    allowed_storage_kinds: tuple[TableStorageKind, ...] = (
        TableStorageKind.RUNTIME_SQL,
        TableStorageKind.MEMORY,
        TableStorageKind.EXTERNAL_SQL,
    )
    default_source: str | None = "upstream_current"

    def to_catalog_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "required": self.required,
            "allowed_storage_kinds": [
                storage_kind.value for storage_kind in self.allowed_storage_kinds
            ],
        }
        if self.display_name is not None:
            data["display_name"] = self.display_name
        if self.description is not None:
            data["description"] = self.description
        if self.default_source is not None:
            data["default_source"] = self.default_source
        return data


@dataclass(frozen=True)
class NodeTableOutputSlotSpec:
    name: str
    display_name: str | None = None
    description: str | None = None
    default_role: TableRole = TableRole.CURRENT
    allow_current: bool = True
    allow_new_memory: bool = False
    allow_new_runtime_sql: bool = False
    allow_existing_memory: bool = False
    allow_existing_runtime_sql: bool = False

    def to_catalog_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "default_role": self.default_role.value,
            "allow_current": self.allow_current,
            "allow_new_memory": self.allow_new_memory,
            "allow_new_runtime_sql": self.allow_new_runtime_sql,
            "allow_existing_memory": self.allow_existing_memory,
            "allow_existing_runtime_sql": self.allow_existing_runtime_sql,
        }
        if self.display_name is not None:
            data["display_name"] = self.display_name
        if self.description is not None:
            data["description"] = self.description
        return data


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
    input_table_slots: tuple[NodeTableInputSlotSpec, ...] = ()
    output_table_slots: tuple[NodeTableOutputSlotSpec, ...] = ()
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
            "input_table_slots": [
                slot.to_catalog_data() for slot in self.input_table_slots
            ],
            "output_table_slots": [
                slot.to_catalog_data() for slot in self.output_table_slots
            ],
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
