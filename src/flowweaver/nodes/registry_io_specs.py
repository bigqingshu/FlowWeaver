from __future__ import annotations

from dataclasses import dataclass
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
