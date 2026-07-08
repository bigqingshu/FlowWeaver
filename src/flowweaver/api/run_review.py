from __future__ import annotations

from flowweaver.engine.runtime_models import WorkflowRun
from flowweaver.protocols.enums import LifecycleStatus
from flowweaver.protocols.table_ref import TableRefModel


def build_run_review_payload(
    *,
    run: WorkflowRun,
    node_runs: list,
    table_refs: list[TableRefModel],
) -> dict[str, object]:
    readable_refs = [
        table_ref
        for table_ref in table_refs
        if table_ref_is_readable(table_ref)
    ]
    return {
        "run": run,
        "node_runs": node_runs,
        "table_refs": table_refs,
        "table_ref_summary": {
            "total": len(table_refs),
            "readable": len(readable_refs),
            "by_storage_kind": table_ref_counts_by_storage_kind(table_refs),
            "by_lifecycle_status": table_ref_counts_by_lifecycle_status(table_refs),
        },
        "data_preview": {
            "uses_paged_rows": True,
            "row_data_embedded": False,
            "readable_table_ref_ids": [
                table_ref.table_ref_id for table_ref in readable_refs
            ],
        },
    }


def table_ref_is_readable(table_ref: TableRefModel) -> bool:
    if "READ" not in table_ref.capabilities:
        return False
    return table_ref.lifecycle_status not in {
        LifecycleStatus.RELEASED,
        LifecycleStatus.RETIRED,
        LifecycleStatus.ORPHANED,
    }


def table_ref_counts_by_storage_kind(
    table_refs: list[TableRefModel],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table_ref in table_refs:
        key = table_ref.storage_kind.value
        counts[key] = counts.get(key, 0) + 1
    return counts


def table_ref_counts_by_lifecycle_status(
    table_refs: list[TableRefModel],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table_ref in table_refs:
        key = table_ref.lifecycle_status.value
        counts[key] = counts.get(key, 0) + 1
    return counts
