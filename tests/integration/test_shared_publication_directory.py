from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import event, insert, inspect

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
)
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")
    return RuntimeStore.from_sqlite_path(database_path)


def seed_publications(store: RuntimeStore) -> None:
    workflow = store.create_workflow_definition(
        name="Publication directory",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-directory",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-directory",
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
        node_type="core.source",
        node_run_id="node-directory",
    )
    table_ref = TableRefModel(
        table_ref_id="table-directory",
        role=TableRole.CURRENT,
        storage_kind=TableStorageKind.RUNTIME_SQL,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.PUBLISHED_IMMUTABLE,
        provider_id="sqlite_runtime",
        resource_profile_id=None,
        mount_id=None,
        logical_table_id="orders",
        opaque_handle={
            "database_path": "runtime/run-directory.db",
            "table_name": "orders_v1",
        },
        schema=[
            FieldSchemaModel(
                field_id="orders-row-id",
                name="row_id",
                data_type="INTEGER",
                nullable=False,
                ordinal=0,
            )
        ],
        schema_fingerprint="orders-v1",
        version=1,
        capabilities={"READ"},
        lifecycle_status=LifecycleStatus.PUBLISHED,
        created_by_workflow_run_id=run.workflow_run_id,
        created_by_node_run_id=node.node_run_id,
        created_at=utc_now(),
    )
    store.register_table_ref(table_ref)
    for share_index in range(20):
        for version_index in range(5):
            store.create_shared_publication(
                publication_id=f"publication-{share_index}-{version_index}",
                share_name=f"share-{share_index:02d}",
                producer_workflow_id=workflow.workflow_id,
                producer_run_id=run.workflow_run_id,
                members={"orders": table_ref.table_ref_id},
            )


def test_shared_publication_directory_queries_are_fixed_and_paged(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    seed_publications(store)
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
        publications = store.list_shared_publications(limit=1000)
        assert len(publications) == 100
        assert select_count == 2

        select_count = 0
        catalog = store.list_shared_publication_catalog(offset=5, limit=5)
        assert [item.share_name for item in catalog] == [
            "share-05",
            "share-06",
            "share-07",
            "share-08",
            "share-09",
        ]
        assert all(item.latest_published_version == 5 for item in catalog)
        assert all(item.published_version_count == 5 for item in catalog)
        assert all(item.latest_member_count == 1 for item in catalog)
        assert select_count == 3

        select_count = 0
        summaries = store.list_shared_publication_summaries(
            share_name="share-00",
            offset=1,
            limit=2,
        )
        assert [item.publication_version for item in summaries] == [4, 3]
        assert all(item.member_count == 1 for item in summaries)
        assert all(item.is_latest_published is False for item in summaries)
        assert select_count == 3

        select_count = 0
        members = store.list_shared_publication_members(
            publication_id="publication-0-0",
            offset=0,
            limit=10,
        )
        assert [item.export_name for item in members] == ["orders"]
        assert select_count == 1
    finally:
        event.remove(store.engine, "before_cursor_execute", count_selects)


def test_shared_publication_directory_indexes_are_migrated(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    inspector = inspect(store.engine)

    publication_indexes = {
        item["name"] for item in inspector.get_indexes("shared_publications")
    }
    member_indexes = {
        item["name"] for item in inspector.get_indexes("shared_publication_members")
    }

    assert "idx_shared_publications_catalog" in publication_indexes
    assert "idx_shared_publication_members_publication_export" in member_indexes
    assert "idx_shared_publication_members_table_ref" in member_indexes


def test_shared_publication_member_summary_reports_released_table_ref(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    seed_publications(store)

    released = store.mark_table_ref_released("table-directory")
    members = store.list_shared_publication_members(
        publication_id="publication-0-0",
        offset=0,
        limit=10,
    )

    assert released.lifecycle_status == LifecycleStatus.RELEASED
    assert len(members) == 1
    assert members[0].table_ref_lifecycle_status == "RELEASED"
    assert members[0].table_ref_storage_kind == "RUNTIME_SQL"
    assert members[0].logical_table_id == "orders"
    assert members[0].can_read_rows is False


def test_large_shared_publication_directory_stays_indexed_and_bounded(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    seed_publications(store)
    publication_rows: list[dict[str, object]] = []
    member_rows: list[dict[str, object]] = []
    for share_index in range(1000):
        share_name = f"large-share-{share_index:04d}"
        for version_index in range(10):
            publication_id = f"large-publication-{share_index:04d}-{version_index:02d}"
            publication_rows.append(
                {
                    "publication_id": publication_id,
                    "share_name": share_name,
                    "publication_version": version_index + 1,
                    "producer_workflow_id": "workflow-directory",
                    "producer_run_id": "run-directory",
                    "status": "PUBLISHED",
                    "input_snapshot_id": None,
                    "retention_policy_json": "{}",
                    "created_at": "2026-07-11T00:00:00+00:00",
                }
            )
            for export_name in ("orders", "orders_copy"):
                member_rows.append(
                    {
                        "publication_id": publication_id,
                        "export_name": export_name,
                        "table_ref_id": "table-directory",
                        "exact_table_version": 1,
                    }
                )

    with store.engine.begin() as connection:
        connection.execute(insert(SharedPublicationRecord), publication_rows)
        connection.execute(insert(SharedPublicationMemberRecord), member_rows)

    catalog = store.list_shared_publication_catalog(
        query="large-share",
        offset=0,
        limit=20,
    )
    assert len(catalog) == 20
    assert all(item.published_version_count == 10 for item in catalog)
    assert all(item.latest_member_count == 2 for item in catalog)

    summaries = store.list_shared_publication_summaries(
        share_name="large-share-0000",
        offset=0,
        limit=3,
    )
    assert len(summaries) == 3
    assert [item.publication_version for item in summaries] == [10, 9, 8]
    assert all(item.member_count == 2 for item in summaries)
    assert all(not hasattr(item, "members") for item in summaries)

    members = store.list_shared_publication_members(
        publication_id="large-publication-0000-00",
        offset=1,
        limit=1,
    )
    assert [item.export_name for item in members] == ["orders_copy"]

    with store.engine.connect() as connection:
        catalog_plan = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN "
            "SELECT DISTINCT share_name FROM shared_publications "
            "WHERE status = 'PUBLISHED' ORDER BY share_name LIMIT 20 OFFSET 0"
        ).all()
        member_plan = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN "
            "SELECT publication_id, export_name FROM shared_publication_members "
            "WHERE publication_id = 'large-publication-0000-00' "
            "ORDER BY export_name LIMIT 1"
        ).all()

    assert any(
        "idx_shared_publications_catalog" in str(row[3]) for row in catalog_plan
    )
    assert any(
        "idx_shared_publication_members_publication_export" in str(row[3])
        or "sqlite_autoindex_shared_publication_members" in str(row[3])
        for row in member_plan
    )
