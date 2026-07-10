from __future__ import annotations

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.protocols.enums import TableRole, TableStorageKind
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
    return context.registry.get_latest_by_logical_identity(
        workflow_run_id=workflow_run_id,
        storage_kind=storage_kind,
        role=TableRole.AUXILIARY,
        logical_table_id=target_table,
    )


def next_writeback_target_version(existing_ref: TableRefModel | None) -> int:
    if existing_ref is None:
        return 1
    return existing_ref.version + 1
