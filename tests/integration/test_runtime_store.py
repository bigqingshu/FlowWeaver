from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.protocols.enums import (
    LifecycleStatus,
    NodeRunStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
    WorkflowRunStatus,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def alembic_config(database_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    return config


def migrate(database_path: Path) -> None:
    command.upgrade(alembic_config(database_path), "head")


def table_names(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {row[0] for row in rows}


def test_alembic_migration_creates_required_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"

    migrate(database_path)

    assert {
        "workflow_definitions",
        "workflows",
        "workflow_revisions",
        "workflow_runs",
        "node_runs",
        "data_refs",
        "shared_publications",
        "shared_publication_members",
        "input_snapshots",
        "read_leases",
        "table_leases",
        "workflow_processes",
        "audit_events",
        "runtime_events",
    }.issubset(table_names(database_path))


def test_alembic_migration_is_repeatable(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"

    migrate(database_path)
    migrate(database_path)

    assert "workflow_definitions" in table_names(database_path)


def test_runtime_store_workflow_definition_crud(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)

    created = store.create_workflow_definition(
        name="Smoke workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    loaded = store.get_workflow_definition(created.workflow_id)
    updated = store.update_workflow_definition(
        created.workflow_id,
        definition={
            "schema_version": "1.0",
            "nodes": [],
            "connections": [],
            "outputs": [],
        },
    )

    assert loaded is not None
    assert loaded.name == "Smoke workflow"
    assert loaded.revision_id == created.revision_id
    assert loaded.definition == {
        "schema_version": "1.0",
        "nodes": [],
        "connections": [],
    }
    assert updated is not None
    assert updated.version == 2
    assert updated.revision_id != created.revision_id
    assert updated.definition["outputs"] == []
    revisions = store.list_workflow_revisions("workflow-1")
    assert [revision.version for revision in revisions] == [1, 2]
    assert revisions[0].definition == created.definition
    assert [item.workflow_id for item in store.list_workflow_definitions()] == [
        "workflow-1"
    ]


def test_runtime_store_workflow_run_crud(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)

    definition = store.create_workflow_definition(
        name="Run workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    created = store.create_workflow_run(
        workflow_id=definition.workflow_id,
        workflow_run_id="run-1",
        status=WorkflowRunStatus.PENDING,
        started_at=utc_now(),
    )
    updated = store.update_workflow_run_status(
        created.workflow_run_id,
        WorkflowRunStatus.SUCCEEDED,
        finished_at=utc_now(),
    )

    assert store.get_workflow_run(created.workflow_run_id) is not None
    assert created.revision_id == definition.revision_id
    assert created.definition_hash == definition.definition_hash
    assert updated is not None
    assert updated.status == WorkflowRunStatus.SUCCEEDED.value
    assert updated.state_version == 1
    assert store.list_workflow_runs(workflow_id=definition.workflow_id)[
        0
    ].workflow_run_id == "run-1"
    assert store.list_workflow_runs(statuses=[WorkflowRunStatus.SUCCEEDED])[
        0
    ].workflow_run_id == "run-1"


def test_runtime_store_rejects_stale_workflow_run_state(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Run workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )

    first = store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.SUCCEEDED,
        expected_state_version=0,
    )
    stale = store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.FAILED,
        expected_state_version=0,
    )

    assert first is not None
    assert first.state_version == 1
    assert stale is None
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"


def test_runtime_store_rejects_stale_node_run_terminal_update(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Node workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="node-1",
        node_type="core.test",
        node_run_id="node-run-1",
    )

    timed_out = store.update_node_run_status(
        node.node_run_id,
        NodeRunStatus.TIMED_OUT,
        expected_state_version=0,
    )
    stale_success = store.update_node_run_status(
        node.node_run_id,
        NodeRunStatus.SUCCEEDED,
        expected_state_version=0,
    )
    illegal_success = store.update_node_run_status(
        node.node_run_id,
        NodeRunStatus.SUCCEEDED,
        expected_state_version=1,
    )

    assert timed_out is not None
    assert timed_out.state_version == 1
    assert stale_success is None
    assert illegal_success is None
    loaded = store.get_node_run(node.node_run_id)
    assert loaded is not None
    assert loaded.status == NodeRunStatus.TIMED_OUT.value


def test_runtime_store_marks_stale_workflow_process_lost(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Process workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(workflow_id=workflow.workflow_id)
    process = store.create_workflow_process(workflow_run_id=run.workflow_run_id)
    store.record_workflow_process_heartbeat(process.process_id)

    lost = store.mark_lost_workflow_processes(
        stale_before=utc_now() + timedelta(seconds=1)
    )

    assert [item.process_id for item in lost] == [process.process_id]
    loaded = store.get_workflow_process(process.process_id)
    assert loaded is not None
    assert loaded.status == "LOST"


def test_sqlite_pragmas_enable_foreign_keys_and_wal(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)

    with store.engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 5000
        journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
        assert journal_mode.lower() == "wal"

    with pytest.raises(ValueError):
        store.create_workflow_run(
            workflow_id="missing",
            workflow_run_id="run-1",
        )


def test_runtime_store_table_ref_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    table_ref = TableRefModel(
        table_ref_id="table-1",
        role=TableRole.CURRENT,
        storage_kind=TableStorageKind.RUNTIME_SQL,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.PUBLISHED_IMMUTABLE,
        provider_id="sqlite_runtime",
        resource_profile_id="profile-1",
        mount_id="mount-1",
        logical_table_id="orders",
        opaque_handle={"database_path": "runtime/run.db", "table_name": "orders_v1"},
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

    store.register_table_ref(table_ref)
    loaded = store.get_table_ref("table-1")

    assert loaded == table_ref


def test_runtime_event_sequence_numbers_are_persisted(tmp_path: Path) -> None:
    from flowweaver.protocols.enums import EventType
    from flowweaver.protocols.events import EventModel

    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)

    first = store.append_runtime_event(
        EventModel(event_type=EventType.ENGINE_READY, payload={})
    )
    second = store.append_runtime_event(
        EventModel(event_type=EventType.WORKFLOW_STARTED, payload={"run": "1"})
    )

    assert (first, second) == (1, 2)
