from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

from workflow_platform.common.time import utc_now
from workflow_platform.engine.runtime_store import RuntimeStore, sqlite_url
from workflow_platform.protocols.enums import WorkflowRunStatus


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
        "workflow_runs",
        "node_runs",
        "data_refs",
        "shared_publications",
        "shared_publication_members",
        "input_snapshots",
        "read_leases",
        "audit_events",
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
        definition={"nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    loaded = store.get_workflow_definition(created.workflow_id)
    updated = store.update_workflow_definition(
        created.workflow_id,
        definition={"nodes": [{"id": "n1"}], "connections": []},
    )

    assert loaded is not None
    assert loaded.name == "Smoke workflow"
    assert loaded.definition == {"nodes": [], "connections": []}
    assert updated is not None
    assert updated.version == 2
    assert updated.definition["nodes"] == [{"id": "n1"}]
    assert [item.workflow_id for item in store.list_workflow_definitions()] == [
        "workflow-1"
    ]


def test_runtime_store_workflow_run_crud(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)

    definition = store.create_workflow_definition(
        name="Run workflow",
        definition={"nodes": []},
        workflow_id="workflow-1",
    )
    created = store.create_workflow_run(
        workflow_id=definition.workflow_id,
        workflow_version=definition.version,
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
    assert updated is not None
    assert updated.status == WorkflowRunStatus.SUCCEEDED.value
    assert store.list_workflow_runs(workflow_id=definition.workflow_id)[
        0
    ].workflow_run_id == "run-1"
    assert store.list_workflow_runs(statuses=[WorkflowRunStatus.SUCCEEDED])[
        0
    ].workflow_run_id == "run-1"
