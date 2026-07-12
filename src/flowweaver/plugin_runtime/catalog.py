from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from flowweaver.nodes.registry import NodeDefinitionSpec
from flowweaver.nodes.registry_specs import stable_json_hash
from flowweaver.plugin_runtime.manifest import PluginManifestModel


@dataclass(frozen=True)
class PluginDescriptor:
    package_name: str
    package_dir: Path
    manifest_path: Path
    entrypoint_path: Path
    manifest_hash: str
    manifest: PluginManifestModel

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.manifest.node_type, self.manifest.node_version)

    def to_node_definition(self) -> NodeDefinitionSpec:
        return self.manifest.to_node_definition()


@dataclass(frozen=True)
class PluginCatalogEntry:
    package_name: str
    enabled: bool
    disabled_reason: str | None = None
    descriptor: PluginDescriptor | None = None

    @property
    def plugin_id(self) -> str | None:
        return self.descriptor.manifest.plugin_id if self.descriptor else None

    @property
    def plugin_version(self) -> str | None:
        return self.descriptor.manifest.plugin_version if self.descriptor else None

    @property
    def node_type(self) -> str | None:
        return self.descriptor.manifest.node_type if self.descriptor else None

    @property
    def node_version(self) -> str | None:
        return self.descriptor.manifest.node_version if self.descriptor else None

    def disable(self, reason: str) -> PluginCatalogEntry:
        return replace(self, enabled=False, disabled_reason=reason)

    def to_public_data(self) -> dict[str, object]:
        manifest = self.descriptor.manifest if self.descriptor else None
        return {
            "package_name": self.package_name,
            "plugin_id": manifest.plugin_id if manifest else None,
            "plugin_version": manifest.plugin_version if manifest else None,
            "node_type": manifest.node_type if manifest else None,
            "node_version": manifest.node_version if manifest else None,
            "display_name": manifest.display_name if manifest else None,
            "category": manifest.category if manifest else None,
            "execution_mode": manifest.execution_mode if manifest else None,
            "protocol": manifest.protocol if manifest else None,
            "external_actions": manifest.external_actions if manifest else None,
            "manifest_hash": (
                self.descriptor.manifest_hash if self.descriptor else None
            ),
            "enabled": self.enabled,
            "disabled_reason": self.disabled_reason,
        }


@dataclass(frozen=True)
class PluginCatalogState:
    catalog_hash: str
    plugin_count: int
    enabled_count: int


class PluginCatalog:
    def __init__(self, entries: Iterable[PluginCatalogEntry] = ()) -> None:
        self._entries = tuple(
            sorted(entries, key=lambda entry: entry.package_name.casefold())
        )

    @classmethod
    def empty(cls) -> PluginCatalog:
        return cls()

    def list_entries(self) -> tuple[PluginCatalogEntry, ...]:
        return self._entries

    def node_definitions(self) -> tuple[NodeDefinitionSpec, ...]:
        return tuple(
            entry.descriptor.to_node_definition()
            for entry in self._entries
            if entry.enabled and entry.descriptor is not None
        )

    def with_reserved_definitions(
        self,
        definitions: Iterable[NodeDefinitionSpec],
        *,
        reserved_plugin_ids: Iterable[str] = (),
    ) -> PluginCatalog:
        reserved_keys = {definition.registry_key for definition in definitions}
        reserved_ids = set(reserved_plugin_ids)
        entries: list[PluginCatalogEntry] = []
        for entry in self._entries:
            descriptor = entry.descriptor
            if not entry.enabled or descriptor is None:
                entries.append(entry)
                continue
            if descriptor.registry_key in reserved_keys:
                node_type, node_version = descriptor.registry_key
                entries.append(
                    entry.disable(
                        "plugin node conflicts with a reserved node definition: "
                        f"{node_type}@{node_version}"
                    )
                )
                continue
            if descriptor.manifest.plugin_id in reserved_ids:
                entries.append(
                    entry.disable(
                        "plugin_id is reserved by FlowWeaver: "
                        f"{descriptor.manifest.plugin_id}"
                    )
                )
                continue
            entries.append(entry)
        return PluginCatalog(entries)

    def catalog_state(self) -> PluginCatalogState:
        public_data = [entry.to_public_data() for entry in self._entries]
        return PluginCatalogState(
            catalog_hash=stable_json_hash(public_data),
            plugin_count=len(public_data),
            enabled_count=sum(entry.enabled for entry in self._entries),
        )
