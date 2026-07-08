from __future__ import annotations

import json
from typing import Any

from flowweaver.nodes.builtin_table_node_types import PLUGIN_NODE_TYPE
from flowweaver.nodes.table_node_common import (
    bool_status as _bool_status,
)
from flowweaver.nodes.table_node_common import (
    simple_schema as _simple_schema,
)
from flowweaver.nodes.table_node_config import (
    bool_config as _bool_config,
)
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    object_config as _object_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class PluginNodeHandler:
    node_type = PLUGIN_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        plugin_id = _node_string_config(
            task.config,
            "plugin_id",
            node_type=self.node_type,
        )
        plugin_version = _optional_string_config(
            task.config,
            "plugin_version",
            node_type=self.node_type,
        )
        params = _object_config(task.config, "params", node_type=self.node_type)
        input_bindings = _object_config(
            task.config,
            "input_bindings",
            node_type=self.node_type,
        )
        output_bindings = _object_config(
            task.config,
            "output_bindings",
            node_type=self.node_type,
        )
        plugin_manifest = _object_config(
            task.config,
            "plugin_manifest",
            node_type=self.node_type,
        )
        execution_mode = _enum_config(
            task.config,
            "execution_mode",
            default="external_process",
            allowed={"in_process", "external_process"},
            node_type=self.node_type,
        )
        allow_external_actions = _bool_config(
            task.config,
            "allow_external_actions",
            default=False,
        )
        enable_execute = _bool_config(
            task.config,
            "enable_execute",
            default=False,
        )
        status_row = _plugin_status_row(
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            plugin_manifest=plugin_manifest,
            params=params,
            input_bindings=input_bindings,
            output_bindings=output_bindings,
            input_ref_count=len(task.input_refs),
            execution_mode=execution_mode,
            allow_external_actions=allow_external_actions,
            enable_execute=enable_execute,
        )
        return [
            context.publish_rows(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=_plugin_status_schema(),
                rows=[status_row],
            )
        ]


def _plugin_status_row(
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
            else "missing" if not plugin_manifest else "invalid"
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
    status_row = {
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
    return status_row


def _plugin_validate_binding_object(
    bindings: dict[str, Any],
    *,
    binding_name: str,
    validation_errors: list[str],
) -> None:
    for key, value in bindings.items():
        if not isinstance(key, str) or not key.strip():
            validation_errors.append(f"{binding_name} contains an empty binding name")
        if not isinstance(value, str) or not value.strip():
            validation_errors.append(
                f"{binding_name}.{key} must map to a non-empty string"
            )


def _plugin_manifest_string(
    manifest: dict[str, Any],
    key: str,
    *,
    validation_errors: list[str],
    required: bool = False,
) -> str:
    value = manifest.get(key)
    if value is None:
        if required:
            validation_errors.append(f"plugin_manifest.{key} is required")
        return ""
    if not isinstance(value, str) or not value.strip():
        validation_errors.append(f"plugin_manifest.{key} must be a string")
        return ""
    return value.strip()


def _plugin_validate_execution_mode(
    manifest: dict[str, Any],
    *,
    execution_mode: str,
    validation_errors: list[str],
) -> None:
    modes_value = manifest.get("execution_modes")
    if modes_value is None:
        modes_value = manifest.get("execution_mode")
    modes = _plugin_string_set(
        modes_value,
        manifest_key="execution_modes",
        validation_errors=validation_errors,
    )
    if modes is not None and execution_mode not in modes:
        validation_errors.append(
            f"plugin_manifest.execution_modes does not allow {execution_mode}"
        )


def _plugin_validate_bindings_against_manifest(
    manifest: dict[str, Any],
    *,
    key: str,
    bindings: dict[str, Any],
    validation_errors: list[str],
) -> None:
    declarations = manifest.get(key)
    declared_names = _plugin_manifest_declared_names(
        declarations,
        manifest_key=key,
        validation_errors=validation_errors,
    )
    if declared_names is None:
        return
    for binding_name in bindings:
        if binding_name not in declared_names:
            validation_errors.append(
                f"{key} does not declare binding: {binding_name}"
            )
    for required_name in _plugin_manifest_required_names(
        declarations,
        manifest_key=key,
        validation_errors=validation_errors,
    ):
        if required_name not in bindings:
            validation_errors.append(
                f"{key} requires binding: {required_name}"
            )


def _plugin_manifest_declared_names(
    declarations: Any,
    *,
    manifest_key: str,
    validation_errors: list[str],
) -> set[str] | None:
    if declarations is None:
        return None
    if isinstance(declarations, list):
        return _plugin_string_set(
            declarations,
            manifest_key=manifest_key,
            validation_errors=validation_errors,
        )
    if isinstance(declarations, dict):
        names: set[str] = set()
        for name in declarations:
            if not isinstance(name, str) or not name.strip():
                validation_errors.append(
                    f"plugin_manifest.{manifest_key} contains an empty name"
                )
                continue
            names.add(name.strip())
        return names
    validation_errors.append(f"plugin_manifest.{manifest_key} must be a list or object")
    return None


def _plugin_manifest_required_names(
    declarations: Any,
    *,
    manifest_key: str,
    validation_errors: list[str],
) -> set[str]:
    if not isinstance(declarations, dict):
        return set()
    required: set[str] = set()
    for name, spec in declarations.items():
        if not isinstance(name, str) or not name.strip():
            continue
        normalized_name = name.strip()
        if spec is True:
            required.add(normalized_name)
        elif isinstance(spec, dict):
            required_value = spec.get("required", False)
            if isinstance(required_value, bool):
                if required_value:
                    required.add(normalized_name)
            else:
                validation_errors.append(
                    f"plugin_manifest.{manifest_key}.{normalized_name}.required "
                    "must be a boolean"
                )
    return required


def _plugin_validate_required_params(
    manifest: dict[str, Any],
    *,
    params: dict[str, Any],
    validation_errors: list[str],
) -> None:
    required_params = _plugin_string_set(
        manifest.get("required_params"),
        manifest_key="required_params",
        validation_errors=validation_errors,
    )
    if required_params is None:
        return
    for required_param in sorted(required_params):
        if required_param not in params:
            validation_errors.append(
                f"plugin_manifest.required_params requires param: {required_param}"
            )


def _plugin_manifest_external_actions(
    manifest: dict[str, Any],
    *,
    validation_errors: list[str],
) -> bool:
    declared = False
    for key in (
        "has_external_actions",
        "requires_external_actions",
        "external_actions",
    ):
        if key not in manifest:
            continue
        value = manifest[key]
        if isinstance(value, bool):
            declared = declared or value
        else:
            validation_errors.append(f"plugin_manifest.{key} must be a boolean")
    side_effect_level = manifest.get("side_effect_level")
    if isinstance(side_effect_level, str):
        declared = declared or side_effect_level.strip().lower() in {
            "external",
            "write_external",
            "external_write",
            "high",
        }
    elif side_effect_level is not None:
        validation_errors.append("plugin_manifest.side_effect_level must be a string")
    return declared


def _plugin_string_set(
    value: Any,
    *,
    manifest_key: str,
    validation_errors: list[str],
) -> set[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        if not value.strip():
            validation_errors.append(f"plugin_manifest.{manifest_key} is empty")
            return set()
        return {value.strip()}
    if not isinstance(value, list):
        validation_errors.append(
            f"plugin_manifest.{manifest_key} must be a string list"
        )
        return None
    items: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            validation_errors.append(
                f"plugin_manifest.{manifest_key} must be a string list"
            )
            continue
        normalized = item.strip()
        if normalized in items:
            validation_errors.append(
                f"plugin_manifest.{manifest_key} contains duplicate value: "
                f"{normalized}"
            )
        items.add(normalized)
    return items


def _plugin_status_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("status", "TEXT", False),
            ("plugin_id", "TEXT", False),
            ("plugin_version", "TEXT", False),
            ("manifest_status", "TEXT", False),
            ("manifest_plugin_id", "TEXT", False),
            ("manifest_plugin_version", "TEXT", False),
            ("execution_mode", "TEXT", False),
            ("input_ref_count", "INTEGER", False),
            ("param_count", "INTEGER", False),
            ("input_binding_count", "INTEGER", False),
            ("output_binding_count", "INTEGER", False),
            ("plugin_found", "TEXT", False),
            ("validation_status", "TEXT", False),
            ("validation_errors", "TEXT", False),
            ("allow_external_actions", "TEXT", False),
            ("enable_execute", "TEXT", False),
            ("external_actions_declared", "TEXT", False),
            ("execution_ready", "TEXT", False),
            ("actual_execute", "TEXT", False),
            ("skipped_reason", "TEXT", False),
        ]
    )


