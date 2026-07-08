from __future__ import annotations

from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.protocols.enums import LifecycleStatus, TableStorageKind
from flowweaver.protocols.table_ref import TableRefModel

_INTERNAL_CLEANUP_STORAGE_KINDS = {
    TableStorageKind.RUNTIME_SQL,
    TableStorageKind.MEMORY,
}


def cleanup_table_refs_for_run(
    *,
    workflow_run_id: str,
    store: RuntimeStore,
    provider_registry: TableProviderRegistry,
) -> dict[str, object]:
    cleaned: list[TableRefModel] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    for table_ref in store.list_table_refs_by_workflow_run(workflow_run_id):
        skip_reason = table_cleanup_skip_reason(table_ref)
        if skip_reason is not None:
            skipped.append(
                {
                    "table_ref_id": table_ref.table_ref_id,
                    "reason": skip_reason,
                }
            )
            continue
        provider = provider_registry.get(table_ref.provider_id)
        if provider is None or not provider_registry.supports_storage_kind(
            table_ref.provider_id,
            table_ref.storage_kind,
        ):
            skipped.append(
                {
                    "table_ref_id": table_ref.table_ref_id,
                    "reason": "provider_unsupported",
                }
            )
            continue
        try:
            provider.drop_table(table_ref)
        except ValueError as exc:
            failed.append(
                {
                    "table_ref_id": table_ref.table_ref_id,
                    "reason": str(exc),
                }
            )
            continue
        released = store.mark_table_ref_released(table_ref.table_ref_id)
        if released is None:
            skipped.append(
                {
                    "table_ref_id": table_ref.table_ref_id,
                    "reason": "already_unavailable",
                }
            )
            continue
        cleaned.append(released)
    return {
        "workflow_run_id": workflow_run_id,
        "cleaned_count": len(cleaned),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "cleaned_table_refs": cleaned,
        "skipped": skipped,
        "failed": failed,
    }


def table_cleanup_skip_reason(table_ref: TableRefModel) -> str | None:
    if table_ref.storage_kind not in _INTERNAL_CLEANUP_STORAGE_KINDS:
        return "external_or_unsupported_storage"
    if table_ref.lifecycle_status in {
        LifecycleStatus.RELEASED,
        LifecycleStatus.RETIRED,
        LifecycleStatus.ORPHANED,
    }:
        return "already_unavailable"
    return None
