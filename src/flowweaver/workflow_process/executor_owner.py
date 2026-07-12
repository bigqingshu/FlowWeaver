from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable

from flowweaver.common.config import MemoryTableLimits
from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.node_executor import (
    BuiltinSharedTableNodeExecutor,
    BuiltinTableNodeExecutor,
    NodeExecutor,
    SubprocessNodeExecutorIpcClient,
)
from flowweaver.nodes.builtin_shared_table import is_shared_table_node_type
from flowweaver.nodes.builtin_table import is_table_node_type
from flowweaver.protocols.node_task import NodeTaskModel


@runtime_checkable
class _ClosableExecutor(Protocol):
    def close(self) -> None:
        ...


class DefaultWorkflowProcessExecutorOwner:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        runtime_dir: Path,
        memory_table_limits: MemoryTableLimits,
        default_executor_factory: Callable[[], NodeExecutor] = (
            SubprocessNodeExecutorIpcClient
        ),
        shared_table_executor_factory: Callable[..., NodeExecutor] = (
            BuiltinSharedTableNodeExecutor
        ),
    ) -> None:
        self._store = store
        self._runtime_dir = runtime_dir
        self._memory_table_limits = memory_table_limits
        self._default_executor_factory = default_executor_factory
        self._shared_table_executor_factory = shared_table_executor_factory
        self._data_registry: RuntimeDataRegistry | None = None
        self._table_provider: SQLiteRuntimeTableProvider | None = None
        self._table_executor: BuiltinTableNodeExecutor | None = None
        self._executor: NodeExecutor | None = None

    def executor_for_task(
        self,
        task: NodeTaskModel,
    ) -> NodeExecutor:
        if is_table_node_type(task.node_type):
            return self._builtin_table_executor()
        if is_shared_table_node_type(task.node_type):
            return self._shared_table_executor_factory(store=self._store)
        if self._executor is None or getattr(self._executor, "closed", False):
            self._executor = self._default_executor_factory()
        return self._executor

    def _builtin_table_executor(self) -> BuiltinTableNodeExecutor:
        if self._table_provider is None:
            self._table_provider = SQLiteRuntimeTableProvider(self._runtime_dir)
        if self._data_registry is None:
            self._data_registry = RuntimeDataRegistry(
                store=self._store,
                table_provider=self._table_provider,
            )
        if self._table_executor is None:
            self._table_executor = BuiltinTableNodeExecutor(
                store=self._store,
                registry=self._data_registry,
                table_provider=self._table_provider,
                memory_provider=MemoryTableProvider(
                    limits=self._memory_table_limits,
                ),
            )
        return self._table_executor

    def close(self) -> None:
        if self._executor is None:
            return
        close_executor(self._executor)
        self._executor = None


def close_executor(executor: object) -> None:
    if not isinstance(executor, _ClosableExecutor):
        return
    try:
        executor.close()
    except Exception:
        pass
