from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowweaver.nodes.plugin_manifest_checks import (
    manifest_external_actions as _plugin_manifest_external_actions,
)
from flowweaver.nodes.plugin_manifest_checks import (
    manifest_string as _plugin_manifest_string,
)
from flowweaver.nodes.plugin_manifest_checks import (
    validate_binding_object as _plugin_validate_binding_object,
)
from flowweaver.nodes.plugin_manifest_checks import (
    validate_bindings_against_manifest as _plugin_validate_bindings_against_manifest,
)
from flowweaver.nodes.plugin_manifest_checks import (
    validate_execution_mode as _plugin_validate_execution_mode,
)
from flowweaver.nodes.plugin_manifest_checks import (
    validate_required_params as _plugin_validate_required_params,
)


@dataclass(frozen=True)
class PluginManifestState:
    validation_errors: list[str]
    manifest_status: str
    manifest_plugin_id: str
    manifest_plugin_version: str
    plugin_found: bool
    external_actions_declared: bool
    external_actions_blocked: bool


def collect_plugin_manifest_state(
    *,
    plugin_id: str,
    plugin_version: str,
    plugin_manifest: dict[str, Any],
    params: dict[str, Any],
    input_bindings: dict[str, Any],
    output_bindings: dict[str, Any],
    execution_mode: str,
    allow_external_actions: bool,
    enable_execute: bool,
) -> PluginManifestState:
    validation_errors: list[str] = []
    manifest_status = "missing"
    manifest_plugin_id = ""
    manifest_plugin_version = ""
    plugin_found = False
    external_actions_declared = False
    external_actions_blocked = False

    _plugin_validate_binding_object(
        input_bindings,
        binding_name="input_bindings",
        validation_errors=validation_errors,
    )
    _plugin_validate_binding_object(
        output_bindings,
        binding_name="output_bindings",
        validation_errors=validation_errors,
    )

    if plugin_manifest:
        manifest_status = "valid"
        manifest_plugin_id = _plugin_manifest_string(
            plugin_manifest,
            "plugin_id",
            required=True,
            validation_errors=validation_errors,
        )
        manifest_plugin_version = _plugin_manifest_string(
            plugin_manifest,
            "plugin_version",
            validation_errors=validation_errors,
        )
        if manifest_plugin_id == plugin_id:
            plugin_found = True
        else:
            validation_errors.append(
                "plugin_manifest.plugin_id does not match config.plugin_id"
            )
        if (
            plugin_version
            and manifest_plugin_version
            and plugin_version != manifest_plugin_version
        ):
            validation_errors.append(
                "plugin_manifest.plugin_version does not match config.plugin_version"
            )
        _plugin_validate_execution_mode(
            plugin_manifest,
            execution_mode=execution_mode,
            validation_errors=validation_errors,
        )
        _plugin_validate_bindings_against_manifest(
            plugin_manifest,
            key="inputs",
            bindings=input_bindings,
            validation_errors=validation_errors,
        )
        _plugin_validate_bindings_against_manifest(
            plugin_manifest,
            key="outputs",
            bindings=output_bindings,
            validation_errors=validation_errors,
        )
        _plugin_validate_required_params(
            plugin_manifest,
            params=params,
            validation_errors=validation_errors,
        )
        external_actions_declared = _plugin_manifest_external_actions(
            plugin_manifest,
            validation_errors=validation_errors,
        )
        if external_actions_declared and not allow_external_actions:
            external_actions_blocked = True
            validation_errors.append(
                "plugin declares external actions but allow_external_actions is false"
            )
    elif enable_execute:
        validation_errors.append("plugin_manifest is not configured")

    return PluginManifestState(
        validation_errors=validation_errors,
        manifest_status=manifest_status,
        manifest_plugin_id=manifest_plugin_id,
        manifest_plugin_version=manifest_plugin_version,
        plugin_found=plugin_found,
        external_actions_declared=external_actions_declared,
        external_actions_blocked=external_actions_blocked,
    )
