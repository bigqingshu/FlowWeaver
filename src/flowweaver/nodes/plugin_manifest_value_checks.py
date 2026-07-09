from __future__ import annotations

from typing import Any


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
