from __future__ import annotations

from typing import Any

from flowweaver.protocols.enums import TableRole, TableStorageKind
from flowweaver.workflow_process.table_output_target_models import (
    TableOutputTarget,
    TableOutputTargetIssue,
    TableOutputTargetKind,
    TableOutputTargetResolution,
    TableOutputTargetResolutionStatus,
    default_current_output_target,
)


def target_from_output_save(
    value: dict[str, Any],
) -> TableOutputTarget | TableOutputTargetResolution:
    target_type = optional_string(value, "target_type")
    if target_type in {"memory", "memory_table", "new_memory"}:
        target_kind = TableOutputTargetKind.NEW_MEMORY
    elif target_type in {"runtime_sql", "run_table", "new_runtime_sql"}:
        target_kind = TableOutputTargetKind.NEW_RUNTIME_SQL
    else:
        return config_error(
            "saved_table",
            f"unsupported output_save target_type: {target_type}",
        )
    return named_target_from_kind(
        slot=optional_string(value, "slot") or "saved_table",
        value=value,
        target_kind=target_kind,
    )


def target_from_value(
    slot: str,
    value: Any,
) -> TableOutputTarget | TableOutputTargetResolution | None:
    if not isinstance(value, dict):
        return config_error(slot, "output target must be an object")
    raw_target_kind = optional_string(value, "target_kind") or optional_string(
        value,
        "target_type",
    )
    if raw_target_kind is None:
        return None
    target_kind = normalize_target_kind(raw_target_kind)
    if target_kind is None:
        return config_error(slot, f"unsupported output target kind: {raw_target_kind}")
    if target_kind == TableOutputTargetKind.CURRENT:
        if target_logical_table_id(value) is not None:
            return config_error(slot, "current output target must not be named")
        return default_current_output_target(slot)
    return named_target_from_kind(
        slot=slot,
        value=value,
        target_kind=target_kind,
    )


def named_target_from_kind(
    *,
    slot: str,
    value: dict[str, Any],
    target_kind: TableOutputTargetKind,
) -> TableOutputTarget | TableOutputTargetResolution:
    logical_table_id = target_logical_table_id(value)
    if logical_table_id is None:
        return config_error(slot, f"{target_kind.value} requires table_name")
    storage_kind = storage_kind_for_target(target_kind)
    return TableOutputTarget(
        slot=slot,
        target_kind=target_kind,
        role=TableRole.AUXILIARY,
        storage_kind=storage_kind,
        logical_table_id=logical_table_id,
    )


def normalize_target_kind(value: str) -> TableOutputTargetKind | None:
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


def storage_kind_for_target(
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


def target_logical_table_id(value: dict[str, Any]) -> str | None:
    return (
        optional_string(value, "logical_table_id")
        or optional_string(value, "table_name")
        or optional_string(value, "target_table")
    )


def first_duplicate_slot(targets: list[TableOutputTarget]) -> str | None:
    seen: set[str] = set()
    for target in targets:
        if target.slot in seen:
            return target.slot
        seen.add(target.slot)
    return None


def optional_string(value: dict[str, Any], key: str) -> str | None:
    raw = value.get(key)
    if not isinstance(raw, str):
        return None
    normalized = raw.strip()
    return normalized or None


def config_error(slot: str, message: str) -> TableOutputTargetResolution:
    return TableOutputTargetResolution(
        TableOutputTargetResolutionStatus.ERROR,
        issue=TableOutputTargetIssue(
            slot=slot,
            message=message,
            details={"slot": slot},
        ),
    )
