from __future__ import annotations

from flowweaver.nodes.table_node_errors import BuiltinTableNodeValidationError
from flowweaver.nodes.table_node_output_target_models import (
    TableNodeOutputContext,
)
from flowweaver.protocols.table_ref import TableRefModel
from flowweaver.workflow_process.table_output_targets import TableOutputTarget


def find_latest_output_target_ref(
    context: TableNodeOutputContext,
    *,
    workflow_run_id: str,
    target: TableOutputTarget,
) -> TableRefModel | None:
    if target.logical_table_id is None or target.storage_kind is None:
        return None
    return context.registry.get_latest_by_logical_identity(
        workflow_run_id=workflow_run_id,
        storage_kind=target.storage_kind,
        role=target.role,
        logical_table_id=target.logical_table_id,
    )


def require_existing_output_target_ref(
    context: TableNodeOutputContext,
    *,
    workflow_run_id: str,
    target: TableOutputTarget,
) -> TableRefModel:
    if not target.is_existing_target:
        raise BuiltinTableNodeValidationError(
            "output target must be an existing target"
        )
    table_ref = find_latest_output_target_ref(
        context,
        workflow_run_id=workflow_run_id,
        target=target,
    )
    if table_ref is None:
        raise BuiltinTableNodeValidationError(
            f"output target does not exist: {target.logical_table_id}"
        )
    return table_ref
