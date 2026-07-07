from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.protocols.enums import TableRole, TableStorageKind
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

DEFAULT_ROW_BATCH_SIZE = 1000

if TYPE_CHECKING:
    from flowweaver.nodes.builtin_sql import SqlMappingNodeRunner


class BuiltinTableNodeValidationError(ValueError):
    pass


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

    def _reader_for(self, table_ref: TableRefModel):
        if table_ref.storage_kind == TableStorageKind.MEMORY:
            return self.memory_provider
        if table_ref.storage_kind == TableStorageKind.RUNTIME_SQL:
            return self.table_provider
        raise BuiltinTableNodeValidationError(
            f"Unsupported table storage kind: {table_ref.storage_kind.value}"
        )


class BuiltinTableNodeHandler(Protocol):
    node_type: str

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        ...


class BuiltinTableNodeHandlerRegistry:
    def __init__(
        self,
        handlers: Sequence[BuiltinTableNodeHandler] = (),
    ) -> None:
        self._handlers: dict[str, BuiltinTableNodeHandler] = {}
        for handler in handlers:
            self.register(handler)

    def register(self, handler: BuiltinTableNodeHandler) -> None:
        if handler.node_type in self._handlers:
            raise ValueError(
                f"Duplicate builtin table node handler: {handler.node_type}"
            )
        self._handlers[handler.node_type] = handler

    def get(self, node_type: str) -> BuiltinTableNodeHandler | None:
        return self._handlers.get(node_type)

    def node_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))
