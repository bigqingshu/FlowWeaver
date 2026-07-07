from __future__ import annotations

import pytest

from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeHandlerRegistry,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel


class _ExampleHandler:
    node_type = "ExampleNode"

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        return []


def test_builtin_table_node_handler_registry_lists_and_returns_handlers() -> None:
    handler = _ExampleHandler()
    registry = BuiltinTableNodeHandlerRegistry(handlers=(handler,))

    assert registry.node_types() == ("ExampleNode",)
    assert registry.get("ExampleNode") is handler
    assert registry.get("MissingNode") is None


def test_builtin_table_node_handler_registry_rejects_duplicate_handlers() -> None:
    registry = BuiltinTableNodeHandlerRegistry(handlers=(_ExampleHandler(),))

    with pytest.raises(ValueError, match="Duplicate builtin table node handler"):
        registry.register(_ExampleHandler())
