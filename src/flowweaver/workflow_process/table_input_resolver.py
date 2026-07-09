from __future__ import annotations

from typing import Any

from flowweaver.engine.runtime_store import NodeRun, RuntimeStore
from flowweaver.protocols.table_ref import TableRefModel
from flowweaver.workflow_process.table_input_resolution_models import (
    TableInputResolution,
    TableInputResolutionIssue,
    TableInputResolutionStatus,
    TableInputSelector,
)
from flowweaver.workflow_process.table_input_selector_config import (
    INPUT_SOURCE_CONFIG_KEY as INPUT_SOURCE_CONFIG_KEY,
)
from flowweaver.workflow_process.table_input_selector_config import (
    INPUT_SOURCES_CONFIG_KEYS as INPUT_SOURCES_CONFIG_KEYS,
)
from flowweaver.workflow_process.table_input_selector_config import (
    selectors_from_config as _selectors_from_config,
)


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
