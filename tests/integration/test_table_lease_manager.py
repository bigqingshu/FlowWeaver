from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.table_lease_manager import TableLeaseManager
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableLeaseStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    store.register_table_ref(
        TableRefModel(
            table_ref_id="table-1",
            role=TableRole.CURRENT,
            storage_kind=TableStorageKind.RUNTIME_SQL,
            scope=TableScope.WORKFLOW_SCOPE,
            mutability=TableMutability.PUBLISHED_IMMUTABLE,
            provider_id="sqlite_runtime",
            resource_profile_id="profile-1",
            mount_id="mount-1",
            logical_table_id="orders",
            opaque_handle={"database_path": "run.db", "table_name": "orders_v1"},
            schema=[
                FieldSchemaModel(
                    field_id="field-1",
                    name="amount",
                    data_type="FLOAT",
                    nullable=False,
                    ordinal=0,
                )
            ],
            schema_fingerprint="fingerprint-1",
            version=1,
            capabilities={"READ"},
            lifecycle_status=LifecycleStatus.PUBLISHED,
            created_by_workflow_run_id="run-1",
            created_by_node_run_id="node-1",
            created_at=utc_now(),
        )
    )
    return store


def test_read_leases_can_share_and_block_write(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    manager = TableLeaseManager(store.engine)

    first = manager.acquire_read_lease(
        table_ref_id="table-1",
        owner_id="consumer-a",
        ttl_seconds=60,
    )
    second = manager.acquire_read_lease(
        table_ref_id="table-1",
        owner_id="consumer-b",
        ttl_seconds=60,
    )
    blocked_write = manager.acquire_write_lease(
        table_ref_id="table-1",
        owner_id="producer",
        ttl_seconds=60,
    )

    assert first.granted is True
    assert second.granted is True
    assert manager.active_read_count("table-1") == 2
    assert blocked_write.granted is False
    assert blocked_write.reason == "TABLE_LEASE_CONFLICT"

    assert first.lease is not None
    assert second.lease is not None
    assert manager.release(first.lease.lease_id) is True
    assert manager.release(second.lease.lease_id) is True
    granted_write = manager.acquire_write_lease(
        table_ref_id="table-1",
        owner_id="producer",
        ttl_seconds=60,
    )

    assert granted_write.granted is True


def test_write_lease_blocks_read_until_released(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    manager = TableLeaseManager(store.engine)

    write = manager.acquire_write_lease(
        table_ref_id="table-1",
        owner_id="producer",
        ttl_seconds=60,
    )
    blocked_read = manager.acquire_read_lease(
        table_ref_id="table-1",
        owner_id="consumer",
        ttl_seconds=60,
    )

    assert write.granted is True
    assert blocked_read.granted is False
    assert write.lease is not None
    assert manager.release(write.lease.lease_id) is True
    assert manager.acquire_read_lease(
        table_ref_id="table-1",
        owner_id="consumer",
        ttl_seconds=60,
    ).granted


def test_expired_read_lease_is_recovered_before_write(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    manager = TableLeaseManager(store.engine)

    read = manager.acquire_read_lease(
        table_ref_id="table-1",
        owner_id="consumer",
        ttl_seconds=0,
    )
    write = manager.acquire_write_lease(
        table_ref_id="table-1",
        owner_id="producer",
        ttl_seconds=60,
    )

    assert read.granted is True
    assert write.granted is True
    assert write.lease is not None
    assert write.lease.status == TableLeaseStatus.ACTIVE.value


def test_table_lease_rejects_releasable_table_ref(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    manager = TableLeaseManager(store.engine)
    with store.engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE data_refs SET lifecycle_status = 'RELEASABLE' "
                "WHERE table_ref_id = 'table-1'"
            )
        )

    result = manager.acquire_read_lease(
        table_ref_id="table-1",
        owner_id="late-reader",
        ttl_seconds=60,
    )

    assert result.granted is False
    assert result.reason == "TABLE_REF_NOT_AVAILABLE"
