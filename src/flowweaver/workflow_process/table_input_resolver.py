from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.enums import TableRole, TableStorageKind
from flowweaver.protocols.table_ref import TableRefModel

INPUT_SOURCE_CONFIG_KEY = "input_source"
INPUT_SOURCES_CONFIG_KEYS = ("input_sources", "input_table_sources")


class TableInputResolutionStatus(str, Enum):
    NO_CONFIG = "NO_CONFIG"
    RESOLVED = "RESOLVED"
    WAITING = "WAITING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class TableInputSelector:
    slot: str
    source_node_instance_id: str
    output_role: TableRole | None = None
    storage_kind: TableStorageKind | None = None
    logical_table_id: str | None = None
    output_slot: str | None = None


@dataclass(frozen=True)
class TableInputResolutionIssue:
    slot: str
    message: str
    details: dict[str, Any]


@dataclass(frozen=True)
class TableInputResolution:
    status: TableInputResolutionStatus
    input_refs: tuple[str, ...] = ()
    input_slot_bindings: dict[str, str] | None = None
    issue: TableInputResolutionIssue | None = None


def resolve_configured_input_refs(
    *,
    store: RuntimeStore,
    config: dict[str, Any],
    upstream_node_runs: dict[str, NodeRun],
) -> TableInputResolution:
    selectors_result = _selectors_from_config(config)
    if isinstance(selectors_result, TableInputResolution):
        return selectors_result
    selectors = selectors_result
    if not selectors:
        return TableInputResolution(TableInputResolutionStatus.NO_CONFIG)

    input_refs: list[str] = []
    input_slot_bindings: dict[str, str] = {}
    for selector in selectors:
        source_node = upstream_node_runs.get(selector.source_node_instance_id)
        if source_node is None:
            return _error(
                selector.slot,
                "Input table source node is not a ready upstream dependency",
                selector=selector,
            )
        result = store.get_latest_succeeded_node_task_result_for_node_run(
            source_node.node_run_id
        )
        if result is None:
            return TableInputResolution(TableInputResolutionStatus.WAITING)

        matches = _matching_table_refs(
            store,
            output_refs=result.output_refs,
            selector=selector,
        )
        if not matches:
            return _error(
                selector.slot,
                "Input table selector did not match any upstream table",
                selector=selector,
            )
        if len(matches) > 1:
            return _error(
                selector.slot,
                "Input table selector matched multiple upstream tables",
                selector=selector,
                matched_table_ref_ids=[
                    table_ref.table_ref_id for table_ref in matches
                ],
            )
        input_refs.append(matches[0].table_ref_id)
        input_slot_bindings[selector.slot] = matches[0].table_ref_id

    return TableInputResolution(
        TableInputResolutionStatus.RESOLVED,
        input_refs=tuple(input_refs),
        input_slot_bindings=input_slot_bindings,
    )


def _selectors_from_config(
    config: dict[str, Any],
) -> tuple[TableInputSelector, ...] | TableInputResolution:
    selectors: list[TableInputSelector] = []

    single_source = config.get(INPUT_SOURCE_CONFIG_KEY)
    if isinstance(single_source, dict):
        selector = _selector_from_value("in", single_source)
        if isinstance(selector, TableInputResolution):
            return selector
        if selector is not None:
            selectors.append(selector)

    for key in INPUT_SOURCES_CONFIG_KEYS:
        sources = config.get(key)
        if isinstance(sources, dict):
            for slot, source in sources.items():
                if not isinstance(slot, str) or not slot.strip():
                    return _config_error(
                        "",
                        f"{key} contains an empty input slot name",
                    )
                selector = _selector_from_value(slot.strip(), source)
                if isinstance(selector, TableInputResolution):
                    return selector
                if selector is not None:
                    selectors.append(selector)
        elif isinstance(sources, list):
            for index, source in enumerate(sources):
                if not isinstance(source, dict):
                    return _config_error(
                        "",
                        f"{key}[{index}] must be an object",
                    )
                slot = _optional_string(source, "slot") or _optional_string(
                    source,
                    "input_slot",
                )
                if slot is None:
                    return _config_error(
                        "",
                        f"{key}[{index}] must include slot",
                    )
                selector = _selector_from_value(slot, source)
                if isinstance(selector, TableInputResolution):
                    return selector
                if selector is not None:
                    selectors.append(selector)

    seen_slots: set[str] = set()
    for selector in selectors:
        if selector.slot in seen_slots:
            return _config_error(selector.slot, f"duplicate input slot: {selector.slot}")
        seen_slots.add(selector.slot)

    return tuple(selectors)


def _selector_from_value(
    slot: str,
    value: Any,
) -> TableInputSelector | TableInputResolution | None:
    if not isinstance(value, dict):
        return _config_error(slot, "input source must be an object")
    source_type = _optional_string(value, "type") or (
        "upstream_table"
        if _optional_string(value, "source_node_instance_id") is not None
        else "current"
    )
    if source_type in {"current", "current_table"}:
        return None
    if source_type not in {"upstream_table", "upstream"}:
        return _config_error(slot, f"unsupported input source type: {source_type}")

    source_node_instance_id = _optional_string(value, "source_node_instance_id")
    if source_node_instance_id is None:
        return _config_error(
            slot,
            "upstream input source requires source_node_instance_id",
        )
    output_role = _optional_table_role(value, slot=slot)
    if isinstance(output_role, TableInputResolution):
        return output_role
    storage_kind = _optional_storage_kind(value, slot=slot)
    if isinstance(storage_kind, TableInputResolution):
        return storage_kind

    return TableInputSelector(
        slot=slot,
        source_node_instance_id=source_node_instance_id,
        output_role=output_role,
        storage_kind=storage_kind,
        logical_table_id=_optional_string(value, "logical_table_id"),
        output_slot=(
            _optional_string(value, "output_slot")
            or _optional_string(value, "output_alias")
        ),
    )


def _matching_table_refs(
    store: RuntimeStore,
    *,
    output_refs: list[str],
    selector: TableInputSelector,
) -> list[TableRefModel]:
    matches: list[TableRefModel] = []
    for output_ref in output_refs:
        table_ref = store.get_table_ref(output_ref)
        if table_ref is None:
            continue
        if "READ" not in table_ref.capabilities:
            continue
        if (
            selector.output_role is not None
            and table_ref.role != selector.output_role
        ):
            continue
        if (
            selector.storage_kind is not None
            and table_ref.storage_kind != selector.storage_kind
        ):
            continue
        if (
            selector.logical_table_id is not None
            and table_ref.logical_table_id != selector.logical_table_id
        ):
            continue
        if selector.output_slot is not None and not _matches_output_slot(
            table_ref,
            selector.output_slot,
        ):
            continue
        matches.append(table_ref)
    return matches


def _matches_output_slot(table_ref: TableRefModel, output_slot: str) -> bool:
    handle_slot = table_ref.opaque_handle.get("output_slot")
    if isinstance(handle_slot, str) and handle_slot:
        return handle_slot == output_slot
    handle_output_name = table_ref.opaque_handle.get("output_name")
    if isinstance(handle_output_name, str) and handle_output_name:
        return handle_output_name == output_slot
    return table_ref.logical_table_id == output_slot


def _optional_table_role(
    value: dict[str, Any],
    *,
    slot: str,
) -> TableRole | TableInputResolution | None:
    raw = _optional_string(value, "output_role")
    if raw is None:
        return None
    try:
        return TableRole(raw)
    except ValueError:
        return _config_error(slot, f"unsupported output_role: {raw}")


def _optional_storage_kind(
    value: dict[str, Any],
    *,
    slot: str,
) -> TableStorageKind | TableInputResolution | None:
    raw = _optional_string(value, "storage_kind")
    if raw is None:
        return None
    try:
        return TableStorageKind(raw)
    except ValueError:
        return _config_error(slot, f"unsupported storage_kind: {raw}")


def _optional_string(value: dict[str, Any], key: str) -> str | None:
    raw = value.get(key)
    if not isinstance(raw, str):
        return None
    normalized = raw.strip()
    return normalized or None


def _config_error(slot: str, message: str) -> TableInputResolution:
    return TableInputResolution(
        TableInputResolutionStatus.ERROR,
        issue=TableInputResolutionIssue(
            slot=slot,
            message=message,
            details={"slot": slot},
        ),
    )


def _error(
    slot: str,
    message: str,
    *,
    selector: TableInputSelector,
    **details: Any,
) -> TableInputResolution:
    payload = {
        "slot": selector.slot,
        "source_node_instance_id": selector.source_node_instance_id,
        "output_role": (
            selector.output_role.value if selector.output_role is not None else None
        ),
        "storage_kind": (
            selector.storage_kind.value if selector.storage_kind is not None else None
        ),
        "logical_table_id": selector.logical_table_id,
        "output_slot": selector.output_slot,
    }
    payload.update(details)
    return TableInputResolution(
        TableInputResolutionStatus.ERROR,
        issue=TableInputResolutionIssue(
            slot=slot,
            message=message,
            details=payload,
        ),
    )
