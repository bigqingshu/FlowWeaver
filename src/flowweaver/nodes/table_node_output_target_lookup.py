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
    matches = [
        table_ref
        for table_ref in context.registry.list_by_workflow_run(workflow_run_id)
        if table_ref.logical_table_id == target.logical_table_id
        and table_ref.storage_kind == target.storage_kind
        and table_ref.role == target.role
    ]
    if not matches:
        return None
    return max(matches, key=lambda table_ref: table_ref.version)


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
