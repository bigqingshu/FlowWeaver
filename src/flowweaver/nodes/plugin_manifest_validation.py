from __future__ import annotations

import json
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
from flowweaver.nodes.table_node_common import bool_status as _bool_status


def build_plugin_status_row(
    *,
    plugin_id: str,
    plugin_version: str,
    plugin_manifest: dict[str, Any],
    params: dict[str, Any],
    input_bindings: dict[str, Any],
    output_bindings: dict[str, Any],
    input_ref_count: int,
    execution_mode: str,
    allow_external_actions: bool,
    enable_execute: bool,
) -> dict[str, Any]:
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
    else:
        if enable_execute:
            validation_errors.append("plugin_manifest is not configured")

    if validation_errors:
        external_only_block = external_actions_blocked and len(validation_errors) == 1
        manifest_status = (
            "valid"
            if external_only_block
            else "missing"
            if not plugin_manifest
            else "invalid"
        )
        validation_status = "blocked" if external_only_block else manifest_status
        status = "blocked" if validation_status == "blocked" else "invalid"
        execution_ready = False
        skipped_reason = (
            "external actions are not allowed"
            if validation_status == "blocked"
            else "plugin validation failed"
        )
    elif not enable_execute:
        validation_status = "skipped" if manifest_status == "missing" else "valid"
        status = "skipped"
        execution_ready = False
        skipped_reason = "enable_execute is false"
    else:
        validation_status = "valid"
        status = "skipped"
        execution_ready = True
        skipped_reason = "plugin execution runner is not configured"

    validation_errors_text = (
        json.dumps(validation_errors, ensure_ascii=False)
        if validation_errors
        else ""
    )
    return {
        "status": status,
        "plugin_id": plugin_id,
        "plugin_version": plugin_version,
        "manifest_status": manifest_status,
        "manifest_plugin_id": manifest_plugin_id,
        "manifest_plugin_version": manifest_plugin_version,
        "execution_mode": execution_mode,
        "input_ref_count": input_ref_count,
        "param_count": len(params),
        "input_binding_count": len(input_bindings),
        "output_binding_count": len(output_bindings),
        "plugin_found": _bool_status(plugin_found),
        "validation_status": validation_status,
        "validation_errors": validation_errors_text,
        "allow_external_actions": _bool_status(allow_external_actions),
        "enable_execute": _bool_status(enable_execute),
        "external_actions_declared": _bool_status(external_actions_declared),
        "execution_ready": _bool_status(execution_ready),
        "actual_execute": "false",
        "skipped_reason": skipped_reason,
    }
