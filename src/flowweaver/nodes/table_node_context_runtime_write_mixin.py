from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from flowweaver.nodes.table_node_context_runtime_write import (
    publish_runtime_row_batches as _publish_runtime_row_batches,
)
from flowweaver.nodes.table_node_context_runtime_write import (
    replace_runtime_table_batches as _replace_runtime_table_batches,
)
from flowweaver.protocols.enums import TableRole
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


class TableNodeContextRuntimeWriteMixin:
    def publish_rows(
        self,
        task: NodeTaskModel,
        *,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
        role: TableRole = TableRole.CURRENT,
        version: int = 1,
    ) -> TableRefModel:
        return self.publish_row_batches(
            task,
            output_name=output_name,
            schema=schema,
            row_batches=(rows,),
            role=role,
            version=version,
        )

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
        return _publish_runtime_row_batches(
            self,
            task,
            output_name=output_name,
            schema=schema,
            row_batches=row_batches,
            role=role,
            version=version,
        )

    def replace_runtime_table_rows(
        self,
        task: NodeTaskModel,
        *,
        target_ref: TableRefModel,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
    ) -> TableRefModel:
        return self.replace_runtime_table_batches(
            task,
            target_ref=target_ref,
            output_name=output_name,
            schema=schema,
            row_batches=(rows,),
        )

    def replace_runtime_table_batches(
        self,
        task: NodeTaskModel,
        *,
        target_ref: TableRefModel,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> TableRefModel:
        return _replace_runtime_table_batches(
            self,
            task,
            target_ref=target_ref,
            output_name=output_name,
            schema=schema,
            row_batches=row_batches,
        )
