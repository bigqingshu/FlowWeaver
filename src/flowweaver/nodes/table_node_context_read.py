from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.table_node_errors import BuiltinTableNodeValidationError
from flowweaver.protocols.enums import TableStorageKind
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel


class TableNodeContextReadMixin:
    registry: RuntimeDataRegistry
    table_provider: SQLiteRuntimeTableProvider
    memory_provider: MemoryTableProvider
    row_batch_size: int

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

    def _reader_for(
        self,
        table_ref: TableRefModel,
    ) -> MemoryTableProvider | SQLiteRuntimeTableProvider:
        if table_ref.storage_kind == TableStorageKind.MEMORY:
            return self.memory_provider
        if table_ref.storage_kind == TableStorageKind.RUNTIME_SQL:
            return self.table_provider
        raise BuiltinTableNodeValidationError(
            f"Unsupported table storage kind: {table_ref.storage_kind.value}"
        )
