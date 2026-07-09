from __future__ import annotations

from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.table_node_context_memory_write_mixin import (
    TableNodeContextMemoryWriteMixin,
)
from flowweaver.nodes.table_node_context_output_target_write_mixin import (
    TableNodeContextOutputTargetWriteMixin,
)
from flowweaver.nodes.table_node_context_runtime_write_mixin import (
    TableNodeContextRuntimeWriteMixin,
)


class TableNodeContextWriteMixin(
    TableNodeContextRuntimeWriteMixin,
    TableNodeContextMemoryWriteMixin,
    TableNodeContextOutputTargetWriteMixin,
):
    store: RuntimeStore
    registry: RuntimeDataRegistry
    table_provider: SQLiteRuntimeTableProvider
    memory_provider: MemoryTableProvider
