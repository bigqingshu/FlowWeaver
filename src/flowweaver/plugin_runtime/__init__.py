"""Trusted plugin manifest discovery and catalog metadata."""

from flowweaver.plugin_runtime.catalog import (
    PluginCatalog,
    PluginCatalogEntry,
    PluginCatalogState,
    PluginDescriptor,
)
from flowweaver.plugin_runtime.discovery import discover_plugins
from flowweaver.plugin_runtime.executor import PluginExternalProcessExecutor
from flowweaver.plugin_runtime.manifest import (
    PLUGIN_EXTERNAL_IMPLEMENTATION_REF,
    PLUGIN_JSONL_PROTOCOL_V1,
    PluginManifestModel,
)

__all__ = [
    "PLUGIN_EXTERNAL_IMPLEMENTATION_REF",
    "PLUGIN_JSONL_PROTOCOL_V1",
    "PluginCatalog",
    "PluginCatalogEntry",
    "PluginCatalogState",
    "PluginDescriptor",
    "PluginExternalProcessExecutor",
    "PluginManifestModel",
    "discover_plugins",
]
