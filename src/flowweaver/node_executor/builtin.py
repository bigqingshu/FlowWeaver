from __future__ import annotations

from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.builtin_table import BuiltinTableNodeRunner
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


class BuiltinTableNodeExecutor:
    def __init__(
        self,
        *,
        executor_id: str = "builtin-table-node-executor",
        store: RuntimeStore,
        registry: RuntimeDataRegistry,
        table_provider: SQLiteRuntimeTableProvider,
    ) -> None:
        self.executor_id = executor_id
        self._runner = BuiltinTableNodeRunner(
            store=store,
            registry=registry,
            table_provider=table_provider,
        )

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        return self._runner.execute(task, executor_id=self.executor_id)
