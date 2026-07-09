from __future__ import annotations

from typing import Any

from flowweaver.workflow_process.table_output_target_config import (
    config_error as _config_error,
)
from flowweaver.workflow_process.table_output_target_config import (
    first_duplicate_slot as _first_duplicate_slot,
)
from flowweaver.workflow_process.table_output_target_config import (
    optional_string as _optional_string,
)
from flowweaver.workflow_process.table_output_target_config import (
    target_from_output_save as _target_from_output_save,
)
from flowweaver.workflow_process.table_output_target_config import (
    target_from_value as _target_from_value,
)
from flowweaver.workflow_process.table_output_target_models import (
    OUTPUT_SAVE_CONFIG_KEY as OUTPUT_SAVE_CONFIG_KEY,
)
from flowweaver.workflow_process.table_output_target_models import (
    OUTPUT_TARGET_CONFIG_KEY as OUTPUT_TARGET_CONFIG_KEY,
)
from flowweaver.workflow_process.table_output_target_models import (
    OUTPUT_TARGETS_CONFIG_KEYS as OUTPUT_TARGETS_CONFIG_KEYS,
)
from flowweaver.workflow_process.table_output_target_models import (
    TableOutputTarget as TableOutputTarget,
)
from flowweaver.workflow_process.table_output_target_models import (
    TableOutputTargetIssue as TableOutputTargetIssue,
)
from flowweaver.workflow_process.table_output_target_models import (
    TableOutputTargetKind as TableOutputTargetKind,
)
from flowweaver.workflow_process.table_output_target_models import (
    TableOutputTargetResolution as TableOutputTargetResolution,
)
from flowweaver.workflow_process.table_output_target_models import (
    TableOutputTargetResolutionStatus as TableOutputTargetResolutionStatus,
)
from flowweaver.workflow_process.table_output_target_models import (
    default_current_output_target as default_current_output_target,
)


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
