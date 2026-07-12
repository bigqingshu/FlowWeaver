from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from threading import Barrier

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, insert, text

from flowweaver.common.config import EngineConfig
from flowweaver.common.database import sqlite_url
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import SharedPublicationRecord
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.engine.shared_publication_cleanup_worker import (
    SharedPublicationCleanupWorker,
)
from flowweaver.engine.shared_publication_lifecycle import (
    SharedPublicationCleanupBlocker,
    SharedPublicationCleanupOutcome,
    SharedPublicationLifecycleService,
)
from flowweaver.engine.shared_table_reader import (
    SharedTableReader,
    SharedTableVersionPolicy,
)
from flowweaver.engine.table_lease_manager import TableLeaseManager
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.engine.table_ref_release import (
    TableRefReleaseOutcome,
    TableRefReleaseService,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
    WorkflowRunStatus,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


class CountingRuntimeProvider(SQLiteRuntimeTableProvider):
    def __init__(self, runtime_dir: Path) -> None:
        super().__init__(runtime_dir)
        self.drop_calls = 0

    def drop_table(self, table_ref: TableRefModel) -> None:
        self.drop_calls += 1
        super().drop_table(table_ref)


class FailOnceRuntimeProvider(CountingRuntimeProvider):
    def drop_table(self, table_ref: TableRefModel) -> None:
        self.drop_calls += 1
        if self.drop_calls == 1:
            raise ValueError("temporary cleanup failure")
        SQLiteRuntimeTableProvider.drop_table(self, table_ref)


class NoopCountingRuntimeProvider(SQLiteRuntimeTableProvider):
    def __init__(self, runtime_dir: Path) -> None:
        super().__init__(runtime_dir)
        self.drop_calls = 0

    def drop_table(self, table_ref: TableRefModel) -> None:
        self.drop_calls += 1


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


def register_runtime_table(
    store: RuntimeStore,
    provider: SQLiteRuntimeTableProvider,
    *,
    workflow_run_id: str,
    node_run_id: str,
    output_name: str,
    value: int = 1,
) -> TableRefModel:
    staging = provider.create_staging_table(
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
        output_name=output_name,
        schema=[
            FieldSchemaModel(
                field_id=f"{output_name}-value",
                name="value",
                data_type="INTEGER",
                nullable=False,
                ordinal=0,
            )
        ],
    )
    provider.insert_rows(staging, [{"value": value}])
    published = provider.published_ref_from_staging(staging)
    provider.publish_staging(staging, published)
    store.register_table_ref(published)
    return published


def seed_cleanup_context(
    tmp_path: Path,
    *,
    old_member_count: int = 1,
) -> tuple[
    RuntimeStore,
    SQLiteRuntimeTableProvider,
    str,
    tuple[TableRefModel, ...],
    datetime,
]:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Cleanup producer",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-cleanup-producer",
    )
    store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-cleanup-producer",
        status=WorkflowRunStatus.SUCCEEDED,
    )
    store.create_node_run(
        workflow_run_id="run-cleanup-producer",
        node_instance_id="source",
        node_type="core.source",
        node_run_id="node-cleanup-producer",
    )
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime-tables")
    old_refs = tuple(
        register_runtime_table(
            store,
            provider,
            workflow_run_id="run-cleanup-producer",
            node_run_id="node-cleanup-producer",
            output_name=f"old_{index}",
        )
        for index in range(old_member_count)
    )
    latest_ref = register_runtime_table(
        store,
        provider,
        workflow_run_id="run-cleanup-producer",
        node_run_id="node-cleanup-producer",
        output_name="latest",
    )
    old_publication = store.create_shared_publication(
        publication_id="publication-cleanup-old",
        share_name="cleanup-share",
        producer_workflow_id=workflow.workflow_id,
        producer_run_id="run-cleanup-producer",
        members={
            f"member-{index}": table_ref.table_ref_id
            for index, table_ref in enumerate(old_refs)
        },
        retention_policy={"retention_seconds": 1},
    )
    latest_publication = store.create_shared_publication(
        publication_id="publication-cleanup-latest",
        share_name="cleanup-share",
        producer_workflow_id=workflow.workflow_id,
        producer_run_id="run-cleanup-producer",
        members={"latest": latest_ref.table_ref_id},
        retention_policy={"retention_seconds": 1},
    )
    return (
        store,
        provider,
        old_publication.publication_id,
        old_refs,
        latest_publication.created_at + timedelta(seconds=2),
    )


def make_cleanup_service(
    store: RuntimeStore,
    provider: SQLiteRuntimeTableProvider,
) -> SharedPublicationLifecycleService:
    registry = TableProviderRegistry()
    registry.register(provider, storage_kinds=(TableStorageKind.RUNTIME_SQL,))
    return SharedPublicationLifecycleService(
        store,
        table_ref_release_service=TableRefReleaseService(
            store=store,
            provider_registry=registry,
        ),
    )


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


def test_manual_cleanup_releases_runtime_table_and_is_idempotent(
    tmp_path: Path,
) -> None:
    store, provider, publication_id, old_refs, now = seed_cleanup_context(tmp_path)
    service = make_cleanup_service(store, provider)

    first = service.cleanup(publication_id, now=now)
    second = service.cleanup(publication_id, now=now)

    assert first.outcome == SharedPublicationCleanupOutcome.CLEANED
    assert first.status == "RELEASED"
    assert first.processed_member_count == 1
    assert first.released_member_count == 1
    assert first.remaining_member_count == 0
    assert second.outcome == SharedPublicationCleanupOutcome.ALREADY_RELEASED
    publication = store.get_shared_publication(publication_id)
    assert publication is not None
    assert publication.status == "RELEASED"
    assert publication.released_at == now
    assert [member.table_ref_id for member in publication.members] == [
        old_refs[0].table_ref_id
    ]
    released_ref = store.get_table_ref(old_refs[0].table_ref_id)
    assert released_ref is not None
    assert released_ref.lifecycle_status == LifecycleStatus.RELEASED
    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        provider.read_rows(old_refs[0], offset=0, limit=1)


def test_manual_cleanup_failure_stays_releasing_and_retries(
    tmp_path: Path,
) -> None:
    store, _provider, publication_id, old_refs, now = seed_cleanup_context(tmp_path)
    provider = FailOnceRuntimeProvider(tmp_path / "runtime-tables")
    service = make_cleanup_service(store, provider)

    first = service.cleanup(publication_id, now=now)
    claimed_ref = store.get_table_ref(old_refs[0].table_ref_id)
    failed_publication = store.get_shared_publication(publication_id)
    second = service.cleanup(publication_id, now=now + timedelta(seconds=1))

    assert first.outcome == SharedPublicationCleanupOutcome.RETRY_PENDING
    assert first.failed_member_count == 1
    assert first.remaining_member_count == 1
    assert claimed_ref is not None
    assert claimed_ref.lifecycle_status == LifecycleStatus.RELEASABLE
    assert failed_publication is not None
    assert failed_publication.status == "RELEASING"
    assert failed_publication.last_cleanup_error is not None
    assert second.outcome == SharedPublicationCleanupOutcome.CLEANED
    assert second.released_member_count == 1
    assert provider.drop_calls == 2
    completed = store.get_shared_publication(publication_id)
    assert completed is not None
    assert completed.status == "RELEASED"
    assert completed.cleanup_attempt_count == 2
    assert completed.last_cleanup_error is None


def test_manual_cleanup_is_bounded_and_finishes_in_multiple_calls(
    tmp_path: Path,
) -> None:
    store, provider, publication_id, old_refs, now = seed_cleanup_context(
        tmp_path,
        old_member_count=3,
    )
    service = make_cleanup_service(store, provider)

    first = service.cleanup(publication_id, max_table_refs=1, now=now)
    second = service.cleanup(
        publication_id,
        max_table_refs=1,
        now=now + timedelta(seconds=1),
    )
    third = service.cleanup(
        publication_id,
        max_table_refs=1,
        now=now + timedelta(seconds=2),
    )

    assert first.outcome == SharedPublicationCleanupOutcome.RETRY_PENDING
    assert first.processed_member_count == 1
    assert first.remaining_member_count == 2
    assert second.outcome == SharedPublicationCleanupOutcome.RETRY_PENDING
    assert second.processed_member_count == 1
    assert third.outcome == SharedPublicationCleanupOutcome.CLEANED
    assert third.processed_member_count == 1
    assert all(
        store.get_table_ref(table_ref.table_ref_id).lifecycle_status
        == LifecycleStatus.RELEASED
        for table_ref in old_refs
    )


def test_large_manual_cleanup_limits_provider_work_per_request(
    tmp_path: Path,
) -> None:
    store, _lifecycle, _reader, publication_id, _latest_id, _table_ids, now = (
        seed_lifecycle_context(tmp_path, old_member_count=250)
    )
    provider = NoopCountingRuntimeProvider(tmp_path / "runtime-tables")
    service = make_cleanup_service(store, provider)

    result = service.cleanup(publication_id, max_table_refs=10, now=now)

    assert result.outcome == SharedPublicationCleanupOutcome.RETRY_PENDING
    assert result.processed_member_count == 10
    assert result.released_member_count == 10
    assert result.remaining_member_count == 11
    assert provider.drop_calls == 10


def test_cleanup_candidate_query_is_single_indexed_and_bounded(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    publication_rows = [
        {
            "publication_id": f"candidate-{index:05d}",
            "share_name": f"candidate-share-{index:05d}",
            "publication_version": 1,
            "producer_workflow_id": "workflow-candidate",
            "producer_run_id": "run-candidate",
            "status": "PUBLISHED",
            "input_snapshot_id": None,
            "retention_policy_json": '{"retention_seconds":1}',
            "created_at": "2026-07-10T00:00:00+00:00",
            "expires_at": "2026-07-10T00:00:01+00:00",
            "release_started_at": None,
            "cleanup_last_progress_at": None,
        }
        for index in range(10_000)
    ]
    publication_rows.append(
        {
            "publication_id": "candidate-no-retention",
            "share_name": "candidate-no-retention",
            "publication_version": 1,
            "producer_workflow_id": "workflow-candidate",
            "producer_run_id": "run-candidate",
            "status": "PUBLISHED",
            "input_snapshot_id": None,
            "retention_policy_json": "{}",
            "created_at": "2026-07-10T00:00:00+00:00",
            "expires_at": None,
            "release_started_at": None,
            "cleanup_last_progress_at": None,
        }
    )
    publication_rows.append(
        {
            "publication_id": "candidate-stale-releasing",
            "share_name": "candidate-stale-releasing",
            "publication_version": 1,
            "producer_workflow_id": "workflow-candidate",
            "producer_run_id": "run-candidate",
            "status": "RELEASING",
            "input_snapshot_id": None,
            "retention_policy_json": '{"retention_seconds":1}',
            "created_at": "2026-07-10T00:00:00+00:00",
            "expires_at": "2026-07-10T00:00:01+00:00",
            "release_started_at": "2026-07-10T00:00:02+00:00",
            "cleanup_last_progress_at": "2026-07-10T00:00:02+00:00",
        }
    )
    with store.engine.begin() as connection:
        connection.execute(insert(SharedPublicationRecord), publication_rows)
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
        candidates = store.list_shared_publication_cleanup_candidate_ids(
            now=datetime.fromisoformat("2026-07-12T00:00:00+00:00"),
            stale_before=datetime.fromisoformat("2026-07-11T00:00:00+00:00"),
            limit=25,
        )
    finally:
        event.remove(store.engine, "before_cursor_execute", count_selects)

    assert len(candidates) == 25
    assert "candidate-no-retention" not in candidates
    assert select_count == 1
    with store.engine.connect() as connection:
        query_plan = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT publication_id FROM ("
            "SELECT publication_id, expires_at AS candidate_at "
            "FROM shared_publications WHERE status = 'PUBLISHED' "
            "AND expires_at IS NOT NULL "
            "AND expires_at <= '2026-07-12T00:00:00+00:00' "
            "UNION ALL "
            "SELECT publication_id, cleanup_last_progress_at AS candidate_at "
            "FROM shared_publications WHERE status = 'RELEASING' "
            "AND cleanup_last_progress_at IS NOT NULL "
            "AND cleanup_last_progress_at <= '2026-07-11T00:00:00+00:00'"
            ") ORDER BY candidate_at, publication_id LIMIT 25"
        ).all()
    assert any(
        "idx_shared_publications_status_expires" in str(row[3])
        for row in query_plan
    )
    assert any(
        "idx_shared_publications_status_cleanup_progress" in str(row[3])
        for row in query_plan
    )


def test_manual_cleanup_rechecks_preview_and_blocks_active_lease(
    tmp_path: Path,
) -> None:
    store, provider, publication_id, old_refs, now = seed_cleanup_context(tmp_path)
    counting_provider = CountingRuntimeProvider(tmp_path / "runtime-tables")
    service = make_cleanup_service(store, counting_provider)
    preview = service.preview(publication_id, now=now)
    assert preview is not None
    assert preview.eligible is True
    lease = TableLeaseManager(store.engine).acquire_read_lease(
        table_ref_id=old_refs[0].table_ref_id,
        owner_id="manual-cleanup-blocker",
        ttl_seconds=300,
    )
    assert lease.granted is True

    result = service.cleanup(publication_id, now=now)

    assert result.outcome == SharedPublicationCleanupOutcome.BLOCKED
    assert SharedPublicationCleanupBlocker.ACTIVE_TABLE_LEASE in result.blockers
    assert counting_provider.drop_calls == 0
    publication = store.get_shared_publication(publication_id)
    assert publication is not None
    assert publication.status == "PUBLISHED"
    assert provider.read_rows(old_refs[0], offset=0, limit=1) == [{"value": 1}]


def test_manual_cleanup_does_not_drop_legacy_external_member(
    tmp_path: Path,
) -> None:
    store, _provider, publication_id, old_refs, now = seed_cleanup_context(tmp_path)
    counting_provider = CountingRuntimeProvider(tmp_path / "runtime-tables")
    with store.engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE data_refs SET storage_kind = 'EXTERNAL_SQL' "
                "WHERE table_ref_id = :table_ref_id"
            ),
            {"table_ref_id": old_refs[0].table_ref_id},
        )
    service = make_cleanup_service(store, counting_provider)

    result = service.cleanup(publication_id, now=now)

    assert result.outcome == SharedPublicationCleanupOutcome.BLOCKED
    assert SharedPublicationCleanupBlocker.MEMBER_NOT_RELEASABLE in result.blockers
    assert counting_provider.drop_calls == 0


def test_manual_cleanup_does_not_drop_member_referenced_by_other_publication(
    tmp_path: Path,
) -> None:
    store, provider, publication_id, old_refs, now = seed_cleanup_context(tmp_path)
    store.create_shared_publication(
        publication_id="publication-cleanup-other-reference",
        share_name="cleanup-other-reference",
        producer_workflow_id="workflow-cleanup-producer",
        producer_run_id="run-cleanup-producer",
        members={"shared": old_refs[0].table_ref_id},
        retention_policy={"retention_seconds": 1},
    )
    counting_provider = CountingRuntimeProvider(tmp_path / "runtime-tables")
    service = make_cleanup_service(store, counting_provider)

    result = service.cleanup(publication_id, now=now)

    assert result.outcome == SharedPublicationCleanupOutcome.BLOCKED
    assert (
        SharedPublicationCleanupBlocker.MEMBER_REFERENCED_BY_OTHER_PUBLICATION
        in result.blockers
    )
    assert counting_provider.drop_calls == 0
    assert provider.read_rows(old_refs[0], offset=0, limit=1) == [{"value": 1}]


def test_worker_recovers_stale_releasing_publication_after_restart(
    tmp_path: Path,
) -> None:
    store, provider, publication_id, _old_refs, now = seed_cleanup_context(tmp_path)
    failing_service = make_cleanup_service(
        store,
        FailOnceRuntimeProvider(tmp_path / "runtime-tables"),
    )
    first = failing_service.cleanup(publication_id, now=now)
    assert first.outcome == SharedPublicationCleanupOutcome.RETRY_PENDING
    with store.engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE shared_publications "
                "SET cleanup_last_progress_at = '2000-01-01T00:00:00+00:00' "
                "WHERE publication_id = :publication_id"
            ),
            {"publication_id": publication_id},
        )
    service = make_cleanup_service(store, provider)
    worker = SharedPublicationCleanupWorker(
        config=EngineConfig(
            data_dir=tmp_path,
            shared_publication_cleanup_enabled=True,
            shared_publication_cleanup_publication_batch_size=5,
            shared_publication_cleanup_table_ref_batch_size=5,
            shared_publication_cleanup_cycle_budget_seconds=2,
            shared_publication_releasing_stale_seconds=1,
        ),
        store=store,
        lifecycle_service=service,
    )

    cycle = worker.run_cycle()

    assert cycle.cleaned_count == 1
    publication = store.get_shared_publication(publication_id)
    assert publication is not None
    assert publication.status == "RELEASED"


def test_worker_respects_reader_lease_then_cleans_after_release(
    tmp_path: Path,
) -> None:
    store, _service, reader, publication_id, _latest_id, _table_ids, _now = (
        seed_lifecycle_context(tmp_path)
    )
    with store.engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE shared_publications "
                "SET expires_at = '2000-01-01T00:00:00+00:00' "
                "WHERE publication_id = :publication_id"
            ),
            {"publication_id": publication_id},
        )
    read = reader.read(
        consumer_workflow_run_id="run-lifecycle-consumer",
        share_name="lifecycle-share",
        version_policy=SharedTableVersionPolicy.EXACT_VERSION,
        exact_version=1,
        lease_expires_at=utc_now() + timedelta(minutes=5),
    )
    provider = NoopCountingRuntimeProvider(tmp_path / "runtime-tables")
    service = make_cleanup_service(store, provider)
    worker = SharedPublicationCleanupWorker(
        config=EngineConfig(
            data_dir=tmp_path,
            shared_publication_cleanup_enabled=True,
            shared_publication_cleanup_publication_batch_size=5,
            shared_publication_cleanup_table_ref_batch_size=5,
            shared_publication_cleanup_cycle_budget_seconds=2,
        ),
        store=store,
        lifecycle_service=service,
    )

    blocked_cycle = worker.run_cycle()
    store.release_read_lease(read.read_lease.lease_id)
    cleaned_cycle = worker.run_cycle()

    assert blocked_cycle.blocked_count >= 1
    assert cleaned_cycle.cleaned_count >= 1
    with pytest.raises(ValueError, match="Shared publication not found"):
        reader.read(
            consumer_workflow_run_id="run-lifecycle-consumer",
            share_name="lifecycle-share",
            version_policy=SharedTableVersionPolicy.EXACT_VERSION,
            exact_version=1,
            lease_expires_at=utc_now() + timedelta(minutes=5),
        )


def test_worker_never_cleans_latest_published_version(tmp_path: Path) -> None:
    store, provider, old_id, _old_refs, _now = seed_cleanup_context(tmp_path)
    with store.engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE shared_publications SET expires_at = NULL "
                "WHERE publication_id = :publication_id"
            ),
            {"publication_id": old_id},
        )
        connection.exec_driver_sql(
            "UPDATE shared_publications "
            "SET expires_at = '2000-01-01T00:00:00+00:00' "
            "WHERE publication_id = 'publication-cleanup-latest'"
        )
    service = make_cleanup_service(store, provider)
    worker = SharedPublicationCleanupWorker(
        config=EngineConfig(
            data_dir=tmp_path,
            shared_publication_cleanup_enabled=True,
            shared_publication_cleanup_publication_batch_size=5,
            shared_publication_cleanup_table_ref_batch_size=5,
            shared_publication_cleanup_cycle_budget_seconds=2,
        ),
        store=store,
        lifecycle_service=service,
    )

    cycle = worker.run_cycle()

    assert cycle.blocked_count == 1
    latest = store.get_shared_publication("publication-cleanup-latest")
    assert latest is not None
    assert latest.status == "PUBLISHED"


def test_shared_table_end_to_end_preserves_versions_cleanup_and_restart(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime-tables")
    producer_workflow = store.create_workflow_definition(
        name="Shared table end-to-end producer",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-shared-e2e-producer",
    )
    consumer_workflow = store.create_workflow_definition(
        name="Shared table end-to-end consumer",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-shared-e2e-consumer",
    )

    store.create_workflow_run(
        workflow_id=producer_workflow.workflow_id,
        workflow_run_id="run-shared-e2e-producer-v1",
        status=WorkflowRunStatus.SUCCEEDED,
    )
    store.create_node_run(
        workflow_run_id="run-shared-e2e-producer-v1",
        node_instance_id="source-v1",
        node_type="core.source",
        node_run_id="node-shared-e2e-producer-v1",
    )
    store.create_workflow_run(
        workflow_id=consumer_workflow.workflow_id,
        workflow_run_id="run-shared-e2e-consumer-v1",
    )
    table_v1 = register_runtime_table(
        store,
        provider,
        workflow_run_id="run-shared-e2e-producer-v1",
        node_run_id="node-shared-e2e-producer-v1",
        output_name="orders_v1",
        value=101,
    )
    publication_v1 = store.create_shared_publication(
        publication_id="publication-shared-e2e-v1",
        share_name="shared-e2e",
        producer_workflow_id=producer_workflow.workflow_id,
        producer_run_id="run-shared-e2e-producer-v1",
        members={"orders": table_v1.table_ref_id},
        retention_policy={"retention_seconds": 1},
    )
    registry = TableProviderRegistry()
    registry.register(provider, storage_kinds=(TableStorageKind.RUNTIME_SQL,))
    release_service = TableRefReleaseService(
        store=store,
        provider_registry=registry,
    )
    lifecycle_service = SharedPublicationLifecycleService(
        store,
        table_ref_release_service=release_service,
    )

    guarded_release = release_service.release(table_v1.table_ref_id)

    assert guarded_release.outcome == TableRefReleaseOutcome.SKIPPED
    assert guarded_release.reason == "shared_publication_active"
    assert provider.read_rows(table_v1, offset=0, limit=10) == [{"value": 101}]

    reader = SharedTableReader(store)
    read_v1 = reader.read(
        consumer_workflow_run_id="run-shared-e2e-consumer-v1",
        share_name="shared-e2e",
        version_policy=SharedTableVersionPolicy.LATEST,
        selected_members=("orders",),
        lease_expires_at=utc_now() + timedelta(minutes=5),
    )
    assert read_v1.publication.publication_id == publication_v1.publication_id
    assert read_v1.publication.publication_version == 1
    assert provider.read_rows(read_v1.table_refs[0], offset=0, limit=10) == [
        {"value": 101}
    ]

    store.create_workflow_run(
        workflow_id=producer_workflow.workflow_id,
        workflow_run_id="run-shared-e2e-producer-v2",
        status=WorkflowRunStatus.SUCCEEDED,
    )
    store.create_node_run(
        workflow_run_id="run-shared-e2e-producer-v2",
        node_instance_id="source-v2",
        node_type="core.source",
        node_run_id="node-shared-e2e-producer-v2",
    )
    table_v2 = register_runtime_table(
        store,
        provider,
        workflow_run_id="run-shared-e2e-producer-v2",
        node_run_id="node-shared-e2e-producer-v2",
        output_name="orders_v2",
        value=202,
    )
    publication_v2 = store.create_shared_publication(
        publication_id="publication-shared-e2e-v2",
        share_name="shared-e2e",
        producer_workflow_id=producer_workflow.workflow_id,
        producer_run_id="run-shared-e2e-producer-v2",
        members={"orders": table_v2.table_ref_id},
        retention_policy={"retention_seconds": 1},
    )
    store.create_workflow_run(
        workflow_id=consumer_workflow.workflow_id,
        workflow_run_id="run-shared-e2e-consumer-v2",
    )
    read_v2 = reader.read(
        consumer_workflow_run_id="run-shared-e2e-consumer-v2",
        share_name="shared-e2e",
        version_policy=SharedTableVersionPolicy.LATEST,
        selected_members=("orders",),
        lease_expires_at=utc_now() + timedelta(minutes=5),
    )

    assert publication_v2.publication_version == 2
    assert read_v1.publication.publication_id == publication_v1.publication_id
    assert read_v1.input_snapshot.inputs[0].publication_version == 1
    assert provider.read_rows(read_v1.table_refs[0], offset=0, limit=10) == [
        {"value": 101}
    ]
    assert read_v2.publication.publication_id == publication_v2.publication_id
    assert provider.read_rows(read_v2.table_refs[0], offset=0, limit=10) == [
        {"value": 202}
    ]

    evaluated_at = publication_v2.created_at + timedelta(seconds=2)
    blocked_preview = lifecycle_service.preview(
        publication_v1.publication_id,
        now=evaluated_at,
    )
    assert blocked_preview is not None
    assert blocked_preview.eligible is False
    assert (
        SharedPublicationCleanupBlocker.ACTIVE_READ_LEASE
        in blocked_preview.blockers
    )

    store.release_read_lease(read_v1.read_lease.lease_id)
    store.release_read_lease(read_v2.read_lease.lease_id)
    eligible_preview = lifecycle_service.preview(
        publication_v1.publication_id,
        now=evaluated_at,
    )
    assert eligible_preview is not None
    assert eligible_preview.eligible is True
    assert eligible_preview.blockers == ()

    cleanup_result = lifecycle_service.cleanup(
        publication_v1.publication_id,
        now=evaluated_at,
    )

    assert cleanup_result.outcome == SharedPublicationCleanupOutcome.CLEANED
    released_v1 = store.get_shared_publication(publication_v1.publication_id)
    current_v2 = store.get_shared_publication(publication_v2.publication_id)
    assert released_v1 is not None
    assert released_v1.status == "RELEASED"
    assert [member.table_ref_id for member in released_v1.members] == [
        table_v1.table_ref_id
    ]
    assert current_v2 is not None
    assert current_v2.status == "PUBLISHED"
    assert store.get_latest_shared_publication("shared-e2e") == current_v2
    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        provider.read_rows(table_v1, offset=0, limit=10)
    assert provider.read_rows(table_v2, offset=0, limit=10) == [{"value": 202}]

    store.dispose()
    reopened_store = RuntimeStore.from_sqlite_path(database_path)
    reopened_store.create_workflow_run(
        workflow_id=consumer_workflow.workflow_id,
        workflow_run_id="run-shared-e2e-consumer-restarted",
    )
    reopened_v1 = reopened_store.get_shared_publication(
        publication_v1.publication_id
    )
    reopened_v2 = reopened_store.get_shared_publication(
        publication_v2.publication_id
    )
    assert reopened_v1 is not None
    assert reopened_v1.status == "RELEASED"
    assert reopened_v2 is not None
    assert reopened_v2.status == "PUBLISHED"
    assert (
        reopened_store.get_latest_shared_publication("shared-e2e") == reopened_v2
    )

    restarted_read = SharedTableReader(reopened_store).read(
        consumer_workflow_run_id="run-shared-e2e-consumer-restarted",
        share_name="shared-e2e",
        version_policy=SharedTableVersionPolicy.LATEST,
        selected_members=("orders",),
        lease_expires_at=utc_now() + timedelta(minutes=5),
    )
    assert restarted_read.publication.publication_id == publication_v2.publication_id
    assert provider.read_rows(restarted_read.table_refs[0], offset=0, limit=10) == [
        {"value": 202}
    ]
    assert (
        make_cleanup_service(reopened_store, provider)
        .cleanup(publication_v1.publication_id)
        .outcome
        == SharedPublicationCleanupOutcome.ALREADY_RELEASED
    )
    reopened_store.release_read_lease(restarted_read.read_lease.lease_id)
    reopened_store.dispose()
