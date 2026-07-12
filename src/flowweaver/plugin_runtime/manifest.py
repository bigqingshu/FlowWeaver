from __future__ import annotations

import re
from typing import Any, Literal, Self

from pydantic import Field, field_validator, model_validator

from flowweaver.nodes.registry import (
    NodeConfigFieldSpec,
    NodeConfigSchemaSpec,
    NodeDefinitionSpec,
    NodePortSpec,
    NodeTableInputSlotSpec,
    NodeTableOutputSlotSpec,
)
from flowweaver.protocols.base import StrictModel
from flowweaver.protocols.enums import TableRole, TableStorageKind

PLUGIN_JSONL_PROTOCOL_V1 = "flowweaver.plugin-jsonl.v1"
PLUGIN_EXTERNAL_IMPLEMENTATION_REF = "flowweaver.plugin.external_process"
PLUGIN_NODE_EXECUTION_MODE = "PLUGIN_EXTERNAL_PROCESS"

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CONFIG_FIELD_TYPES = {
    "array",
    "boolean",
    "enum",
    "integer",
    "number",
    "object",
    "string",
}
_RESERVED_PLUGIN_CONFIG_FIELDS = {
    "allow_external_actions",
    "enable_execute",
}


class PluginConfigFieldModel(StrictModel):
    type: str
    title: str | None = None
    required: bool = Field(default=False, strict=True)
    default: Any | None = None
    minimum: int | float | None = None
    enum: list[str] = Field(default_factory=list)
    item_type: str | None = None
    description: str | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in _CONFIG_FIELD_TYPES:
            raise ValueError(f"unsupported config field type: {value}")
        return value

    @field_validator("enum")
    @classmethod
    def validate_enum(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("config enum values must be non-empty strings")
        if len(value) != len(set(value)):
            raise ValueError("config enum values must be unique")
        return value

    @field_validator("item_type")
    @classmethod
    def validate_item_type(cls, value: str | None) -> str | None:
        if value is not None and value not in _CONFIG_FIELD_TYPES - {"enum"}:
            raise ValueError(f"unsupported config item type: {value}")
        return value

    def to_spec(self) -> NodeConfigFieldSpec:
        return NodeConfigFieldSpec(
            type=self.type,
            title=self.title,
            required=self.required,
            default=self.default,
            minimum=self.minimum,
            enum=tuple(self.enum),
            item_type=self.item_type,
            description=self.description,
        )


class PluginConfigSchemaModel(StrictModel):
    type: Literal["object"] = "object"
    properties: dict[str, PluginConfigFieldModel] = Field(default_factory=dict)

    @field_validator("properties")
    @classmethod
    def validate_property_names(
        cls,
        value: dict[str, PluginConfigFieldModel],
    ) -> dict[str, PluginConfigFieldModel]:
        for name in value:
            _validate_identifier(name, field_name="config property")
            if name in _RESERVED_PLUGIN_CONFIG_FIELDS:
                raise ValueError(f"reserved plugin config property: {name}")
        return value

    def to_spec(self) -> NodeConfigSchemaSpec:
        return NodeConfigSchemaSpec(
            properties={
                name: field.to_spec() for name, field in self.properties.items()
            }
        )


class PluginPortModel(StrictModel):
    name: str
    required: bool = Field(default=False, strict=True)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_identifier(value, field_name="port name")

    def to_spec(self) -> NodePortSpec:
        return NodePortSpec(name=self.name, required=self.required)


class PluginInputTableSlotModel(StrictModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    required: bool = Field(default=False, strict=True)
    allowed_storage_kinds: list[TableStorageKind] = Field(
        default_factory=lambda: [
            TableStorageKind.RUNTIME_SQL,
            TableStorageKind.MEMORY,
            TableStorageKind.EXTERNAL_SQL,
        ]
    )
    default_source: str | None = "upstream_current"

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_identifier(value, field_name="input table slot name")

    @field_validator("allowed_storage_kinds")
    @classmethod
    def validate_storage_kinds(
        cls,
        value: list[TableStorageKind],
    ) -> list[TableStorageKind]:
        if not value:
            raise ValueError("input table slot requires an allowed storage kind")
        if len(value) != len(set(value)):
            raise ValueError("input table slot storage kinds must be unique")
        return value

    def to_spec(self) -> NodeTableInputSlotSpec:
        return NodeTableInputSlotSpec(
            name=self.name,
            display_name=self.display_name,
            description=self.description,
            required=self.required,
            allowed_storage_kinds=tuple(self.allowed_storage_kinds),
            default_source=self.default_source,
        )


class PluginOutputTableSlotModel(StrictModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    default_role: TableRole = TableRole.CURRENT
    allow_current: bool = Field(default=True, strict=True)
    allow_new_memory: bool = Field(default=False, strict=True)
    allow_new_runtime_sql: bool = Field(default=False, strict=True)
    allow_existing_memory: bool = Field(default=False, strict=True)
    allow_existing_runtime_sql: bool = Field(default=False, strict=True)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_identifier(value, field_name="output table slot name")

    def to_spec(self) -> NodeTableOutputSlotSpec:
        return NodeTableOutputSlotSpec(
            name=self.name,
            display_name=self.display_name,
            description=self.description,
            default_role=self.default_role,
            allow_current=self.allow_current,
            allow_new_memory=self.allow_new_memory,
            allow_new_runtime_sql=self.allow_new_runtime_sql,
            allow_existing_memory=self.allow_existing_memory,
            allow_existing_runtime_sql=self.allow_existing_runtime_sql,
        )


class PluginManifestModel(StrictModel):
    manifest_version: Literal["1"]
    plugin_id: str
    plugin_version: str
    node_type: str
    node_version: str
    display_name: str
    category: str
    config_schema: PluginConfigSchemaModel = Field(
        default_factory=PluginConfigSchemaModel
    )
    input_ports: list[PluginPortModel] = Field(default_factory=list)
    output_ports: list[PluginPortModel] = Field(default_factory=list)
    input_table_slots: list[PluginInputTableSlotModel] = Field(default_factory=list)
    output_table_slots: list[PluginOutputTableSlotModel] = Field(default_factory=list)
    execution_mode: Literal["external_process"]
    protocol: Literal["flowweaver.plugin-jsonl.v1"]
    entrypoint: str
    external_actions: bool = Field(default=False, strict=True)

    @field_validator("plugin_id", "node_type")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return _validate_identifier(value, field_name="identifier")

    @field_validator("node_type")
    @classmethod
    def validate_plugin_node_namespace(cls, value: str) -> str:
        if not value.startswith("plugin."):
            raise ValueError("plugin node_type must start with 'plugin.'")
        return value

    @field_validator(
        "plugin_version",
        "node_version",
        "display_name",
        "category",
        "entrypoint",
    )
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must be a non-empty string")
        if len(normalized) > 512:
            raise ValueError("value is too long")
        return normalized

    @model_validator(mode="after")
    def validate_io_declarations(self) -> Self:
        input_port_names = _unique_names(self.input_ports, field_name="input_ports")
        output_port_names = _unique_names(
            self.output_ports,
            field_name="output_ports",
        )
        input_slot_names = _unique_names(
            self.input_table_slots,
            field_name="input_table_slots",
        )
        output_slot_names = _unique_names(
            self.output_table_slots,
            field_name="output_table_slots",
        )
        unknown_inputs = sorted(input_slot_names - input_port_names)
        unknown_outputs = sorted(output_slot_names - output_port_names)
        if unknown_inputs:
            raise ValueError(
                "input table slots require matching input ports: "
                + ", ".join(unknown_inputs)
            )
        if unknown_outputs:
            raise ValueError(
                "output table slots require matching output ports: "
                + ", ".join(unknown_outputs)
            )
        input_ports = {port.name: port for port in self.input_ports}
        inconsistent_inputs = sorted(
            slot.name
            for slot in self.input_table_slots
            if slot.required != input_ports[slot.name].required
        )
        if inconsistent_inputs:
            raise ValueError(
                "input table slot required flags must match input ports: "
                + ", ".join(inconsistent_inputs)
            )
        return self

    def to_node_definition(self) -> NodeDefinitionSpec:
        config_properties = dict(self.config_schema.to_spec().properties)
        config_properties.update(
            {
                "allow_external_actions": NodeConfigFieldSpec(
                    type="boolean",
                    title="Allow External Actions",
                    default=False,
                ),
                "enable_execute": NodeConfigFieldSpec(
                    type="boolean",
                    title="Enable Execute",
                    default=False,
                ),
            }
        )
        return NodeDefinitionSpec(
            node_type=self.node_type,
            node_version=self.node_version,
            display_name=self.display_name,
            plugin_id=self.plugin_id,
            provider_type="user_plugin",
            category=self.category,
            ui_visibility="visible",
            enabled=True,
            implementation_ref=PLUGIN_EXTERNAL_IMPLEMENTATION_REF,
            input_ports=tuple(port.to_spec() for port in self.input_ports),
            output_ports=tuple(port.to_spec() for port in self.output_ports),
            input_table_slots=tuple(slot.to_spec() for slot in self.input_table_slots),
            output_table_slots=tuple(
                slot.to_spec() for slot in self.output_table_slots
            ),
            execution_mode=PLUGIN_NODE_EXECUTION_MODE,
            config_schema=NodeConfigSchemaSpec(properties=config_properties),
        )


def _validate_identifier(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not _IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(f"{field_name} contains unsupported characters")
    return normalized


def _unique_names(items: list[Any], *, field_name: str) -> set[str]:
    names = [item.name for item in items]
    if len(names) != len(set(names)):
        raise ValueError(f"{field_name} names must be unique")
    return set(names)
