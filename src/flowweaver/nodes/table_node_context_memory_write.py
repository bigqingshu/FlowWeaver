from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from flowweaver.protocols.enums import TableRole
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def create_memory_table(
    context: Any,
    task: NodeTaskModel,
    *,
    logical_table_id: str,
    schema: Sequence[FieldSchemaModel],
    rows: Sequence[dict[str, Any]],
    role: TableRole = TableRole.AUXILIARY,
    version: int = 1,
) -> TableRefModel:
    memory_ref = context.memory_provider.create_memory_table(
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        logical_table_id=logical_table_id,
        schema=schema,
        rows=rows,
        role=role,
        version=version,
    )
    context.store.register_table_ref(memory_ref)
    return memory_ref


def create_memory_table_from_batches(
    context: Any,
    task: NodeTaskModel,
    *,
    logical_table_id: str,
    schema: Sequence[FieldSchemaModel],
    row_batches: Iterable[Sequence[dict[str, Any]]],
    role: TableRole = TableRole.AUXILIARY,
    version: int = 1,
) -> TableRefModel:
    memory_ref = context.memory_provider.create_memory_table_from_batches(
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        logical_table_id=logical_table_id,
        schema=schema,
        row_batches=row_batches,
        role=role,
        version=version,
    )
    context.store.register_table_ref(memory_ref)
    return memory_ref


def replace_memory_table_rows(
    context: Any,
    table_ref: TableRefModel,
    rows: Sequence[dict[str, Any]],
) -> None:
    context.memory_provider.replace_rows(table_ref, rows)


def replace_memory_table_batches(
    context: Any,
    table_ref: TableRefModel,
    row_batches: Iterable[Sequence[dict[str, Any]]],
) -> None:
    context.memory_provider.replace_row_batches(table_ref, row_batches)
