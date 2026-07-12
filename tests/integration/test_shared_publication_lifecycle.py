from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from threading import Barrier

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, text

from flowweaver.common.database import sqlite_url
from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.shared_publication_lifecycle import (
    SharedPublicationCleanupBlocker,
    SharedPublicationLifecycleService,
)
from flowweaver.engine.shared_table_reader import (
    SharedTableReader,
    SharedTableVersionPolicy,
)
from flowweaver.engine.table_lease_manager import TableLeaseManager
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
    WorkflowRunStatus,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")
    return RuntimeStore.from_sqlite_path(database_path)


def make_table_ref(
    *,
    table_ref_id: str,
    logical_table_id: str,
    workflow_run_id: str = "run-lifecycle-producer",
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
            "database_path": "runtime/lifecycle.db",
            "table_name": table_ref_id,
        },
        schema=[
            FieldSchemaModel(
                field_id=f"{table_ref_id}-field",
                name="value",
                data_type="INTEGER",
                nullable=False,
                ordinal=0,
            )
        ],
        schema_fingerprint=f"{table_ref_id}-schema",
        version=1,
        capabilities={"READ"},
        lifecycle_status=LifecycleStatus.PUBLISHED,
        created_by_workflow_run_id=workflow_run_id,
        created_by_node_run_id="node-lifecycle-producer",
        created_at=utc_now(),
    )


def seed_lifecycle_context(
    tmp_path: Path,
    *,
    old_member_count: int = 1,
    producer_status: WorkflowRunStatus = WorkflowRunStatus.SUCCEEDED,
) -> tuple[
    RuntimeStore,
    SharedPublicationLifecycleService,
    SharedTableReader,
    str,
    str,
    tuple[str, ...],
    datetime,
]:
    store = make_store(tmp_path)
    producer_workflow = store.create_workflow_definition(
        name="Lifecycle producer",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-lifecycle-producer",
    )
    store.create_workflow_run(
        workflow_id=producer_workflow.workflow_id,
        workflow_run_id="run-lifecycle-producer",
        status=producer_status,
    )
    store.create_node_run(
        workflow_run_id="run-lifecycle-producer",
        node_instance_id="source",
        node_type="core.source",
        node_run_id="node-lifecycle-producer",
    )
    consumer_workflow = store.create_workflow_definition(
        name="Lifecycle consumer",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-lifecycle-consumer",
    )
    store.create_workflow_run(
        workflow_id=consumer_workflow.workflow_id,
        workflow_run_id="run-lifecycle-consumer",
    )
    old_table_ref_ids = []
    old_members = {}
    for index in range(old_member_count):
        table_ref = make_table_ref(
            table_ref_id=f"table-lifecycle-old-{index}",
            logical_table_id=f"old-{index}",
        )
        store.register_table_ref(table_ref)
        old_table_ref_ids.append(table_ref.table_ref_id)
        old_members[f"member-{index}"] = table_ref.table_ref_id
    latest_table_ref = make_table_ref(
        table_ref_id="table-lifecycle-latest",
        logical_table_id="latest",
    )
    store.register_table_ref(latest_table_ref)
    old_publication = store.create_shared_publication(
        publication_id="publication-lifecycle-old",
        share_name="lifecycle-share",
        producer_workflow_id=producer_workflow.workflow_id,
        producer_run_id="run-lifecycle-producer",
        members=old_members,
        retention_policy={"retention_seconds": 1},
    )
    latest_publication = store.create_shared_publication(
        publication_id="publication-lifecycle-latest",
        share_name="lifecycle-share",
        producer_workflow_id=producer_workflow.workflow_id,
        producer_run_id="run-lifecycle-producer",
        members={"latest": latest_table_ref.table_ref_id},
        retention_policy={"retention_seconds": 1},
    )
    evaluated_at = latest_publication.created_at + timedelta(seconds=2)
    return (
        store,
        SharedPublicationLifecycleService(store),
        SharedTableReader(store),
        old_publication.publication_id,
        latest_publication.publication_id,
        tuple(old_table_ref_ids),
        evaluated_at,
    )


def blocker_values(preview) -> set[str]:
    return {blocker.value for blocker in preview.blockers}


def test_cleanup_preview_is_fixed_query_and_candidate_lookup_is_bounded(
    tmp_path: Path,
) -> None:
    store, service, _reader, old_id, _latest_id, _table_ids, now = (
        seed_lifecycle_context(tmp_path, old_member_count=25)
    )
    select_count = 0

    def count_selects(
        _connection,
        _cursor,
        statement: str,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    event.listen(store.engine, "before_cursor_execute", count_selects)
    try:
        preview = service.preview(old_id, now=now)
    finally:
        event.remove(store.engine, "before_cursor_execute", count_selects)

    assert preview is not None
    assert preview.eligible is True
    assert preview.blockers == ()
    assert preview.releasable_member_count == 25
    assert preview.protected_member_count == 0
    assert select_count == 6
    assert store.list_expired_shared_publication_ids(now=now, limit=1) == [old_id]

    with store.engine.connect() as connection:
        query_plan = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN "
            "SELECT publication_id FROM shared_publications "
            "WHERE status = 'PUBLISHED' "
            "AND expires_at IS NOT NULL "
            "AND expires_at <= '2099-01-01T00:00:00+00:00' "
            "ORDER BY expires_at, publication_id LIMIT 1"
        ).all()
    assert any(
        "idx_shared_publications_status_expires" in str(row[3])
        for row in query_plan
    )


def test_cleanup_preview_reports_active_lease_and_reference_blockers(
    tmp_path: Path,
) -> None:
    store, service, reader, old_id, _latest_id, table_ids, now = (
        seed_lifecycle_context(tmp_path)
    )
    reader.read(
        consumer_workflow_run_id="run-lifecycle-consumer",
        share_name="lifecycle-share",
        version_policy=SharedTableVersionPolicy.EXACT_VERSION,
        exact_version=1,
        lease_expires_at=now + timedelta(minutes=5),
    )
    lease = TableLeaseManager(store.engine).acquire_read_lease(
        table_ref_id=table_ids[0],
        owner_id="preview-test",
        ttl_seconds=300,
    )
    assert lease.granted is True
    store.create_shared_publication(
        publication_id="publication-lifecycle-reference",
        share_name="lifecycle-reference-share",
        producer_workflow_id="workflow-lifecycle-producer",
        producer_run_id="run-lifecycle-producer",
        members={"referenced": table_ids[0]},
        retention_policy={"retention_seconds": 1},
    )

    preview = service.preview(old_id, now=now)

    assert preview is not None
    assert {
        SharedPublicationCleanupBlocker.ACTIVE_READ_LEASE.value,
        SharedPublicationCleanupBlocker.ACTIVE_TABLE_LEASE.value,
        SharedPublicationCleanupBlocker.MEMBER_REFERENCED_BY_OTHER_PUBLICATION.value,
    }.issubset(blocker_values(preview))
    assert preview.active_read_lease_count == 1
    assert preview.active_table_lease_count == 1
    assert preview.releasable_member_count == 0
    assert preview.protected_member_count == 1


def test_cleanup_preview_explains_retention_latest_and_active_producer(
    tmp_path: Path,
) -> None:
    store, service, _reader, _old_id, latest_id, _table_ids, _now = (
        seed_lifecycle_context(
            tmp_path,
            producer_status=WorkflowRunStatus.PENDING,
        )
    )
    latest = store.get_shared_publication(latest_id)
    assert latest is not None

    preview = service.preview(latest_id, now=latest.created_at)

    assert preview is not None
    assert {
        SharedPublicationCleanupBlocker.RETENTION_NOT_EXPIRED.value,
        SharedPublicationCleanupBlocker.LATEST_VERSION_PROTECTED.value,
        SharedPublicationCleanupBlocker.PRODUCER_RUN_ACTIVE.value,
    }.issubset(blocker_values(preview))


def test_cleanup_preview_explains_missing_retention(tmp_path: Path) -> None:
    store, service, _reader, old_id, _latest_id, _table_ids, now = (
        seed_lifecycle_context(tmp_path)
    )
    with store.engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE shared_publications SET expires_at = NULL "
                "WHERE publication_id = :publication_id"
            ),
            {"publication_id": old_id},
        )

    preview = service.preview(old_id, now=now)

    assert preview is not None
    assert SharedPublicationCleanupBlocker.RETENTION_NOT_CONFIGURED.value in (
        blocker_values(preview)
    )


@pytest.mark.parametrize(
    ("statement", "expected_blocker"),
    [
        (
            "UPDATE data_refs SET storage_kind = 'MEMORY' "
            "WHERE table_ref_id = 'table-lifecycle-old-0'",
            SharedPublicationCleanupBlocker.MEMBER_NOT_RELEASABLE,
        ),
        (
            "UPDATE shared_publication_members SET exact_table_version = 99 "
            "WHERE publication_id = 'publication-lifecycle-old'",
            SharedPublicationCleanupBlocker.PUBLICATION_INCONSISTENT,
        ),
    ],
)
def test_cleanup_preview_explains_member_blockers(
    tmp_path: Path,
    statement: str,
    expected_blocker: SharedPublicationCleanupBlocker,
) -> None:
    store, service, _reader, old_id, _latest_id, _table_ids, now = (
        seed_lifecycle_context(tmp_path)
    )
    with store.engine.begin() as connection:
        connection.exec_driver_sql(statement)

    preview = service.preview(old_id, now=now)

    assert preview is not None
    assert expected_blocker.value in blocker_values(preview)


def test_reader_first_blocks_cleanup_claim(tmp_path: Path) -> None:
    _store, service, reader, old_id, _latest_id, _table_ids, now = (
        seed_lifecycle_context(tmp_path)
    )
    reader.read(
        consumer_workflow_run_id="run-lifecycle-consumer",
        share_name="lifecycle-share",
        version_policy=SharedTableVersionPolicy.EXACT_VERSION,
        exact_version=1,
        lease_expires_at=now + timedelta(minutes=5),
    )

    preview = service.preview(old_id, now=now)
    claim = service.claim(old_id, now=now)

    assert preview is not None
    assert SharedPublicationCleanupBlocker.ACTIVE_READ_LEASE.value in (
        blocker_values(preview)
    )
    assert claim.claimed is False


def test_cleanup_claim_first_makes_exact_reader_unavailable(tmp_path: Path) -> None:
    store, service, reader, old_id, _latest_id, _table_ids, now = (
        seed_lifecycle_context(tmp_path)
    )

    claim = service.claim(old_id, now=now)

    assert claim.claimed is True
    with pytest.raises(ValueError, match="Shared publication not found"):
        reader.read(
            consumer_workflow_run_id="run-lifecycle-consumer",
            share_name="lifecycle-share",
            version_policy=SharedTableVersionPolicy.EXACT_VERSION,
            exact_version=1,
            lease_expires_at=now + timedelta(minutes=5),
        )
    claimed = store.get_shared_publication(old_id)
    assert claimed is not None
    assert claimed.status == "RELEASING"
    assert claimed.cleanup_attempt_count == 1
    assert store.get_shared_publication_version(
        share_name="lifecycle-share",
        publication_version=1,
    ) is None
    latest = store.get_latest_shared_publication("lifecycle-share")
    assert latest is not None
    assert latest.publication_id == "publication-lifecycle-latest"

    preview = service.preview(old_id, now=now)
    assert preview is not None
    assert SharedPublicationCleanupBlocker.PUBLICATION_NOT_PUBLISHED.value in (
        blocker_values(preview)
    )


def test_two_cleanup_claimants_only_transition_once(tmp_path: Path) -> None:
    store, service, _reader, old_id, _latest_id, _table_ids, now = (
        seed_lifecycle_context(tmp_path)
    )
    barrier = Barrier(2)

    def claim() -> bool:
        barrier.wait()
        return service.claim(old_id, now=now).claimed

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: claim(), range(2)))

    assert sorted(results) == [False, True]
    publication = store.get_shared_publication(old_id)
    assert publication is not None
    assert publication.status == "RELEASING"
    assert publication.cleanup_attempt_count == 1
    with store.engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == 5000
