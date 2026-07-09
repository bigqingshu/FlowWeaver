from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowweaver.engine.runtime_models import SharedPublication


class SharedTableNodeValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PublishSharedTablesConfig:
    share_name: str
    export_names: tuple[str, ...]
    retention_policy: dict[str, Any]


@dataclass(frozen=True)
class ReadSharedTablesConfig:
    share_name: str
    version_policy: str
    exact_version: int | None
    selected_members: tuple[str, ...] | None


def publish_shared_tables_config(
    config: dict[str, Any],
    *,
    input_ref_count: int,
) -> PublishSharedTablesConfig:
    share_name = _required_str_config(config, "share_name")
    export_names = _required_str_list_config(config, "export_names")
    if len(export_names) != input_ref_count:
        raise SharedTableNodeValidationError(
            "PublishSharedTablesNode config.export_names must match input_refs"
        )
    if len(set(export_names)) != len(export_names):
        raise SharedTableNodeValidationError(
            "PublishSharedTablesNode config.export_names must be unique"
        )
    return PublishSharedTablesConfig(
        share_name=share_name,
        export_names=export_names,
        retention_policy=_retention_policy(config),
    )


def read_shared_tables_config(config: dict[str, Any]) -> ReadSharedTablesConfig:
    return ReadSharedTablesConfig(
        share_name=_required_str_config(config, "share_name"),
        version_policy=_required_str_config(config, "version_policy"),
        exact_version=_optional_int_config(config, "exact_version"),
        selected_members=_optional_str_list_config(config, "selected_members"),
    )


def shared_publication_ref(publication: SharedPublication) -> str:
    return (
        "shared-publication:"
        f"{publication.share_name}:"
        f"{publication.publication_version}:"
        f"{publication.publication_id}"
    )


def single_out_binding(output_refs: list[str]) -> dict[str, str]:
    if not output_refs:
        return {}
    return {"out": output_refs[0]}


def _required_str_config(config: dict[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value:
        raise SharedTableNodeValidationError(
            f"config.{key} must be a non-empty string"
        )
    return value


def _optional_str_list_config(
    config: dict[str, Any],
    key: str,
) -> tuple[str, ...] | None:
    value = config.get(key)
    if value is None:
        return None
    return _str_list_config_value(value, key)


def _required_str_list_config(
    config: dict[str, Any],
    key: str,
) -> tuple[str, ...]:
    value = config.get(key)
    if value is None:
        raise SharedTableNodeValidationError(f"config.{key} must be a list")
    return _str_list_config_value(value, key)


def _str_list_config_value(value: Any, key: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise SharedTableNodeValidationError(f"config.{key} must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise SharedTableNodeValidationError(
                f"config.{key} must contain non-empty strings"
            )
        items.append(item)
    return tuple(items)


def _optional_int_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int | None = None,
) -> int | None:
    value = config.get(key, default)
    if value is None:
        return None
    if not isinstance(value, int):
        raise SharedTableNodeValidationError(f"config.{key} must be an integer")
    return value


def _retention_policy(config: dict[str, Any]) -> dict[str, Any]:
    retention_seconds = _optional_int_config(config, "retention_seconds")
    if retention_seconds is None:
        return {}
    if retention_seconds <= 0:
        raise SharedTableNodeValidationError(
            "PublishSharedTablesNode config.retention_seconds must be positive"
        )
    return {"retention_seconds": retention_seconds}
