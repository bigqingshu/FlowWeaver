from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.nodes.table_node_errors import BuiltinTableNodeValidationError
from flowweaver.protocols.enums import TableRole
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow_process.table_output_targets import (
    TableOutputTarget,
    TableOutputTargetKind,
)


@dataclass(frozen=True)
class TableOutputWriteResult:
    slot: str
    target_kind: TableOutputTargetKind
    table_ref: TableRefModel
    write_mode: str
    affected_rows: int
    target_existed: bool = False

    def to_summary(self) -> dict[str, Any]:
        return {
            "output_slot": self.slot,
            "target_type": self.target_kind.value,
            "target_table": self.table_ref.logical_table_id,
            "target_table_ref_id": self.table_ref.table_ref_id,
            "storage_kind": self.table_ref.storage_kind.value,
            "role": self.table_ref.role.value,
            "write_mode": self.write_mode,
            "affected_rows": self.affected_rows,
            "target_existed": self.target_existed,
        }


class TableNodeOutputContext(Protocol):
    @property
    def registry(self) -> RuntimeDataRegistry:
        ...

    def publish_row_batches(
        self,
        task: NodeTaskModel,
        *,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
        role: TableRole = TableRole.CURRENT,
        version: int = 1,
    ) -> TableRefModel:
        ...

    def create_memory_table_from_batches(
        self,
        task: NodeTaskModel,
        *,
        logical_table_id: str,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
        role: TableRole = TableRole.AUXILIARY,
        version: int = 1,
    ) -> TableRefModel:
        ...

    def replace_memory_table_batches(
        self,
        table_ref: TableRefModel,
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> None:
        ...

    def replace_runtime_table_batches(
        self,
        task: NodeTaskModel,
        *,
        target_ref: TableRefModel,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> TableRefModel:
        ...


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
    )


class _RowBatchCounter:
    def __init__(self, row_batches: Iterable[Sequence[dict[str, Any]]]) -> None:
        self._row_batches = row_batches
        self.row_count = 0

    def __iter__(self):
        for rows in self._row_batches:
            self.row_count += len(rows)
            yield rows


def _required_target_table_name(target: TableOutputTarget) -> str:
    if target.logical_table_id is None:
        raise BuiltinTableNodeValidationError(
            f"output target {target.slot} requires a table name"
        )
    return target.logical_table_id
