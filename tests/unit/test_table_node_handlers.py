from __future__ import annotations

import pytest

from flowweaver.common.time import utc_now
from flowweaver.nodes.builtin_sql import SQL_MAPPING_NODE_TYPE
from flowweaver.nodes.builtin_table import (
    ADD_COLUMNS_NODE_TYPE,
    COPY_COLUMN_NODE_TYPE,
    DELETE_COLUMNS_NODE_TYPE,
    FILL_CELLS_NODE_TYPE,
    FILL_RANGE_NODE_TYPE,
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
    REORDER_COLUMNS_NODE_TYPE,
    REPLACE_TEXT_NODE_TYPE,
    SAVE_MEMORY_TABLE_NODE_TYPE,
    create_builtin_table_node_handler_registry,
    table_node_types,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeHandlerRegistry,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


class _ExampleHandler:
    node_type = "ExampleNode"

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        return []


class _BatchTableProvider:
    provider_id = "fake"

    def __init__(self, rows: list[dict[str, int]]) -> None:
        self._rows = rows

    def count_rows(self, table_ref: TableRefModel) -> int:
        return len(self._rows)

    def read_rows(
        self,
        table_ref: TableRefModel,
        offset: int,
        limit: int,
    ) -> list[dict[str, int]]:
        return self._rows[offset:offset + limit]


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
        DELETE_COLUMNS_NODE_TYPE,
        COPY_COLUMN_NODE_TYPE,
        REORDER_COLUMNS_NODE_TYPE,
        FILL_CELLS_NODE_TYPE,
        FILL_RANGE_NODE_TYPE,
        REPLACE_TEXT_NODE_TYPE,
        SAVE_MEMORY_TABLE_NODE_TYPE,
        SQL_MAPPING_NODE_TYPE,
    }

    registry = create_builtin_table_node_handler_registry()

    assert set(registry.node_types()) == expected_node_types
    assert set(table_node_types()) == expected_node_types
    for node_type in expected_node_types:
        assert registry.get(node_type) is not None


def test_builtin_table_node_context_iterates_row_batches() -> None:
    context = BuiltinTableNodeContext(
        store=object(),
        registry=object(),
        table_provider=_BatchTableProvider(
            rows=[
                {"value": 1},
                {"value": 2},
                {"value": 3},
                {"value": 4},
                {"value": 5},
            ]
        ),
        memory_provider=object(),
        row_batch_size=2,
    )

    assert list(context.iter_row_batches(_table_ref())) == [
        [{"value": 1}, {"value": 2}],
        [{"value": 3}, {"value": 4}],
        [{"value": 5}],
    ]


def test_builtin_table_node_context_rejects_invalid_batch_size() -> None:
    context = BuiltinTableNodeContext(
        store=object(),
        registry=object(),
        table_provider=_BatchTableProvider(rows=[]),
        memory_provider=object(),
    )

    with pytest.raises(BuiltinTableNodeValidationError):
        list(context.iter_row_batches(_table_ref(), batch_size=0))


def _table_ref() -> TableRefModel:
    return TableRefModel(
        table_ref_id="table-ref-1",
        role=TableRole.CURRENT,
        storage_kind=TableStorageKind.RUNTIME_SQL,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.PUBLISHED_IMMUTABLE,
        provider_id="fake",
        logical_table_id="table",
        opaque_handle={},
        schema=[
            FieldSchemaModel(
                field_id="value",
                name="value",
                data_type="INTEGER",
                nullable=False,
                ordinal=0,
            )
        ],
        schema_fingerprint="fingerprint",
        version=1,
        capabilities={"READ"},
        lifecycle_status=LifecycleStatus.PUBLISHED,
        created_by_workflow_run_id="run-1",
        created_by_node_run_id="node-run-1",
        created_at=utc_now(),
    )
