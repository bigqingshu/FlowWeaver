from __future__ import annotations

from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.engine.table_ref_release import (
    TableRefReleaseOutcome,
    TableRefReleaseService,
)
from flowweaver.protocols.table_ref import TableRefModel


def cleanup_table_refs_for_run(
    *,
    workflow_run_id: str,
    store: RuntimeStore,
    provider_registry: TableProviderRegistry,
) -> dict[str, object]:
    cleaned: list[TableRefModel] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    release_service = TableRefReleaseService(
        store=store,
        provider_registry=provider_registry,
    )
    for table_ref in store.list_table_refs_by_workflow_run(workflow_run_id):
        result = release_service.release(table_ref.table_ref_id)
        if result.outcome == TableRefReleaseOutcome.SKIPPED:
            skipped.append(
                {
                    "table_ref_id": table_ref.table_ref_id,
                    "reason": result.reason or "release_skipped",
                }
            )
            continue
        if result.outcome == TableRefReleaseOutcome.FAILED:
            failed.append(
                {
                    "table_ref_id": table_ref.table_ref_id,
                    "reason": result.reason or "release_failed",
                }
            )
            continue
        if result.table_ref is not None:
            cleaned.append(result.table_ref)
    return {
        "workflow_run_id": workflow_run_id,
        "cleaned_count": len(cleaned),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "cleaned_table_refs": cleaned,
        "skipped": skipped,
        "failed": failed,
    }
