from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
                name: field.to_schema() for name, field in self.properties.items()
            },
        }
