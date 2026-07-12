from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from flowweaver.nodes.builtin_table_execution_result import (
    BuiltinTableExecutionResult,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

if TYPE_CHECKING:
    from flowweaver.nodes.table_node_context import BuiltinTableNodeContext


class BuiltinTableNodeHandler(Protocol):
    node_type: str

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> BuiltinTableExecutionResult | list[TableRefModel]:
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
