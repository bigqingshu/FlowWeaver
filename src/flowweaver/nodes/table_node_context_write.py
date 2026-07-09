from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.table_node_context_runtime_write import (
    publish_runtime_row_batches as _publish_runtime_row_batches,
)
from flowweaver.nodes.table_node_context_runtime_write import (
    replace_runtime_table_batches as _replace_runtime_table_batches,
)
from flowweaver.nodes.table_node_output_targets import (
    TableOutputWriteResult,
)
from flowweaver.nodes.table_node_output_targets import (
    find_latest_output_target_ref as _find_latest_output_target_ref,
)
from flowweaver.nodes.table_node_output_targets import (
    publish_output_target_batches as _publish_output_target_batches,
)
from flowweaver.nodes.table_node_output_targets import (
    replace_output_target_batches as _replace_output_target_batches,
)
from flowweaver.nodes.table_node_output_targets import (
    require_existing_output_target_ref as _require_existing_output_target_ref,
)
from flowweaver.protocols.enums import TableRole
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow_process.table_output_targets import (
    TableOutputTarget,
)


class TableNodeContextWriteMixin:
    store: RuntimeStore
    registry: RuntimeDataRegistry
    table_provider: SQLiteRuntimeTableProvider
    memory_provider: MemoryTableProvider

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
        memory_ref = self.memory_provider.create_memory_table(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            logical_table_id=logical_table_id,
            schema=schema,
            rows=rows,
            role=role,
            version=version,
        )
        self.store.register_table_ref(memory_ref)
        return memory_ref

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
        memory_ref = self.memory_provider.create_memory_table_from_batches(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            logical_table_id=logical_table_id,
            schema=schema,
            row_batches=row_batches,
            role=role,
            version=version,
        )
        self.store.register_table_ref(memory_ref)
        return memory_ref

    def replace_memory_table_rows(
        self,
        table_ref: TableRefModel,
        rows: Sequence[dict[str, Any]],
    ) -> None:
        self.memory_provider.replace_rows(table_ref, rows)

    def replace_memory_table_batches(
        self,
        table_ref: TableRefModel,
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> None:
        self.memory_provider.replace_row_batches(table_ref, row_batches)

    def find_latest_output_target_ref(
        self,
        *,
        workflow_run_id: str,
        target: TableOutputTarget,
    ) -> TableRefModel | None:
        return _find_latest_output_target_ref(
            self,
            workflow_run_id=workflow_run_id,
            target=target,
        )

    def require_existing_output_target_ref(
        self,
        *,
        workflow_run_id: str,
        target: TableOutputTarget,
    ) -> TableRefModel:
        return _require_existing_output_target_ref(
            self,
            workflow_run_id=workflow_run_id,
            target=target,
        )

    def publish_output_target_rows(
        self,
        task: NodeTaskModel,
        *,
        target: TableOutputTarget,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
    ) -> TableOutputWriteResult:
        return self.publish_output_target_batches(
            task,
            target=target,
            output_name=output_name,
            schema=schema,
            row_batches=(rows,),
        )

    def publish_output_target_batches(
        self,
        task: NodeTaskModel,
        *,
        target: TableOutputTarget,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> TableOutputWriteResult:
        return _publish_output_target_batches(
            self,
            task,
            target=target,
            output_name=output_name,
            schema=schema,
            row_batches=row_batches,
        )

    def replace_output_target_rows(
        self,
        task: NodeTaskModel,
        *,
        target: TableOutputTarget,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
    ) -> TableOutputWriteResult:
        return self.replace_output_target_batches(
            task,
            target=target,
            schema=schema,
            row_batches=(rows,),
        )

    def replace_output_target_batches(
        self,
        task: NodeTaskModel,
        *,
        target: TableOutputTarget,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> TableOutputWriteResult:
        return _replace_output_target_batches(
            self,
            task,
            target=target,
            schema=schema,
            row_batches=row_batches,
        )
