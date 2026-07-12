from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from pydantic import ValidationError

from flowweaver.plugin_runtime.catalog import (
    PluginCatalog,
    PluginCatalogEntry,
    PluginDescriptor,
)
from flowweaver.plugin_runtime.manifest import PluginManifestModel

MAX_PLUGIN_DIRECTORIES = 256
MAX_PLUGIN_MANIFEST_BYTES = 256 * 1024


def discover_plugins(
    plugin_root: Path,
    *,
    max_plugin_directories: int = MAX_PLUGIN_DIRECTORIES,
    max_manifest_bytes: int = MAX_PLUGIN_MANIFEST_BYTES,
) -> PluginCatalog:
    root = plugin_root.resolve()
    if not root.exists():
        return PluginCatalog.empty()
    if not root.is_dir():
        return PluginCatalog(
            [
                PluginCatalogEntry(
                    package_name=root.name or "plugins",
                    enabled=False,
                    disabled_reason="plugin root is not a directory",
                )
            ]
        )

    try:
        packages = sorted(
            (path for path in root.iterdir() if path.is_dir()),
            key=lambda path: path.name.casefold(),
        )
    except OSError as exc:
        return PluginCatalog(
            [
                PluginCatalogEntry(
                    package_name=root.name or "plugins",
                    enabled=False,
                    disabled_reason=_bounded_reason(
                        f"could not scan plugin root: {exc}"
                    ),
                )
            ]
        )

    entries = [
        _discover_package(
            root,
            package,
            max_manifest_bytes=max_manifest_bytes,
        )
        for package in packages[:max_plugin_directories]
    ]
    if len(packages) > max_plugin_directories:
        entries.append(
            PluginCatalogEntry(
                package_name="__scan_limit__",
                enabled=False,
                disabled_reason=(
                    "plugin directory limit exceeded: "
                    f"ignored {len(packages) - max_plugin_directories} package(s)"
                ),
            )
        )
    return PluginCatalog(_disable_duplicate_entries(entries))


def _discover_package(
    root: Path,
    package: Path,
    *,
    max_manifest_bytes: int,
) -> PluginCatalogEntry:
    package_name = package.name
    try:
        resolved_package = package.resolve()
        if not resolved_package.is_relative_to(root):
            return _disabled(
                package_name, "plugin package resolves outside plugin root"
            )
        manifest_path = resolved_package / "plugin.json"
        if not manifest_path.is_file():
            return _disabled(package_name, "plugin.json is missing")
        resolved_manifest = manifest_path.resolve()
        if not resolved_manifest.is_relative_to(resolved_package):
            return _disabled(
                package_name, "plugin.json resolves outside plugin package"
            )
        manifest_size = resolved_manifest.stat().st_size
        if manifest_size > max_manifest_bytes:
            return _disabled(
                package_name,
                f"plugin.json exceeds {max_manifest_bytes} bytes",
            )
        manifest_bytes = resolved_manifest.read_bytes()
        manifest_hash = sha256(manifest_bytes).hexdigest()
        manifest_data = json.loads(manifest_bytes.decode("utf-8"))
        manifest = PluginManifestModel.model_validate(manifest_data)
        entrypoint = Path(manifest.entrypoint)
        if entrypoint.is_absolute():
            return _disabled(package_name, "entrypoint must be a relative path")
        entrypoint_path = (resolved_package / entrypoint).resolve()
        if not entrypoint_path.is_relative_to(resolved_package):
            return _disabled(package_name, "entrypoint resolves outside plugin package")
        if not entrypoint_path.is_file():
            return _disabled(package_name, "entrypoint does not exist")
        descriptor = PluginDescriptor(
            package_name=package_name,
            package_dir=resolved_package,
            manifest_path=resolved_manifest,
            entrypoint_path=entrypoint_path,
            manifest_hash=manifest_hash,
            manifest=manifest,
        )
        return PluginCatalogEntry(
            package_name=package_name,
            enabled=True,
            descriptor=descriptor,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        return _disabled(
            package_name,
            _bounded_reason(f"invalid plugin manifest: {exc}"),
        )


def _disable_duplicate_entries(
    entries: list[PluginCatalogEntry],
) -> list[PluginCatalogEntry]:
    conflicts: dict[int, list[str]] = {}
    by_plugin_id: dict[str, list[int]] = {}
    by_registry_key: dict[tuple[str, str], list[int]] = {}
    for index, entry in enumerate(entries):
        if not entry.enabled or entry.descriptor is None:
            continue
        descriptor = entry.descriptor
        by_plugin_id.setdefault(descriptor.manifest.plugin_id, []).append(index)
        by_registry_key.setdefault(descriptor.registry_key, []).append(index)

    for plugin_id, indexes in by_plugin_id.items():
        if len(indexes) > 1:
            for index in indexes:
                conflicts.setdefault(index, []).append(
                    f"duplicate plugin_id: {plugin_id}"
                )
    for registry_key, indexes in by_registry_key.items():
        if len(indexes) > 1:
            node_type, node_version = registry_key
            for index in indexes:
                conflicts.setdefault(index, []).append(
                    f"duplicate plugin node definition: {node_type}@{node_version}"
                )

    for index, reasons in conflicts.items():
        entries[index] = replace(
            entries[index],
            enabled=False,
            disabled_reason="; ".join(reasons),
        )
    return entries


def _disabled(package_name: str, reason: str) -> PluginCatalogEntry:
    return PluginCatalogEntry(
        package_name=package_name,
        enabled=False,
        disabled_reason=_bounded_reason(reason),
    )


def _bounded_reason(reason: str) -> str:
    return " ".join(str(reason).split())[:512]
