from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from flowweaver.nodes.table_node_errors import BuiltinTableNodeValidationError
from flowweaver.nodes.table_node_output_target_lookup import (
    find_latest_output_target_ref as find_latest_output_target_ref,
)
from flowweaver.nodes.table_node_output_target_lookup import (
    require_existing_output_target_ref as require_existing_output_target_ref,
)
from flowweaver.nodes.table_node_output_target_models import (
    TableNodeOutputContext as TableNodeOutputContext,
)
from flowweaver.nodes.table_node_output_target_models import (
    TableOutputWriteResult as TableOutputWriteResult,
)
from flowweaver.nodes.table_node_row_batch_counter import (
    RowBatchCounter as _RowBatchCounter,
)
from flowweaver.protocols.enums import TableStorageKind
from flowweaver.protocols.memory_table_warnings import (
    MemoryTableSoftLimitWarningModel,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow_process.table_output_targets import (
    TableOutputTarget,
    TableOutputTargetKind,
)


def publish_output_target_batches(
    context: TableNodeOutputContext,
    task: NodeTaskModel,
    *,
    target: TableOutputTarget,
    output_name: str,
    schema: Sequence[FieldSchemaModel],
    row_batches: Iterable[Sequence[dict[str, Any]]],
) -> TableOutputWriteResult:
    if target.is_existing_target:
        raise BuiltinTableNodeValidationError(
            "publish_output_target_batches does not accept existing targets"
        )
    if target.is_new_target:
        existing_ref = find_latest_output_target_ref(
            context,
            workflow_run_id=task.workflow_run_id,
            target=target,
        )
        if existing_ref is not None:
            raise BuiltinTableNodeValidationError(
                f"output target already exists: {target.logical_table_id}"
            )

    counter = _RowBatchCounter(row_batches)
    if target.target_kind == TableOutputTargetKind.CURRENT:
        table_ref = context.publish_row_batches(
            task,
            output_name=output_name,
            schema=schema,
            row_batches=counter,
            role=target.role,
        )
    elif target.target_kind == TableOutputTargetKind.NEW_MEMORY:
        logical_table_id = _required_target_table_name(target)
        table_ref = context.create_memory_table_from_batches(
            task,
            logical_table_id=logical_table_id,
            schema=schema,
            row_batches=counter,
            role=target.role,
        )
    elif target.target_kind == TableOutputTargetKind.NEW_RUNTIME_SQL:
        logical_table_id = _required_target_table_name(target)
        table_ref = context.publish_row_batches(
            task,
            output_name=logical_table_id,
            schema=schema,
            row_batches=counter,
            role=target.role,
        )
    else:
        raise BuiltinTableNodeValidationError(
            f"unsupported output target kind: {target.target_kind.value}"
        )
    return TableOutputWriteResult(
        slot=target.slot,
        target_kind=target.target_kind,
        table_ref=table_ref,
        write_mode="create",
        affected_rows=counter.row_count,
        memory_table_soft_limit_warning=_memory_table_soft_limit_warning(
            context,
            table_ref=table_ref,
            row_count=counter.row_count,
        ),
    )


def replace_output_target_batches(
    context: TableNodeOutputContext,
    task: NodeTaskModel,
    *,
    target: TableOutputTarget,
    schema: Sequence[FieldSchemaModel],
    row_batches: Iterable[Sequence[dict[str, Any]]],
) -> TableOutputWriteResult:
    target_ref = require_existing_output_target_ref(
        context,
        workflow_run_id=task.workflow_run_id,
        target=target,
    )
    counter = _RowBatchCounter(row_batches)
    if target.target_kind == TableOutputTargetKind.EXISTING_MEMORY:
        context.replace_memory_table_batches(target_ref, counter)
        table_ref = target_ref
    elif target.target_kind == TableOutputTargetKind.EXISTING_RUNTIME_SQL:
        table_ref = context.replace_runtime_table_batches(
            task,
            target_ref=target_ref,
            output_name=target_ref.logical_table_id,
            schema=schema,
            row_batches=counter,
        )
    else:
        raise BuiltinTableNodeValidationError(
            "replace_output_target_batches requires an existing target"
        )
    return TableOutputWriteResult(
        slot=target.slot,
        target_kind=target.target_kind,
        table_ref=table_ref,
        write_mode="overwrite",
        affected_rows=counter.row_count,
        target_existed=True,
        memory_table_soft_limit_warning=_memory_table_soft_limit_warning(
            context,
            table_ref=table_ref,
            row_count=counter.row_count,
        ),
    )


def _required_target_table_name(target: TableOutputTarget) -> str:
    if target.logical_table_id is None:
        raise BuiltinTableNodeValidationError(
            f"output target {target.slot} requires a table name"
        )
    return target.logical_table_id


def _memory_table_soft_limit_warning(
    context: TableNodeOutputContext,
    *,
    table_ref: TableRefModel,
    row_count: int,
) -> MemoryTableSoftLimitWarningModel | None:
    if table_ref.storage_kind != TableStorageKind.MEMORY:
        return None
    soft_row_limit = context.memory_table_limits.soft_row_limit
    if soft_row_limit == 0 or row_count <= soft_row_limit:
        return None
    return MemoryTableSoftLimitWarningModel(
        table_ref_id=table_ref.table_ref_id,
        logical_table_id=table_ref.logical_table_id,
        row_count=row_count,
        soft_row_limit=soft_row_limit,
    )
