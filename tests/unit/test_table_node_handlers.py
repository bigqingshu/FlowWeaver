from __future__ import annotations

import pytest

from flowweaver.nodes.builtin_sql import SQL_MAPPING_NODE_TYPE
from flowweaver.nodes.builtin_table import (
    ADD_COLUMNS_NODE_TYPE,
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
    SAVE_MEMORY_TABLE_NODE_TYPE,
    create_builtin_table_node_handler_registry,
    table_node_types,
)
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


def test_default_builtin_table_handler_registry_covers_table_node_types() -> None:
    expected_node_types = {
        GENERATE_TEST_TABLE_NODE_TYPE,
        FILTER_ROWS_NODE_TYPE,
        ADD_COLUMNS_NODE_TYPE,
        SAVE_MEMORY_TABLE_NODE_TYPE,
        SQL_MAPPING_NODE_TYPE,
    }

    registry = create_builtin_table_node_handler_registry()

    assert set(registry.node_types()) == expected_node_types
    assert set(table_node_types()) == expected_node_types
    for node_type in expected_node_types:
        assert registry.get(node_type) is not None
