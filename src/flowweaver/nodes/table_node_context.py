from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from flowweaver.common.config import MemoryTableLimits
from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.table_node_context_read import TableNodeContextReadMixin
from flowweaver.nodes.table_node_context_write import TableNodeContextWriteMixin

DEFAULT_ROW_BATCH_SIZE = 1000

if TYPE_CHECKING:
    from flowweaver.nodes.builtin_sql import SqlMappingNodeRunner


@dataclass(frozen=True)
class BuiltinTableNodeContext(TableNodeContextReadMixin, TableNodeContextWriteMixin):
    store: RuntimeStore
    registry: RuntimeDataRegistry
    table_provider: SQLiteRuntimeTableProvider
    memory_provider: MemoryTableProvider
    sql_mapping_runner: SqlMappingNodeRunner | None = None
    row_batch_size: int = DEFAULT_ROW_BATCH_SIZE

    @property
    def memory_table_limits(self) -> MemoryTableLimits:
        return self.memory_provider.limits

