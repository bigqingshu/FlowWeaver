from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.table_node_errors import BuiltinTableNodeValidationError
from flowweaver.nodes.table_node_handler_registry import (
    BuiltinTableNodeHandler as BuiltinTableNodeHandler,
)
from flowweaver.nodes.table_node_handler_registry import (
    BuiltinTableNodeHandlerRegistry as BuiltinTableNodeHandlerRegistry,
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
from flowweaver.protocols.enums import TableRole, TableStorageKind
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow_process.table_output_targets import (
    TableOutputTarget,
)

DEFAULT_ROW_BATCH_SIZE = 1000

if TYPE_CHECKING:
    from flowweaver.nodes.builtin_sql import SqlMappingNodeRunner


@dataclass(frozen=True)
class BuiltinTableNodeContext:
    store: RuntimeStore
    registry: RuntimeDataRegistry
    table_provider: SQLiteRuntimeTableProvider
    memory_provider: MemoryTableProvider
    sql_mapping_runner: SqlMappingNodeRunner | None = None
    row_batch_size: int = DEFAULT_ROW_BATCH_SIZE

    def input_ref(self, table_ref_id: str) -> TableRefModel:
        return self.registry.get(table_ref_id)

    def require_single_input_ref(
        self,
        task: NodeTaskModel,
        *,
        node_type: str,
    ) -> TableRefModel:
        if len(task.input_refs) != 1:
            raise BuiltinTableNodeValidationError(
                f"{node_type} requires exactly one input_ref"
            )
        return self.input_ref(task.input_refs[0])

    def require_input_slot(
        self,
        task: NodeTaskModel,
        slot: str,
        *,
        node_type: str,
        allowed_storage_kinds: Sequence[TableStorageKind] | None = None,
    ) -> TableRefModel:
        table_ref_id = task.input_slot_bindings.get(slot)
        if table_ref_id is None:
            raise BuiltinTableNodeValidationError(
                f"{node_type} requires input slot: {slot}"
            )
        table_ref = self.input_ref(table_ref_id)
        if (
            allowed_storage_kinds is not None
            and table_ref.storage_kind not in allowed_storage_kinds
        ):
            allowed = ", ".join(kind.value for kind in allowed_storage_kinds)
            raise BuiltinTableNodeValidationError(
                f"{node_type} input slot {slot} requires storage kind: "
                f"{allowed}; got {table_ref.storage_kind.value}"
            )
        return table_ref

    def iter_slot_batches(
        self,
        task: NodeTaskModel,
        slot: str,
        *,
        node_type: str,
        allowed_storage_kinds: Sequence[TableStorageKind] | None = None,
        batch_size: int | None = None,
    ) -> Iterable[list[dict[str, Any]]]:
        table_ref = self.require_input_slot(
            task,
            slot,
            node_type=node_type,
            allowed_storage_kinds=allowed_storage_kinds,
        )
        return self.iter_row_batches(table_ref, batch_size=batch_size)

    def read_all_rows(self, table_ref: TableRefModel) -> list[dict[str, Any]]:
        provider = self._reader_for(table_ref)
        return provider.read_rows(
            table_ref,
            offset=0,
            limit=provider.count_rows(table_ref),
        )

    def count_rows(self, table_ref: TableRefModel) -> int:
        return self._reader_for(table_ref).count_rows(table_ref)

    def iter_row_batches(
        self,
        table_ref: TableRefModel,
        *,
        batch_size: int | None = None,
    ) -> Iterable[list[dict[str, Any]]]:
        limit = self.row_batch_size if batch_size is None else batch_size
        if limit <= 0:
            raise BuiltinTableNodeValidationError("row batch size must be positive")
        provider = self._reader_for(table_ref)
        total_rows = provider.count_rows(table_ref)
        offset = 0
        while offset < total_rows:
            rows = provider.read_rows(
                table_ref,
                offset=offset,
                limit=limit,
            )
            if not rows:
                break
            yield rows
            offset += len(rows)

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
        staging_ref = self.table_provider.create_staging_table(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            output_name=output_name,
            schema=schema,
            role=role,
            version=version,
        )
        for rows in row_batches:
            self.table_provider.insert_rows(staging_ref, rows)
        self.registry.register_staging(staging_ref)
        return self.registry.publish(staging_ref.table_ref_id)

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
        if target_ref.storage_kind != TableStorageKind.RUNTIME_SQL:
            raise BuiltinTableNodeValidationError(
                "replace_runtime_table_batches requires a RUNTIME_SQL target"
            )
        staging_output_name = f"{output_name}__replace_{target_ref.table_ref_id}"
        staging_ref = self.table_provider.create_staging_table(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            output_name=staging_output_name,
            schema=schema,
            role=target_ref.role,
            version=target_ref.version,
        )
        try:
            for rows in row_batches:
                self.table_provider.insert_rows(staging_ref, rows)
            self.table_provider.publish_staging(staging_ref, target_ref)
        finally:
            with suppress(Exception):
                self.table_provider.drop_table(staging_ref)
        return target_ref

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

    def _reader_for(self, table_ref: TableRefModel):
        if table_ref.storage_kind == TableStorageKind.MEMORY:
            return self.memory_provider
        if table_ref.storage_kind == TableStorageKind.RUNTIME_SQL:
            return self.table_provider
        raise BuiltinTableNodeValidationError(
            f"Unsupported table storage kind: {table_ref.storage_kind.value}"
        )
