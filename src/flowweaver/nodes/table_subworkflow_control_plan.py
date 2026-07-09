from __future__ import annotations

from typing import Any

from flowweaver.protocols.table_ref import TableRefModel


def subworkflow_input_summaries(
    input_refs: list[TableRefModel],
) -> list[dict[str, Any]]:
    return [
        {
            "table_ref_id": input_ref.table_ref_id,
            "logical_table_id": input_ref.logical_table_id,
            "role": input_ref.role.value,
            "storage_kind": input_ref.storage_kind.value,
            "field_count": len(input_ref.schema),
        }
        for input_ref in input_refs
    ]


def subworkflow_plan_details(
    *,
    group_name: str,
    subworkflow_ref: str,
    node_count: int,
    input_source_type: str,
    input_refs: list[TableRefModel],
    input_mapping: list[dict[str, Any]],
    input_defaults: dict[str, Any],
    missing_input_policy: str,
    transit_scope: str,
    allow_loop_nodes: bool,
    main_output_mode: str,
    save_to_transit: bool,
    output_transit_name: str,
) -> dict[str, Any]:
    return {
        "group_name": group_name,
        "subworkflow_ref": subworkflow_ref,
        "node_count": node_count,
        "input_source_type": input_source_type,
        "input_ref_count": len(input_refs),
        "input_refs": subworkflow_input_summaries(input_refs),
        "input_mapping": input_mapping,
        "input_defaults": input_defaults,
        "missing_input_policy": missing_input_policy,
        "transit_scope": transit_scope,
        "allow_loop_nodes": allow_loop_nodes,
        "main_output_mode": main_output_mode,
        "save_to_transit": save_to_transit,
        "output_transit_name": output_transit_name,
    }
