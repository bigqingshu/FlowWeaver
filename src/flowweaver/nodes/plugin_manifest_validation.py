from __future__ import annotations

import json
from typing import Any

from flowweaver.nodes.plugin_manifest_state import (
    collect_plugin_manifest_state as _collect_plugin_manifest_state,
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
    manifest_state = _collect_plugin_manifest_state(
        plugin_id=plugin_id,
        plugin_version=plugin_version,
        plugin_manifest=plugin_manifest,
        params=params,
        input_bindings=input_bindings,
        output_bindings=output_bindings,
        execution_mode=execution_mode,
        allow_external_actions=allow_external_actions,
        enable_execute=enable_execute,
    )
    validation_errors = manifest_state.validation_errors
    manifest_status = manifest_state.manifest_status

    if validation_errors:
        external_only_block = (
            manifest_state.external_actions_blocked
            and len(validation_errors) == 1
        )
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
        "manifest_plugin_id": manifest_state.manifest_plugin_id,
        "manifest_plugin_version": manifest_state.manifest_plugin_version,
        "execution_mode": execution_mode,
        "input_ref_count": input_ref_count,
        "param_count": len(params),
        "input_binding_count": len(input_bindings),
        "output_binding_count": len(output_bindings),
        "plugin_found": _bool_status(manifest_state.plugin_found),
        "validation_status": validation_status,
        "validation_errors": validation_errors_text,
        "allow_external_actions": _bool_status(allow_external_actions),
        "enable_execute": _bool_status(enable_execute),
        "external_actions_declared": _bool_status(
            manifest_state.external_actions_declared
        ),
        "execution_ready": _bool_status(execution_ready),
        "actual_execute": "false",
        "skipped_reason": skipped_reason,
    }
