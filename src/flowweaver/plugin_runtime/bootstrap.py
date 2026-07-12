from __future__ import annotations

from pathlib import Path

from flowweaver.nodes.default_registry import default_node_definitions
from flowweaver.plugin_runtime.catalog import PluginCatalog
from flowweaver.plugin_runtime.discovery import discover_plugins


def load_plugin_catalog(plugin_root: Path) -> PluginCatalog:
    core_definitions = default_node_definitions()
    return discover_plugins(plugin_root).with_reserved_definitions(
        core_definitions,
        reserved_plugin_ids={"flowweaver.core", "flowweaver.dev_test"},
    )
