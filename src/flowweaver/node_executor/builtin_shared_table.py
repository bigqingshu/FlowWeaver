from __future__ import annotations

from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.shared_table_reader import SharedTableReader
from flowweaver.nodes.builtin_shared_table import BuiltinSharedTableNodeRunner
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


class BuiltinSharedTableNodeExecutor:
    def __init__(
        self,
        *,
        executor_id: str = "builtin-shared-table-node-executor",
        store: RuntimeStore,
        reader: SharedTableReader | None = None,
    ) -> None:
        self.executor_id = executor_id
        self._runner = BuiltinSharedTableNodeRunner(store=store, reader=reader)

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        return self._runner.execute(task, executor_id=self.executor_id)
