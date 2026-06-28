from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from flowweaver.common.database import sqlite_url
from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import InputSnapshotEntry, RuntimeStore
from flowweaver.engine.shared_table_reader import (
    SharedTableReader,
    SharedTableVersionPolicy,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def alembic_config(database_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    return config


def migrate(database_path: Path) -> None:
    command.upgrade(alembic_config(database_path), "head")


def row_count(database_path: Path, table_name: str) -> int:
    import sqlite3

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return int(row[0])


def make_table_ref(
    *,
    table_ref_id: str,
    workflow_run_id: str,
    node_run_id: str,
    logical_table_id: str,
    version: int,
) -> TableRefModel:
    return TableRefModel(
        table_ref_id=table_ref_id,
        role=TableRole.CURRENT,
        storage_kind=TableStorageKind.RUNTIME_SQL,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.PUBLISHED_IMMUTABLE,
        provider_id="sqlite_runtime",
        resource_profile_id=None,
        mount_id=None,
        logical_table_id=logical_table_id,
        opaque_handle={
            "database_path": "runtime/run.db",
            "table_name": f"{logical_table_id}_v{version}",
        },
        schema=[
            FieldSchemaModel(
                field_id=f"{logical_table_id}-field-1",
                name="amount",
                data_type="FLOAT",
                nullable=False,
                ordinal=0,
            )
        ],
        schema_fingerprint=f"{logical_table_id}-fingerprint-{version}",
        version=version,
        capabilities={"READ"},
        lifecycle_status=LifecycleStatus.PUBLISHED,
        created_by_workflow_run_id=workflow_run_id,
        created_by_node_run_id=node_run_id,
        created_at=utc_now(),
    )


def create_workflow_run(
    store: RuntimeStore,
    *,
    workflow_id: str,
    workflow_run_id: str,
) -> None:
    workflow = store.create_workflow_definition(
        name=f"Workflow {workflow_id}",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id=workflow_id,
    )
    store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id=workflow_run_id,
    )
    store.create_node_run(
        workflow_run_id=workflow_run_id,
        node_instance_id=f"{workflow_id}-node",
        node_type="builtin.test",
        node_run_id=f"{workflow_run_id}-node",
    )


def setup_publications(
    tmp_path: Path,
) -> tuple[RuntimeStore, SharedTableReader]:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    create_workflow_run(
        store,
        workflow_id="workflow-producer",
        workflow_run_id="run-producer",
    )
    create_workflow_run(
        store,
        workflow_id="workflow-consumer",
        workflow_run_id="run-consumer",
    )
    orders_v1 = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="orders",
        version=1,
    )
    customers_v1 = make_table_ref(
        table_ref_id="table-customers-v1",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="customers",
        version=1,
    )
    orders_v2 = make_table_ref(
        table_ref_id="table-orders-v2",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="orders",
        version=2,
    )
    store.register_table_ref(orders_v1)
    store.register_table_ref(customers_v1)
    store.register_table_ref(orders_v2)
    store.create_shared_publication(
        publication_id="publication-v1",
        share_name="daily_report",
        producer_workflow_id="workflow-producer",
        producer_run_id="run-producer",
        members={
            "orders": orders_v1.table_ref_id,
            "customers": customers_v1.table_ref_id,
        },
    )
    store.create_shared_publication(
        publication_id="publication-v2",
        share_name="daily_report",
        producer_workflow_id="workflow-producer",
        producer_run_id="run-producer",
        members={"orders": orders_v2.table_ref_id},
    )
    return store, SharedTableReader(store)


def test_shared_table_reader_latest_returns_current_publication(
    tmp_path: Path,
) -> None:
    store, reader = setup_publications(tmp_path)

    result = reader.read(
        consumer_workflow_run_id="run-consumer",
        share_name="daily_report",
        version_policy=SharedTableVersionPolicy.LATEST,
        lease_expires_at=utc_now() + timedelta(seconds=60),
    )

    assert result.publication.publication_id == "publication-v2"
    assert [table.table_ref_id for table in result.table_refs] == ["table-orders-v2"]
    assert result.input_snapshot.inputs[0].publication_id == "publication-v2"
    assert result.input_snapshot.inputs[0].publication_version == 2
    assert result.read_lease.publication_id == "publication-v2"
    assert result.read_lease.selected_members == ("orders",)
    loaded_run = store.get_workflow_run("run-consumer")
    assert loaded_run is not None
    assert loaded_run.input_snapshot_id == result.input_snapshot.input_snapshot_id


def test_shared_table_reader_exact_version_keeps_previous_publication(
    tmp_path: Path,
) -> None:
    store, reader = setup_publications(tmp_path)

    result = reader.read(
        consumer_workflow_run_id="run-consumer",
        share_name="daily_report",
        version_policy=SharedTableVersionPolicy.EXACT_VERSION,
        exact_version=1,
        lease_expires_at=utc_now() + timedelta(seconds=60),
    )

    assert result.publication.publication_id == "publication-v1"
    assert [table.table_ref_id for table in result.table_refs] == [
        "table-customers-v1",
        "table-orders-v1",
    ]
    assert result.input_snapshot.inputs[0].publication_id == "publication-v1"
    assert result.input_snapshot.inputs[0].publication_version == 1
    assert store.get_latest_shared_publication("daily_report").publication_id == (
        "publication-v2"
    )
    assert result.read_lease.publication_version == 1


def test_shared_table_reader_selected_members_are_fixed_atomically(
    tmp_path: Path,
) -> None:
    _store, reader = setup_publications(tmp_path)

    result = reader.read(
        consumer_workflow_run_id="run-consumer",
        share_name="daily_report",
        version_policy="EXACT_VERSION",
        exact_version=1,
        selected_members=("orders",),
        lease_expires_at=utc_now() + timedelta(seconds=60),
    )

    assert [table.table_ref_id for table in result.table_refs] == ["table-orders-v1"]
    assert result.input_snapshot.inputs[0].selected_members == ("orders",)
    assert result.read_lease.selected_members == ("orders",)


def test_shared_table_reader_exact_version_requires_version(tmp_path: Path) -> None:
    _store, reader = setup_publications(tmp_path)

    with pytest.raises(ValueError, match="EXACT_VERSION requires exact_version"):
        reader.read(
            consumer_workflow_run_id="run-consumer",
            share_name="daily_report",
            version_policy=SharedTableVersionPolicy.EXACT_VERSION,
            lease_expires_at=utc_now() + timedelta(seconds=60),
        )


def test_shared_table_reader_rejects_missing_selected_member(tmp_path: Path) -> None:
    _store, reader = setup_publications(tmp_path)

    with pytest.raises(ValueError, match="Shared publication members not found: x"):
        reader.read(
            consumer_workflow_run_id="run-consumer",
            share_name="daily_report",
            version_policy=SharedTableVersionPolicy.EXACT_VERSION,
            exact_version=1,
            selected_members=("x",),
            lease_expires_at=utc_now() + timedelta(seconds=60),
        )


def test_shared_table_reader_rejects_missing_consumer_run_atomically(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    create_workflow_run(
        store,
        workflow_id="workflow-producer",
        workflow_run_id="run-producer",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="orders",
        version=1,
    )
    store.register_table_ref(orders)
    store.create_shared_publication(
        publication_id="publication-v1",
        share_name="daily_report",
        producer_workflow_id="workflow-producer",
        producer_run_id="run-producer",
        members={"orders": orders.table_ref_id},
    )
    reader = SharedTableReader(store)

    with pytest.raises(ValueError, match="Workflow run not found: missing-run"):
        reader.read(
            consumer_workflow_run_id="missing-run",
            share_name="daily_report",
            version_policy=SharedTableVersionPolicy.LATEST,
            lease_expires_at=utc_now() + timedelta(seconds=60),
        )

    assert row_count(database_path, "input_snapshots") == 0
    assert row_count(database_path, "read_leases") == 0


def test_create_snapshot_and_lease_rejects_mismatched_members_atomically(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    create_workflow_run(
        store,
        workflow_id="workflow-producer",
        workflow_run_id="run-producer",
    )
    create_workflow_run(
        store,
        workflow_id="workflow-consumer",
        workflow_run_id="run-consumer",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="orders",
        version=1,
    )
    customers = make_table_ref(
        table_ref_id="table-customers-v1",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="customers",
        version=1,
    )
    store.register_table_ref(orders)
    store.register_table_ref(customers)
    publication = store.create_shared_publication(
        publication_id="publication-v1",
        share_name="daily_report",
        producer_workflow_id="workflow-producer",
        producer_run_id="run-producer",
        members={
            "orders": orders.table_ref_id,
            "customers": customers.table_ref_id,
        },
    )

    with pytest.raises(
        ValueError,
        match="Input snapshot and read lease selected members mismatch",
    ):
        store.create_input_snapshot_and_read_lease(
            workflow_run_id="run-consumer",
            inputs=[
                InputSnapshotEntry(
                    source_name="daily_report",
                    publication_id=publication.publication_id,
                    publication_version=publication.publication_version,
                    selected_members=("orders", "customers"),
                )
            ],
            publication_id=publication.publication_id,
            publication_version=publication.publication_version,
            selected_members=("orders",),
            expires_at=utc_now() + timedelta(seconds=60),
        )

    assert row_count(database_path, "input_snapshots") == 0
    assert row_count(database_path, "read_leases") == 0
