from __future__ import annotations

import json
from pathlib import Path

from flowweaver.nodes.registry import NodeDefinitionSpec
from flowweaver.plugin_runtime.discovery import discover_plugins
from flowweaver.plugin_runtime.manifest import (
    PLUGIN_EXTERNAL_IMPLEMENTATION_REF,
    PLUGIN_JSONL_PROTOCOL_V1,
)


def test_discovery_registers_valid_manifest_without_importing_runner(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    _write_plugin(
        plugin_root,
        "table_projection",
        _manifest(),
        runner_text="raise RuntimeError('runner must not be imported')\n",
    )

    catalog = discover_plugins(plugin_root)

    entries = catalog.list_entries()
    assert len(entries) == 1
    assert entries[0].enabled is True
    assert entries[0].disabled_reason is None
    definition = catalog.node_definitions()[0]
    assert definition.node_type == "plugin.example.table_projection"
    assert definition.plugin_id == "example.table_projection"
    assert definition.provider_type == "user_plugin"
    assert definition.category == "table"
    assert definition.implementation_ref == PLUGIN_EXTERNAL_IMPLEMENTATION_REF
    assert definition.input_ports[0].name == "in"
    assert definition.input_table_slots[0].name == "in"
    assert definition.output_table_slots[0].allow_new_runtime_sql is True
    assert definition.config_schema is not None
    config_properties = definition.config_schema.to_schema()["properties"]
    assert config_properties["field_name"] == {
        "type": "string",
        "title": "Field Name",
        "required": True,
    }
    assert config_properties["enable_execute"]["default"] is False
    assert config_properties["allow_external_actions"]["default"] is False


def test_discovery_disables_invalid_manifest_without_blocking_valid_plugin(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    _write_plugin(plugin_root, "valid", _manifest())
    invalid_dir = plugin_root / "invalid"
    invalid_dir.mkdir(parents=True)
    (invalid_dir / "plugin.json").write_text("{broken", encoding="utf-8")

    catalog = discover_plugins(plugin_root)

    by_package = {entry.package_name: entry for entry in catalog.list_entries()}
    assert by_package["valid"].enabled is True
    assert by_package["invalid"].enabled is False
    assert "invalid plugin manifest" in (by_package["invalid"].disabled_reason or "")
    assert len(catalog.node_definitions()) == 1


def test_discovery_disables_entrypoint_outside_package(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_plugin(
        plugin_root,
        "outside",
        _manifest(entrypoint="../outside.py"),
        create_entrypoint=False,
    )
    (package.parent / "outside.py").write_text("print('outside')\n", encoding="utf-8")

    entry = discover_plugins(plugin_root).list_entries()[0]

    assert entry.enabled is False
    assert entry.disabled_reason == "entrypoint resolves outside plugin package"


def test_discovery_disables_inconsistent_input_slot_requirement(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    manifest = _manifest()
    manifest["input_table_slots"] = [{"name": "in", "required": False}]
    _write_plugin(plugin_root, "inconsistent", manifest)

    entry = discover_plugins(plugin_root).list_entries()[0]

    assert entry.enabled is False
    assert "required flags must match input ports" in (
        entry.disabled_reason or ""
    )


def test_discovery_disables_duplicate_plugin_and_node_ids(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    _write_plugin(plugin_root, "first", _manifest())
    _write_plugin(plugin_root, "second", _manifest())

    entries = discover_plugins(plugin_root).list_entries()

    assert len(entries) == 2
    assert all(entry.enabled is False for entry in entries)
    assert all(
        "duplicate plugin_id" in (entry.disabled_reason or "") for entry in entries
    )
    assert all(
        "duplicate plugin node definition" in (entry.disabled_reason or "")
        for entry in entries
    )


def test_catalog_disables_reserved_core_definition_and_plugin_id(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    _write_plugin(
        plugin_root,
        "reserved_node",
        _manifest(
            plugin_id="example.reserved",
            node_type="plugin.core_conflict",
        ),
    )
    _write_plugin(
        plugin_root,
        "reserved_plugin",
        _manifest(
            plugin_id="flowweaver.core",
            node_type="plugin.example.reserved",
        ),
    )

    catalog = discover_plugins(plugin_root).with_reserved_definitions(
        [
            NodeDefinitionSpec(
                node_type="plugin.core_conflict",
                node_version="1.0",
                display_name="Core Node",
            )
        ],
        reserved_plugin_ids={"flowweaver.core"},
    )

    by_package = {entry.package_name: entry for entry in catalog.list_entries()}
    assert by_package["reserved_node"].enabled is False
    assert "reserved node definition" in (
        by_package["reserved_node"].disabled_reason or ""
    )
    assert by_package["reserved_plugin"].enabled is False
    assert by_package["reserved_plugin"].disabled_reason == (
        "plugin_id is reserved by FlowWeaver: flowweaver.core"
    )


def test_discovery_enforces_manifest_and_directory_limits(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    _write_plugin(plugin_root, "first", _manifest(plugin_id="first.plugin"))
    _write_plugin(plugin_root, "second", _manifest(plugin_id="second.plugin"))
    oversized = plugin_root / "oversized"
    oversized.mkdir(parents=True)
    (oversized / "plugin.json").write_bytes(b"x" * 65)

    catalog = discover_plugins(
        plugin_root,
        max_plugin_directories=2,
        max_manifest_bytes=64,
    )

    entries = catalog.list_entries()
    assert len(entries) == 3
    limit_entry = next(
        entry for entry in entries if entry.package_name == "__scan_limit__"
    )
    assert limit_entry.enabled is False
    assert limit_entry.disabled_reason == (
        "plugin directory limit exceeded: ignored 1 package(s)"
    )


def test_catalog_hash_changes_with_manifest_content(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_plugin(plugin_root, "plugin", _manifest())
    first = discover_plugins(plugin_root).catalog_state()
    manifest = _manifest()
    manifest["display_name"] = "Changed Display Name"
    (package / "plugin.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )
    second = discover_plugins(plugin_root).catalog_state()

    assert first.plugin_count == 1
    assert first.enabled_count == 1
    assert first.catalog_hash != second.catalog_hash


def test_missing_plugin_root_returns_empty_catalog(tmp_path: Path) -> None:
    state = discover_plugins(tmp_path / "missing").catalog_state()

    assert state.plugin_count == 0
    assert state.enabled_count == 0
    assert len(state.catalog_hash) == 64


def _write_plugin(
    plugin_root: Path,
    package_name: str,
    manifest: dict,
    *,
    runner_text: str = "print('runner')\n",
    create_entrypoint: bool = True,
) -> Path:
    package = plugin_root / package_name
    package.mkdir(parents=True)
    (package / "plugin.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )
    if create_entrypoint:
        (package / str(manifest["entrypoint"])).write_text(
            runner_text,
            encoding="utf-8",
        )
    return package


def _manifest(
    *,
    plugin_id: str = "example.table_projection",
    node_type: str = "plugin.example.table_projection",
    entrypoint: str = "runner.py",
) -> dict:
    return {
        "manifest_version": "1",
        "plugin_id": plugin_id,
        "plugin_version": "1.0.0",
        "node_type": node_type,
        "node_version": "1.0",
        "display_name": "Table Projection",
        "category": "table",
        "config_schema": {
            "type": "object",
            "properties": {
                "field_name": {
                    "type": "string",
                    "title": "Field Name",
                    "required": True,
                }
            },
        },
        "input_ports": [{"name": "in", "required": True}],
        "output_ports": [{"name": "out"}],
        "input_table_slots": [{"name": "in", "required": True}],
        "output_table_slots": [
            {
                "name": "out",
                "allow_new_runtime_sql": True,
            }
        ],
        "execution_mode": "external_process",
        "protocol": PLUGIN_JSONL_PROTOCOL_V1,
        "entrypoint": entrypoint,
        "external_actions": False,
    }
