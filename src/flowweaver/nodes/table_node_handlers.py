from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


@dataclass(frozen=True)
class BuiltinTableNodeContext:
    store: RuntimeStore
    registry: RuntimeDataRegistry
    table_provider: SQLiteRuntimeTableProvider
    memory_provider: MemoryTableProvider

    def input_ref(self, table_ref_id: str) -> TableRefModel:
        return self.registry.get(table_ref_id)

    def publish_rows(
        self,
        task: NodeTaskModel,
        *,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
    ) -> TableRefModel:
        staging_ref = self.table_provider.create_staging_table(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            output_name=output_name,
            schema=schema,
        )
        self.table_provider.insert_rows(staging_ref, rows)
        self.registry.register_staging(staging_ref)
        return self.registry.publish(staging_ref.table_ref_id)


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
