from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowweaver.nodes.registry_config_specs import NodeConfigSchemaSpec
from flowweaver.nodes.registry_io_specs import (
    NodePortSpec,
    NodeTableInputSlotSpec,
    NodeTableOutputSlotSpec,
)


@dataclass(frozen=True)
class NodeDefinitionSpec:
    node_type: str
    node_version: str
    display_name: str
    plugin_id: str = "flowweaver.core"
    provider_type: str = "core"
    category: str | None = None
    ui_visibility: str = "visible"
    enabled: bool = True
    disabled_reason: str | None = None
    implementation_ref: str | None = None
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

    def to_catalog_data(self) -> dict[str, Any]:
        return {
            "node_type": self.node_type,
            "node_version": self.node_version,
            "plugin_id": self.plugin_id,
            "provider_type": self.provider_type,
            "category": self.category,
            "ui_visibility": self.ui_visibility,
            "enabled": self.enabled,
            "disabled_reason": self.disabled_reason,
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
            "config_schema_version": self.config_schema_version,
            "config_schema": (
                self.config_schema.to_schema()
                if self.config_schema is not None
                else None
            ),
        }
