from __future__ import annotations

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.protocols.enums import LifecycleStatus, TableStorageKind
from flowweaver.protocols.table_ref import TableRefModel


def find_latest_writeback_target_ref(
    context: BuiltinTableNodeContext,
    *,
    workflow_run_id: str,
    target_type: str,
    target_table: str,
) -> TableRefModel | None:
    storage_kind = (
        TableStorageKind.MEMORY
        if target_type == "memory_table"
        else TableStorageKind.RUNTIME_SQL
    )
    candidates = [
        table_ref
        for table_ref in context.registry.list_by_workflow_run(workflow_run_id)
        if table_ref.logical_table_id == target_table
        and table_ref.storage_kind == storage_kind
        and table_ref.lifecycle_status in {
            LifecycleStatus.ACTIVE,
            LifecycleStatus.PUBLISHED,
        }
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda table_ref: table_ref.created_at)


def next_writeback_target_version(existing_ref: TableRefModel | None) -> int:
    if existing_ref is None:
        return 1
    return existing_ref.version + 1
