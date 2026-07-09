from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from flowweaver.nodes.table_node_context_memory_write import (
    create_memory_table as _create_memory_table,
)
from flowweaver.nodes.table_node_context_memory_write import (
    create_memory_table_from_batches as _create_memory_table_from_batches,
)
from flowweaver.nodes.table_node_context_memory_write import (
    replace_memory_table_batches as _replace_memory_table_batches,
)
from flowweaver.nodes.table_node_context_memory_write import (
    replace_memory_table_rows as _replace_memory_table_rows,
)
from flowweaver.protocols.enums import TableRole
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


class TableNodeContextMemoryWriteMixin:
    def create_memory_table(
        self,
        task: NodeTaskModel,
        *,
        logical_table_id: str,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
        role: TableRole = TableRole.AUXILIARY,
        version: int = 1,
    ) -> TableRefModel:
        return _create_memory_table(
            self,
            task,
            logical_table_id=logical_table_id,
            schema=schema,
            rows=rows,
            role=role,
            version=version,
        )

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
        return _create_memory_table_from_batches(
            self,
            task,
            logical_table_id=logical_table_id,
            schema=schema,
            row_batches=row_batches,
            role=role,
            version=version,
        )

    def replace_memory_table_rows(
        self,
        table_ref: TableRefModel,
        rows: Sequence[dict[str, Any]],
    ) -> None:
        _replace_memory_table_rows(self, table_ref, rows)

    def replace_memory_table_batches(
        self,
        table_ref: TableRefModel,
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> None:
        _replace_memory_table_batches(self, table_ref, row_batches)
