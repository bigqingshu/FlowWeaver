from __future__ import annotations

from typing import Any


def validate_binding_object(
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


def manifest_string(
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


def validate_execution_mode(
    manifest: dict[str, Any],
    *,
    execution_mode: str,
    validation_errors: list[str],
) -> None:
    modes_value = manifest.get("execution_modes")
    if modes_value is None:
        modes_value = manifest.get("execution_mode")
    modes = string_set(
        modes_value,
        manifest_key="execution_modes",
        validation_errors=validation_errors,
    )
    if modes is not None and execution_mode not in modes:
        validation_errors.append(
            f"plugin_manifest.execution_modes does not allow {execution_mode}"
        )


def validate_bindings_against_manifest(
    manifest: dict[str, Any],
    *,
    key: str,
    bindings: dict[str, Any],
    validation_errors: list[str],
) -> None:
    declarations = manifest.get(key)
    declared_names = manifest_declared_names(
        declarations,
        manifest_key=key,
        validation_errors=validation_errors,
    )
    if declared_names is None:
        return
    for binding_name in bindings:
        if binding_name not in declared_names:
            validation_errors.append(f"{key} does not declare binding: {binding_name}")
    for required_name in manifest_required_names(
        declarations,
        manifest_key=key,
        validation_errors=validation_errors,
    ):
        if required_name not in bindings:
            validation_errors.append(f"{key} requires binding: {required_name}")


def manifest_declared_names(
    declarations: Any,
    *,
    manifest_key: str,
    validation_errors: list[str],
) -> set[str] | None:
    if declarations is None:
        return None
    if isinstance(declarations, list):
        return string_set(
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


def manifest_required_names(
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


def validate_required_params(
    manifest: dict[str, Any],
    *,
    params: dict[str, Any],
    validation_errors: list[str],
) -> None:
    required_params = string_set(
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


def manifest_external_actions(
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


def string_set(
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
