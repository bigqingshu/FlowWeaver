from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from flowweaver.protocols.enums import TableRole, TableStorageKind

OUTPUT_TARGET_CONFIG_KEY = "output_target"
OUTPUT_TARGETS_CONFIG_KEYS = ("output_targets", "output_table_targets")
OUTPUT_SAVE_CONFIG_KEY = "output_save"


class TableOutputTargetKind(str, Enum):
    CURRENT = "current"
    NEW_MEMORY = "new_memory"
    NEW_RUNTIME_SQL = "new_runtime_sql"
    EXISTING_MEMORY = "existing_memory"
    EXISTING_RUNTIME_SQL = "existing_runtime_sql"


class TableOutputTargetResolutionStatus(str, Enum):
    NO_CONFIG = "NO_CONFIG"
    RESOLVED = "RESOLVED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class TableOutputTarget:
    slot: str
    target_kind: TableOutputTargetKind
    role: TableRole
    storage_kind: TableStorageKind | None = None
    logical_table_id: str | None = None

    @property
    def is_existing_target(self) -> bool:
        return self.target_kind in {
            TableOutputTargetKind.EXISTING_MEMORY,
            TableOutputTargetKind.EXISTING_RUNTIME_SQL,
        }

    @property
    def is_new_target(self) -> bool:
        return self.target_kind in {
            TableOutputTargetKind.NEW_MEMORY,
            TableOutputTargetKind.NEW_RUNTIME_SQL,
        }


@dataclass(frozen=True)
class TableOutputTargetIssue:
    slot: str
    message: str
    details: dict[str, Any]


@dataclass(frozen=True)
class TableOutputTargetResolution:
    status: TableOutputTargetResolutionStatus
    targets: tuple[TableOutputTarget, ...] = ()
    issue: TableOutputTargetIssue | None = None


def resolve_configured_output_targets(
    config: dict[str, Any],
) -> TableOutputTargetResolution:
    targets: list[TableOutputTarget] = []

    single_target = config.get(OUTPUT_TARGET_CONFIG_KEY)
    if isinstance(single_target, dict):
        target = _target_from_value(
            _optional_string(single_target, "slot") or "out",
            single_target,
        )
        if isinstance(target, TableOutputTargetResolution):
            return target
        if target is not None:
            targets.append(target)

    for key in OUTPUT_TARGETS_CONFIG_KEYS:
        target_configs = config.get(key)
        if isinstance(target_configs, dict):
            for slot, value in target_configs.items():
                if not isinstance(slot, str) or not slot.strip():
                    return _config_error(
                        "",
                        f"{key} contains an empty output slot name",
                    )
                target = _target_from_value(slot.strip(), value)
                if isinstance(target, TableOutputTargetResolution):
                    return target
                if target is not None:
                    targets.append(target)
        elif isinstance(target_configs, list):
            for index, value in enumerate(target_configs):
                if not isinstance(value, dict):
                    return _config_error("", f"{key}[{index}] must be an object")
                slot = _optional_string(value, "slot") or _optional_string(
                    value,
                    "output_slot",
                )
                if slot is None:
                    return _config_error("", f"{key}[{index}] must include slot")
                target = _target_from_value(slot, value)
                if isinstance(target, TableOutputTargetResolution):
                    return target
                if target is not None:
                    targets.append(target)

    output_save = config.get(OUTPUT_SAVE_CONFIG_KEY)
    if isinstance(output_save, dict) and output_save.get("enabled") is True:
        target = _target_from_output_save(output_save)
        if isinstance(target, TableOutputTargetResolution):
            return target
        targets.append(target)

    if not targets:
        return TableOutputTargetResolution(TableOutputTargetResolutionStatus.NO_CONFIG)
    duplicate_slot = _first_duplicate_slot(targets)
    if duplicate_slot is not None:
        return _config_error(
            duplicate_slot,
            f"duplicate output target slot: {duplicate_slot}",
        )
    return TableOutputTargetResolution(
        TableOutputTargetResolutionStatus.RESOLVED,
        targets=tuple(targets),
    )


def default_current_output_target(slot: str = "out") -> TableOutputTarget:
    return TableOutputTarget(
        slot=slot,
        target_kind=TableOutputTargetKind.CURRENT,
        role=TableRole.CURRENT,
    )


def _target_from_output_save(
    value: dict[str, Any],
) -> TableOutputTarget | TableOutputTargetResolution:
    target_type = _optional_string(value, "target_type")
    if target_type in {"memory", "memory_table", "new_memory"}:
        target_kind = TableOutputTargetKind.NEW_MEMORY
    elif target_type in {"runtime_sql", "run_table", "new_runtime_sql"}:
        target_kind = TableOutputTargetKind.NEW_RUNTIME_SQL
    else:
        return _config_error(
            "saved_table",
            f"unsupported output_save target_type: {target_type}",
        )
    return _named_target_from_kind(
        slot=_optional_string(value, "slot") or "saved_table",
        value=value,
        target_kind=target_kind,
    )


def _target_from_value(
    slot: str,
    value: Any,
) -> TableOutputTarget | TableOutputTargetResolution | None:
    if not isinstance(value, dict):
        return _config_error(slot, "output target must be an object")
    raw_target_kind = _optional_string(value, "target_kind") or _optional_string(
        value,
        "target_type",
    )
    if raw_target_kind is None:
        return None
    target_kind = _normalize_target_kind(raw_target_kind)
    if target_kind is None:
        return _config_error(slot, f"unsupported output target kind: {raw_target_kind}")
    if target_kind == TableOutputTargetKind.CURRENT:
        if _target_logical_table_id(value) is not None:
            return _config_error(slot, "current output target must not be named")
        return default_current_output_target(slot)
    return _named_target_from_kind(
        slot=slot,
        value=value,
        target_kind=target_kind,
    )


def _named_target_from_kind(
    *,
    slot: str,
    value: dict[str, Any],
    target_kind: TableOutputTargetKind,
) -> TableOutputTarget | TableOutputTargetResolution:
    logical_table_id = _target_logical_table_id(value)
    if logical_table_id is None:
        return _config_error(slot, f"{target_kind.value} requires table_name")
    storage_kind = _storage_kind_for_target(target_kind)
    return TableOutputTarget(
        slot=slot,
        target_kind=target_kind,
        role=TableRole.AUXILIARY,
        storage_kind=storage_kind,
        logical_table_id=logical_table_id,
    )


def _normalize_target_kind(value: str) -> TableOutputTargetKind | None:
    aliases = {
        "current": TableOutputTargetKind.CURRENT,
        "current_table": TableOutputTargetKind.CURRENT,
        "memory": TableOutputTargetKind.NEW_MEMORY,
        "memory_table": TableOutputTargetKind.NEW_MEMORY,
        "new_memory": TableOutputTargetKind.NEW_MEMORY,
        "runtime_sql": TableOutputTargetKind.NEW_RUNTIME_SQL,
        "run_table": TableOutputTargetKind.NEW_RUNTIME_SQL,
        "new_runtime_sql": TableOutputTargetKind.NEW_RUNTIME_SQL,
        "existing_memory": TableOutputTargetKind.EXISTING_MEMORY,
        "existing_memory_table": TableOutputTargetKind.EXISTING_MEMORY,
        "existing_runtime_sql": TableOutputTargetKind.EXISTING_RUNTIME_SQL,
        "existing_run_table": TableOutputTargetKind.EXISTING_RUNTIME_SQL,
    }
    return aliases.get(value)


def _storage_kind_for_target(
    target_kind: TableOutputTargetKind,
) -> TableStorageKind | None:
    if target_kind in {
        TableOutputTargetKind.NEW_MEMORY,
        TableOutputTargetKind.EXISTING_MEMORY,
    }:
        return TableStorageKind.MEMORY
    if target_kind in {
        TableOutputTargetKind.NEW_RUNTIME_SQL,
        TableOutputTargetKind.EXISTING_RUNTIME_SQL,
    }:
        return TableStorageKind.RUNTIME_SQL
    return None


def _target_logical_table_id(value: dict[str, Any]) -> str | None:
    return (
        _optional_string(value, "logical_table_id")
        or _optional_string(value, "table_name")
        or _optional_string(value, "target_table")
    )


def _first_duplicate_slot(targets: list[TableOutputTarget]) -> str | None:
    seen: set[str] = set()
    for target in targets:
        if target.slot in seen:
            return target.slot
        seen.add(target.slot)
    return None


def _optional_string(value: dict[str, Any], key: str) -> str | None:
    raw = value.get(key)
    if not isinstance(raw, str):
        return None
    normalized = raw.strip()
    return normalized or None


def _config_error(slot: str, message: str) -> TableOutputTargetResolution:
    return TableOutputTargetResolution(
        TableOutputTargetResolutionStatus.ERROR,
        issue=TableOutputTargetIssue(
            slot=slot,
            message=message,
            details={"slot": slot},
        ),
    )
