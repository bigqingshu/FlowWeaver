from __future__ import annotations

import pytest

from flowweaver.engine.runtime_table_provider import (
    SQLiteRuntimeTableProvider,
    schema_fingerprint,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import FieldSchemaModel


def table_schema() -> list[FieldSchemaModel]:
    return [
        FieldSchemaModel(
            field_id="row-id",
            name="row_id",
            data_type="INTEGER",
            nullable=False,
            ordinal=0,
        ),
        FieldSchemaModel(
            field_id="amount",
            name="amount",
            data_type="FLOAT",
            nullable=False,
            ordinal=1,
        ),
        FieldSchemaModel(
            field_id="category",
            name="category",
            data_type="TEXT",
            nullable=False,
            ordinal=2,
        ),
    ]


def test_sqlite_runtime_provider_uses_independent_workflow_run_databases(
    tmp_path,
) -> None:
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")

    first = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-1",
        output_name="orders",
        schema=table_schema(),
    )
    second = provider.create_staging_table(
        workflow_run_id="run-2",
        node_run_id="node-run-2",
        output_name="orders",
        schema=table_schema(),
    )

    assert first.opaque_handle["database_path"] != second.opaque_handle["database_path"]
    assert first.opaque_handle["database_path"].endswith("run_1.db")
    assert second.opaque_handle["database_path"].endswith("run_2.db")


def test_staging_table_can_be_written_read_and_published(tmp_path) -> None:
    schema = table_schema()
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    staging = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-1",
        output_name="orders",
        schema=schema,
    )

    provider.insert_rows(
        staging,
        [
            {"row_id": 1, "amount": 12.5, "category": "keep"},
            {"row_id": 2, "amount": 3.0, "category": "drop"},
            {"row_id": 3, "amount": 18.0, "category": "keep"},
        ],
    )
    filtered_rows = provider.read_rows(
        staging,
        offset=0,
        limit=10,
        columns=["row_id", "amount"],
        filters=[{"field": "category", "operator": "eq", "value": "keep"}],
        order_by=["-amount"],
    )
    published = provider.published_ref_from_staging(staging)

    provider.publish_staging(staging, published)

    assert staging.role == TableRole.CURRENT
    assert staging.storage_kind == TableStorageKind.RUNTIME_SQL
    assert staging.scope == TableScope.WORKFLOW_SCOPE
    assert staging.mutability == TableMutability.WORKING_MUTABLE
    assert staging.lifecycle_status == LifecycleStatus.STAGING
    assert staging.provider_id == provider.provider_id
    assert staging.schema_fingerprint == schema_fingerprint(schema)
    assert provider.count_rows(staging) == 3
    assert filtered_rows == [
        {"row_id": 3, "amount": 18.0},
        {"row_id": 1, "amount": 12.5},
    ]
    assert published.mutability == TableMutability.PUBLISHED_IMMUTABLE
    assert published.lifecycle_status == LifecycleStatus.PUBLISHED
    assert published.capabilities == {"READ"}
    assert provider.get_schema(published) == schema
    assert provider.count_rows(published) == 3
    assert provider.read_rows(published, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 12.5, "category": "keep"},
        {"row_id": 2, "amount": 3.0, "category": "drop"},
        {"row_id": 3, "amount": 18.0, "category": "keep"},
    ]
    with pytest.raises(ValueError, match="only STAGING"):
        provider.insert_rows(published, [{"row_id": 4, "amount": 1.0, "category": "x"}])


def test_publish_rejects_schema_mismatch(tmp_path) -> None:
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    staging = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-1",
        output_name="orders",
        schema=table_schema(),
    )
    published = provider.published_ref_from_staging(staging).model_copy(
        update={"schema_fingerprint": "different"}
    )

    with pytest.raises(ValueError, match="schema must match"):
        provider.publish_staging(staging, published)
