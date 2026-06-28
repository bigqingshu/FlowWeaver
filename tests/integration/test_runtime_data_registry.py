from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.protocols.enums import LifecycleStatus
from flowweaver.protocols.table_ref import FieldSchemaModel


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    return RuntimeStore.from_sqlite_path(database_path)


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
    ]


def test_runtime_data_registry_registers_and_publishes_table_refs(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    staging = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-1",
        output_name="orders",
        schema=table_schema(),
    )
    provider.insert_rows(
        staging,
        [
            {"row_id": 1, "amount": 12.5},
            {"row_id": 2, "amount": 3.0},
        ],
    )

    registry.register_staging(staging)
    published = registry.publish(staging.table_ref_id)

    assert registry.get(staging.table_ref_id) == staging
    assert registry.get(published.table_ref_id) == published
    assert published.lifecycle_status == LifecycleStatus.PUBLISHED
    assert published.version == staging.version + 1
    assert published.opaque_handle["database_path"] == staging.opaque_handle[
        "database_path"
    ]
    assert published.opaque_handle["table_name"].startswith("pub_")
    assert provider.count_rows(published) == 2
    assert provider.read_rows(published, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 12.5},
        {"row_id": 2, "amount": 3.0},
    ]
    refs_by_run = registry.list_by_workflow_run("run-1")
    assert {table_ref.table_ref_id for table_ref in refs_by_run} == {
        staging.table_ref_id,
        published.table_ref_id,
    }


def test_runtime_data_registry_cleans_staging_refs_for_node(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    staging = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-1",
        output_name="orders",
        schema=table_schema(),
    )
    other_staging = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-2",
        output_name="other_orders",
        schema=table_schema(),
    )
    provider.insert_rows(staging, [{"row_id": 1, "amount": 12.5}])
    provider.insert_rows(other_staging, [{"row_id": 2, "amount": 3.0}])
    registry.register_staging(staging)
    registry.register_staging(other_staging)

    cleaned = registry.cleanup_staging_for_node(
        workflow_run_id="run-1",
        node_run_id="node-run-1",
    )

    cleaned_ref = registry.get(staging.table_ref_id)
    other_ref = registry.get(other_staging.table_ref_id)
    assert [item.table_ref_id for item in cleaned] == [staging.table_ref_id]
    assert cleaned_ref.lifecycle_status == LifecycleStatus.RELEASED
    assert other_ref.lifecycle_status == LifecycleStatus.STAGING
    assert provider.count_rows(other_ref) == 1
    with pytest.raises(sqlite3.OperationalError):
        provider.count_rows(staging)


def test_runtime_data_registry_rejects_non_staging_registration(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    staging = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-1",
        output_name="orders",
        schema=table_schema(),
    )
    published = provider.published_ref_from_staging(staging)

    with pytest.raises(ValueError, match="STAGING"):
        registry.register_staging(published)

    with pytest.raises(KeyError):
        registry.get(published.table_ref_id)


def test_runtime_data_registry_publish_requires_existing_staging_ref(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)

    with pytest.raises(KeyError):
        registry.publish("missing-table-ref")
