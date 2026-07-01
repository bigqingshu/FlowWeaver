from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import (
    InputSnapshotEntry,
    NodeRun,
    RuntimeStore,
    WorkflowRun,
    sqlite_url,
)
from flowweaver.protocols.enums import (
    AuditLevel,
    LifecycleStatus,
    NodeResultStatus,
    NodeRunStatus,
    PermissionAction,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
    WorkflowRunCompletionReason,
    WorkflowRunStatus,
)
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.permissions import (
    AuditEventModel,
    PermissionGrantModel,
    PermissionScopeModel,
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


def foreign_keys(database_path: Path, table_name: str) -> set[tuple[str, str, str]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
    return {(row[3], row[2], row[4]) for row in rows}


def indexes(database_path: Path, table_name: str) -> dict[str, list[str]]:
    with sqlite3.connect(database_path) as connection:
        index_rows = connection.execute(f"PRAGMA index_list({table_name})").fetchall()
        result = {}
        for index_row in index_rows:
            index_name = index_row[1]
            column_rows = connection.execute(
                f"PRAGMA index_info({index_name})"
            ).fetchall()
            result[index_name] = [column_row[2] for column_row in column_rows]
    return result


def column_names(database_path: Path, table_name: str) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def row_count(database_path: Path, table_name: str) -> int:
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
    mutability: TableMutability = TableMutability.PUBLISHED_IMMUTABLE,
    lifecycle_status: LifecycleStatus = LifecycleStatus.PUBLISHED,
) -> TableRefModel:
    return TableRefModel(
        table_ref_id=table_ref_id,
        role=TableRole.CURRENT,
        storage_kind=TableStorageKind.RUNTIME_SQL,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=mutability,
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
        lifecycle_status=lifecycle_status,
        created_by_workflow_run_id=workflow_run_id,
        created_by_node_run_id=node_run_id,
        created_at=utc_now(),
    )


def create_producer_context(
    store: RuntimeStore,
    *,
    workflow_id: str = "workflow-1",
    workflow_run_id: str = "run-1",
    node_run_id: str = "node-1",
) -> tuple[WorkflowRun, NodeRun]:
    workflow = store.create_workflow_definition(
        name=f"Producer workflow {workflow_id}",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id=workflow_id,
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id=workflow_run_id,
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id=f"{workflow_id}-producer-node",
        node_type="builtin.producer",
        node_run_id=node_run_id,
    )
    return run, node


def test_alembic_migration_creates_required_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"

    migrate(database_path)

    assert {
        "workflow_definitions",
        "workflows",
        "workflow_revisions",
        "workflow_runs",
        "node_runs",
        "node_tasks",
        "node_task_results",
        "data_refs",
        "shared_publications",
        "shared_publication_members",
        "input_snapshots",
        "read_leases",
        "table_leases",
        "permission_grants",
        "workflow_processes",
        "audit_events",
        "runtime_events",
    }.issubset(table_names(database_path))


def test_shared_publication_prerequisite_schema_is_available(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"

    migrate(database_path)

    assert column_names(database_path, "shared_publications") == {
        "publication_id",
        "share_name",
        "publication_version",
        "producer_workflow_id",
        "producer_run_id",
        "status",
        "input_snapshot_id",
        "retention_policy_json",
        "created_at",
    }
    assert column_names(database_path, "shared_publication_members") == {
        "publication_id",
        "export_name",
        "table_ref_id",
        "exact_table_version",
    }
    assert column_names(database_path, "input_snapshots") == {
        "input_snapshot_id",
        "workflow_run_id",
        "snapshot_json",
        "created_at",
    }
    assert column_names(database_path, "read_leases") == {
        "lease_id",
        "publication_id",
        "publication_version",
        "consumer_workflow_run_id",
        "selected_members_json",
        "acquired_at",
        "expires_at",
        "released_at",
    }
    assert column_names(database_path, "permission_grants") == {
        "permission_handle_id",
        "request_id",
        "workflow_run_id",
        "node_run_id",
        "scopes_json",
        "granted",
        "issued_at",
        "expires_at",
        "revoked_at",
        "denial_reason",
        "audit_level",
    }
    assert "audit_level" in column_names(database_path, "audit_events")
    assert {
        ("publication_id", "shared_publications", "publication_id"),
        ("table_ref_id", "data_refs", "table_ref_id"),
    }.issubset(foreign_keys(database_path, "shared_publication_members"))
    assert ["share_name", "publication_version"] in indexes(
        database_path,
        "shared_publications",
    ).values()


def test_workflow_run_foreign_keys_target_canonical_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"

    migrate(database_path)

    assert {
        ("workflow_id", "workflows", "workflow_id"),
        ("revision_id", "workflow_revisions", "revision_id"),
    }.issubset(foreign_keys(database_path, "workflow_runs"))


def test_runtime_store_permission_grant_and_audit_event_round_trip(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    run, node = create_producer_context(store)
    scope = PermissionScopeModel(
        action=PermissionAction.WRITE_FIELDS,
        resource_type="TABLE_REF",
        resource_id="table-1",
        fields=["amount"],
        write_mode="OVERWRITE",
        constraints={"max_rows": 10},
    )
    grant = PermissionGrantModel(
        permission_handle_id="permission-handle-1",
        request_id="permission-request-1",
        workflow_run_id=run.workflow_run_id,
        node_run_id=node.node_run_id,
        scopes=[scope],
        granted=True,
    )

    created = store.create_permission_grant(grant)

    assert created == grant
    assert store.get_permission_grant(grant.permission_handle_id) == grant
    assert store.list_permission_grants_by_workflow_run(
        run.workflow_run_id,
        active_only=True,
    ) == [grant]

    revoked = store.revoke_permission_grant(grant.permission_handle_id)

    assert revoked is not None
    assert revoked.revoked_at is not None
    assert store.get_permission_grant(grant.permission_handle_id) == revoked
    assert store.list_permission_grants_by_workflow_run(
        run.workflow_run_id,
        active_only=True,
    ) == []

    audit_event = AuditEventModel(
        event_id="audit-event-1",
        event_type="PERMISSION_CHECK",
        workflow_run_id=run.workflow_run_id,
        node_run_id=node.node_run_id,
        subject_type="NODE",
        subject_id=node.node_run_id,
        resource_type="TABLE_REF",
        resource_id="table-1",
        action=PermissionAction.WRITE_FIELDS,
        result="granted",
        audit_level=AuditLevel.STANDARD,
        summary={
            "fields": ["amount"],
            "affected_rows": 3,
            "change_set_summary": {"updated": 3},
        },
    )

    appended = store.append_audit_event(audit_event)

    assert appended == audit_event
    assert store.get_audit_event(audit_event.event_id) == audit_event
    assert store.list_audit_events(workflow_run_id=run.workflow_run_id) == [
        audit_event
    ]
    assert store.list_audit_events(node_run_id=node.node_run_id) == [audit_event]
    assert store.list_audit_events(event_type="PERMISSION_CHECK") == [audit_event]
    assert store.list_audit_events(event_type="TABLE_LEASE") == []


def test_workflow_run_completion_reason_column_is_available(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"

    migrate(database_path)

    assert "completion_reason" in column_names(database_path, "workflow_runs")


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
        WorkflowRunStatus.RUNNING,
        expected_state_version=created.state_version,
    )
    assert updated is not None
    updated = store.update_workflow_run_status(
        created.workflow_run_id,
        WorkflowRunStatus.SUCCEEDED,
        finished_at=utc_now(),
        expected_state_version=updated.state_version,
    )

    assert store.get_workflow_run(created.workflow_run_id) is not None
    assert created.revision_id == definition.revision_id
    assert created.definition_hash == definition.definition_hash
    assert updated is not None
    assert updated.status == WorkflowRunStatus.SUCCEEDED.value
    assert updated.state_version == 2
    assert updated.completion_reason is None
    assert store.list_workflow_runs(workflow_id=definition.workflow_id)[
        0
    ].workflow_run_id == "run-1"
    assert store.list_workflow_runs(statuses=[WorkflowRunStatus.SUCCEEDED])[
        0
    ].workflow_run_id == "run-1"


def test_runtime_store_persists_workflow_run_completion_reason(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Partial failure workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    running = store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        expected_state_version=run.state_version,
    )
    assert running is not None

    failed = store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.FAILED,
        finished_at=utc_now(),
        completion_reason=WorkflowRunCompletionReason.PARTIAL_FAILURE,
        expected_state_version=running.state_version,
    )

    loaded = store.get_workflow_run(run.workflow_run_id)
    listed = store.list_workflow_runs(statuses=[WorkflowRunStatus.FAILED])
    assert failed is not None
    assert failed.completion_reason == "PARTIAL_FAILURE"
    assert loaded is not None
    assert loaded.completion_reason == "PARTIAL_FAILURE"
    assert listed[0].completion_reason == "PARTIAL_FAILURE"


def test_runtime_store_rejects_workflow_run_revision_mismatch(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    first = store.create_workflow_definition(
        name="First workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    second = store.create_workflow_definition(
        name="Second workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-2",
    )

    with pytest.raises(ValueError, match="does not belong"):
        store.create_workflow_run(
            workflow_id=first.workflow_id,
            revision_id=second.revision_id,
        )


def test_runtime_store_rejects_explicit_workflow_run_version(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Version workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )

    with pytest.raises(ValueError, match="derived from revision"):
        store.create_workflow_run(
            workflow_id=workflow.workflow_id,
            workflow_version=99,
        )


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
        WorkflowRunStatus.RUNNING,
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
    assert store.get_workflow_run(run.workflow_run_id).status == "RUNNING"


def test_runtime_store_workflow_run_cas_allows_only_one_writer(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    first_store = RuntimeStore.from_sqlite_path(database_path)
    second_store = RuntimeStore.from_sqlite_path(database_path)
    workflow = first_store.create_workflow_definition(
        name="CAS workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = first_store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )

    first = first_store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        expected_state_version=0,
        allowed_source_statuses=[WorkflowRunStatus.PENDING],
    )
    stale = second_store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.CANCELLED,
        expected_state_version=0,
        allowed_source_statuses=[WorkflowRunStatus.PENDING],
    )

    assert first is not None
    assert first.state_version == 1
    assert stale is None
    assert first_store.get_workflow_run(run.workflow_run_id).status == "RUNNING"


@pytest.mark.parametrize(
    "terminal_status",
    [
        WorkflowRunStatus.CANCELLED,
        WorkflowRunStatus.FAILED,
        WorkflowRunStatus.ABORTED,
    ],
)
def test_runtime_store_rejects_workflow_run_terminal_revival(
    tmp_path: Path,
    terminal_status: WorkflowRunStatus,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Terminal workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    running = store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        expected_state_version=0,
        allowed_source_statuses=[WorkflowRunStatus.PENDING],
    )
    assert running is not None
    terminal = store.update_workflow_run_status(
        run.workflow_run_id,
        terminal_status,
        expected_state_version=running.state_version,
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
    )
    assert terminal is not None

    revived = store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.SUCCEEDED,
        expected_state_version=terminal.state_version,
        allowed_source_statuses=[terminal_status],
    )

    assert revived is None
    assert store.get_workflow_run(run.workflow_run_id).status == terminal_status.value


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
        status=NodeRunStatus.RUNNING,
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


def test_runtime_store_rejects_illegal_node_success_source(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Node transition workflow",
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
        status=NodeRunStatus.READY,
    )

    illegal_success = store.update_node_run_status(
        node.node_run_id,
        NodeRunStatus.SUCCEEDED,
        expected_state_version=node.state_version,
    )

    assert illegal_success is None
    assert store.get_node_run(node.node_run_id).status == NodeRunStatus.READY.value


def test_runtime_store_allows_waiting_node_to_be_skipped_as_terminal(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Skip node workflow",
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
        status=NodeRunStatus.WAITING_DEPENDENCY,
    )

    skipped = store.update_node_run_status(
        node.node_run_id,
        NodeRunStatus.SKIPPED,
        expected_state_version=node.state_version,
    )
    revived = store.update_node_run_status(
        node.node_run_id,
        NodeRunStatus.READY,
        expected_state_version=skipped.state_version if skipped is not None else 1,
    )

    assert skipped is not None
    assert skipped.status == NodeRunStatus.SKIPPED.value
    assert revived is None
    assert store.get_node_run(node.node_run_id).status == NodeRunStatus.SKIPPED.value


def test_runtime_store_node_run_cas_allows_only_one_writer(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    first_store = RuntimeStore.from_sqlite_path(database_path)
    second_store = RuntimeStore.from_sqlite_path(database_path)
    workflow = first_store.create_workflow_definition(
        name="Node CAS workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = first_store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    node = first_store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="node-1",
        node_type="core.test",
        node_run_id="node-run-1",
        status=NodeRunStatus.WAITING_DEPENDENCY,
    )

    first = first_store.update_node_run_status(
        node.node_run_id,
        NodeRunStatus.READY,
        expected_state_version=0,
        allowed_source_statuses=[NodeRunStatus.WAITING_DEPENDENCY],
    )
    stale = second_store.update_node_run_status(
        node.node_run_id,
        NodeRunStatus.CANCELLED,
        expected_state_version=0,
        allowed_source_statuses=[NodeRunStatus.WAITING_DEPENDENCY],
    )

    assert first is not None
    assert first.state_version == 1
    assert stale is None
    assert first_store.get_node_run(node.node_run_id).status == "READY"


def test_runtime_store_records_node_task_result_and_terminal_node_atomically(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Atomic node result workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.create_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="node-1",
        node_type="core.test",
        node_run_id="node-run-1",
        status=NodeRunStatus.RUNNING,
        executor_id="executor-1",
    )
    task = NodeTaskModel(
        task_id="task-1",
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_run_id=node.node_run_id,
        node_instance_id=node.node_instance_id,
        node_type=node.node_type,
        node_version="1.0",
        attempt=node.attempt,
        input_refs=[],
        config={},
        timeout_seconds=60,
    )
    result = NodeTaskResultModel(
        result_id="result-1",
        task_id=task.task_id,
        node_run_id=node.node_run_id,
        attempt=node.attempt,
        executor_id="executor-1",
        process_generation=process.process_generation,
        status=NodeResultStatus.SUCCEEDED,
        output_refs=["table-1"],
    )
    store.create_node_task(task)

    updated = store.record_node_task_result_and_update_node_run_status(
        result,
        NodeRunStatus.SUCCEEDED,
        finished_at=result.finished_at,
        expected_state_version=node.state_version,
        allowed_source_statuses=[NodeRunStatus.RUNNING],
    )

    assert updated is not None
    assert updated.status == NodeRunStatus.SUCCEEDED.value
    assert updated.state_version == node.state_version + 1
    assert store.get_node_task_result(
        task_id=result.task_id,
        result_id=result.result_id,
    ) == result


def test_runtime_store_records_cancelled_result_from_cancel_requested_node(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Atomic cancel result workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.create_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="node-1",
        node_type="core.test",
        node_run_id="node-run-1",
        status=NodeRunStatus.CANCEL_REQUESTED,
        executor_id="executor-1",
    )
    task = NodeTaskModel(
        task_id="task-1",
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_run_id=node.node_run_id,
        node_instance_id=node.node_instance_id,
        node_type=node.node_type,
        node_version="1.0",
        attempt=node.attempt,
        input_refs=[],
        config={},
        timeout_seconds=60,
    )
    result = NodeTaskResultModel(
        result_id="cancel-result-1",
        task_id=task.task_id,
        node_run_id=node.node_run_id,
        attempt=node.attempt,
        executor_id="executor-1",
        process_generation=process.process_generation,
        status=NodeResultStatus.CANCELLED,
        error={"message": "cancelled"},
    )
    store.create_node_task(task)

    updated = store.record_node_task_result_and_update_node_run_status(
        result,
        NodeRunStatus.CANCELLED,
        finished_at=result.finished_at,
        error=result.error,
        expected_state_version=node.state_version,
        allowed_source_statuses=[NodeRunStatus.CANCEL_REQUESTED],
    )

    assert updated is not None
    assert updated.status == NodeRunStatus.CANCELLED.value
    assert store.get_node_task_result(
        task_id=result.task_id,
        result_id=result.result_id,
    ) == result


def test_runtime_store_rolls_back_node_task_result_when_terminal_update_rejected(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Atomic rollback workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.create_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="node-1",
        node_type="core.test",
        node_run_id="node-run-1",
        status=NodeRunStatus.RUNNING,
        executor_id="executor-1",
    )
    task = NodeTaskModel(
        task_id="task-1",
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        node_run_id=node.node_run_id,
        node_instance_id=node.node_instance_id,
        node_type=node.node_type,
        node_version="1.0",
        attempt=node.attempt,
        input_refs=[],
        config={},
        timeout_seconds=60,
    )
    result = NodeTaskResultModel(
        result_id="result-1",
        task_id=task.task_id,
        node_run_id=node.node_run_id,
        attempt=node.attempt,
        executor_id="executor-1",
        process_generation=process.process_generation,
        status=NodeResultStatus.SUCCEEDED,
    )
    store.create_node_task(task)
    failed = store.update_node_run_status(
        node.node_run_id,
        NodeRunStatus.FAILED,
        expected_state_version=node.state_version,
    )
    assert failed is not None

    rejected = store.record_node_task_result_and_update_node_run_status(
        result,
        NodeRunStatus.SUCCEEDED,
        finished_at=result.finished_at,
        expected_state_version=node.state_version,
        allowed_source_statuses=[NodeRunStatus.RUNNING],
    )

    assert rejected is None
    assert store.get_node_task_result(
        task_id=result.task_id,
        result_id=result.result_id,
    ) is None
    loaded_node = store.get_node_run(node.node_run_id)
    assert loaded_node is not None
    assert loaded_node.status == NodeRunStatus.FAILED.value
    assert loaded_node.state_version == failed.state_version


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


def test_runtime_store_marks_workflow_process_lost_at_cutoff_boundary(
    tmp_path: Path,
) -> None:
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
    cutoff = utc_now()
    with store.engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE workflow_processes "
                "SET last_heartbeat_at = :last_heartbeat_at "
                "WHERE process_id = :process_id"
            ),
            {
                "last_heartbeat_at": cutoff.isoformat(),
                "process_id": process.process_id,
            },
        )

    lost = store.mark_lost_workflow_processes(stale_before=cutoff)

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


def test_runtime_store_shared_publication_round_trip_and_latest(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    workflow = store.create_workflow_definition(
        name="Producer workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="producer-node",
        node_type="builtin.producer",
        node_run_id="node-1",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v3",
        workflow_run_id=run.workflow_run_id,
        node_run_id=node.node_run_id,
        logical_table_id="orders",
        version=3,
    )
    customers = make_table_ref(
        table_ref_id="table-customers-v5",
        workflow_run_id=run.workflow_run_id,
        node_run_id=node.node_run_id,
        logical_table_id="customers",
        version=5,
    )
    store.register_table_ref(orders)
    store.register_table_ref(customers)

    first = store.create_shared_publication(
        publication_id="publication-1",
        share_name="daily_report",
        producer_workflow_id=workflow.workflow_id,
        producer_run_id=run.workflow_run_id,
        members={
            "orders": orders.table_ref_id,
            "customers": customers.table_ref_id,
        },
        retention_policy={"retention_seconds": 3600},
    )
    second = store.create_shared_publication(
        publication_id="publication-2",
        share_name="daily_report",
        producer_workflow_id=workflow.workflow_id,
        producer_run_id=run.workflow_run_id,
        members={"orders": orders.table_ref_id},
    )

    assert first.publication_version == 1
    assert first.status == "PUBLISHED"
    assert first.retention_policy == {"retention_seconds": 3600}
    assert [
        (member.export_name, member.table_ref_id, member.exact_table_version)
        for member in first.members
    ] == [
        ("customers", customers.table_ref_id, 5),
        ("orders", orders.table_ref_id, 3),
    ]
    assert second.publication_version == 2
    assert store.get_shared_publication("publication-1") == first
    assert store.get_shared_publication_version(
        share_name="daily_report",
        publication_version=1,
    ) == first
    assert store.get_latest_shared_publication("daily_report") == second


def test_runtime_store_shared_publication_rejects_missing_member_atomically(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    run, _node = create_producer_context(store)

    with pytest.raises(ValueError, match="TableRef not found: missing-table"):
        store.create_shared_publication(
            publication_id="publication-1",
            share_name="daily_report",
            producer_workflow_id="workflow-1",
            producer_run_id=run.workflow_run_id,
            members={
                "orders": "missing-table",
            },
        )

    assert store.get_shared_publication("publication-1") is None
    assert row_count(database_path, "shared_publications") == 0
    assert row_count(database_path, "shared_publication_members") == 0


def test_runtime_store_shared_publication_rejects_unpublished_member_atomically(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    run, node = create_producer_context(store)
    table_ref = make_table_ref(
        table_ref_id="table-staging",
        workflow_run_id=run.workflow_run_id,
        node_run_id=node.node_run_id,
        logical_table_id="orders",
        version=1,
        mutability=TableMutability.WORKING_MUTABLE,
        lifecycle_status=LifecycleStatus.STAGING,
    )
    store.register_table_ref(table_ref)

    with pytest.raises(
        ValueError,
        match="Shared publication member must be PUBLISHED: table-staging",
    ):
        store.create_shared_publication(
            publication_id="publication-1",
            share_name="daily_report",
            producer_workflow_id="workflow-1",
            producer_run_id=run.workflow_run_id,
            members={"orders": table_ref.table_ref_id},
        )

    assert store.get_shared_publication("publication-1") is None
    assert row_count(database_path, "shared_publications") == 0
    assert row_count(database_path, "shared_publication_members") == 0


def test_runtime_store_shared_publication_rejects_mutable_member_atomically(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    run, node = create_producer_context(store)
    table_ref = make_table_ref(
        table_ref_id="table-mutable",
        workflow_run_id=run.workflow_run_id,
        node_run_id=node.node_run_id,
        logical_table_id="orders",
        version=1,
        mutability=TableMutability.WORKING_MUTABLE,
        lifecycle_status=LifecycleStatus.PUBLISHED,
    )
    store.register_table_ref(table_ref)

    with pytest.raises(
        ValueError,
        match=(
            "Shared publication member must be PUBLISHED_IMMUTABLE: "
            "table-mutable"
        ),
    ):
        store.create_shared_publication(
            publication_id="publication-1",
            share_name="daily_report",
            producer_workflow_id="workflow-1",
            producer_run_id=run.workflow_run_id,
            members={"orders": table_ref.table_ref_id},
        )

    assert store.get_shared_publication("publication-1") is None
    assert row_count(database_path, "shared_publications") == 0
    assert row_count(database_path, "shared_publication_members") == 0


def test_runtime_store_shared_publication_rejects_cross_run_member_atomically(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    producer_run, _producer_node = create_producer_context(store)
    other_run, other_node = create_producer_context(
        store,
        workflow_id="workflow-2",
        workflow_run_id="run-2",
        node_run_id="node-2",
    )
    table_ref = make_table_ref(
        table_ref_id="table-other-run",
        workflow_run_id=other_run.workflow_run_id,
        node_run_id=other_node.node_run_id,
        logical_table_id="orders",
        version=1,
    )
    store.register_table_ref(table_ref)

    with pytest.raises(
        ValueError,
        match=(
            "Shared publication member does not belong to producer run: "
            "table-other-run"
        ),
    ):
        store.create_shared_publication(
            publication_id="publication-1",
            share_name="daily_report",
            producer_workflow_id="workflow-1",
            producer_run_id=producer_run.workflow_run_id,
            members={"orders": table_ref.table_ref_id},
        )

    assert store.get_shared_publication("publication-1") is None
    assert row_count(database_path, "shared_publications") == 0
    assert row_count(database_path, "shared_publication_members") == 0


def test_runtime_store_shared_publication_rejects_mismatched_producer_workflow(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    run, node = create_producer_context(store)
    table_ref = make_table_ref(
        table_ref_id="table-orders",
        workflow_run_id=run.workflow_run_id,
        node_run_id=node.node_run_id,
        logical_table_id="orders",
        version=1,
    )
    store.register_table_ref(table_ref)

    with pytest.raises(
        ValueError,
        match="Producer run does not belong to workflow: run-1",
    ):
        store.create_shared_publication(
            publication_id="publication-1",
            share_name="daily_report",
            producer_workflow_id="workflow-other",
            producer_run_id=run.workflow_run_id,
            members={"orders": table_ref.table_ref_id},
        )

    assert store.get_shared_publication("publication-1") is None
    assert row_count(database_path, "shared_publications") == 0
    assert row_count(database_path, "shared_publication_members") == 0


def test_runtime_store_input_snapshot_round_trip_and_workflow_run_link(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    producer_run, producer_node = create_producer_context(store)
    consumer_run, _consumer_node = create_producer_context(
        store,
        workflow_id="workflow-consumer",
        workflow_run_id="run-consumer",
        node_run_id="node-consumer",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id=producer_run.workflow_run_id,
        node_run_id=producer_node.node_run_id,
        logical_table_id="orders",
        version=1,
    )
    customers = make_table_ref(
        table_ref_id="table-customers-v1",
        workflow_run_id=producer_run.workflow_run_id,
        node_run_id=producer_node.node_run_id,
        logical_table_id="customers",
        version=1,
    )
    store.register_table_ref(orders)
    store.register_table_ref(customers)
    v1 = store.create_shared_publication(
        publication_id="publication-v1",
        share_name="daily_report",
        producer_workflow_id="workflow-1",
        producer_run_id=producer_run.workflow_run_id,
        members={
            "orders": orders.table_ref_id,
            "customers": customers.table_ref_id,
        },
    )
    v2 = store.create_shared_publication(
        publication_id="publication-v2",
        share_name="daily_report",
        producer_workflow_id="workflow-1",
        producer_run_id=producer_run.workflow_run_id,
        members={"orders": orders.table_ref_id},
    )

    snapshot = store.create_input_snapshot(
        input_snapshot_id="snapshot-1",
        workflow_run_id=consumer_run.workflow_run_id,
        inputs=[
            InputSnapshotEntry(
                source_name="daily_report",
                publication_id=v1.publication_id,
                publication_version=v1.publication_version,
                selected_members=("orders", "customers"),
            )
        ],
    )

    assert v1.publication_version == 1
    assert v2.publication_version == 2
    assert snapshot.inputs == (
        InputSnapshotEntry(
            source_name="daily_report",
            publication_id="publication-v1",
            publication_version=1,
            selected_members=("orders", "customers"),
        ),
    )
    assert store.get_input_snapshot("snapshot-1") == snapshot
    loaded_consumer_run = store.get_workflow_run(consumer_run.workflow_run_id)
    assert loaded_consumer_run is not None
    assert loaded_consumer_run.input_snapshot_id == snapshot.input_snapshot_id
    assert store.get_latest_shared_publication("daily_report") == v2
    assert store.get_input_snapshot("snapshot-1") == snapshot


def test_runtime_store_input_snapshot_rejects_missing_workflow_run(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)

    with pytest.raises(ValueError, match="Workflow run not found: missing-run"):
        store.create_input_snapshot(
            input_snapshot_id="snapshot-1",
            workflow_run_id="missing-run",
            inputs=[],
        )

    assert store.get_input_snapshot("snapshot-1") is None
    assert row_count(database_path, "input_snapshots") == 0


def test_runtime_store_input_snapshot_rejects_missing_publication(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    consumer_run, _consumer_node = create_producer_context(store)

    with pytest.raises(
        ValueError,
        match="Input snapshot publication not found: missing-publication",
    ):
        store.create_input_snapshot(
            input_snapshot_id="snapshot-1",
            workflow_run_id=consumer_run.workflow_run_id,
            inputs=[
                InputSnapshotEntry(
                    source_name="daily_report",
                    publication_id="missing-publication",
                    publication_version=1,
                    selected_members=("orders",),
                )
            ],
        )

    assert store.get_input_snapshot("snapshot-1") is None
    assert row_count(database_path, "input_snapshots") == 0
    loaded_run = store.get_workflow_run(consumer_run.workflow_run_id)
    assert loaded_run is not None
    assert loaded_run.input_snapshot_id is None


def test_runtime_store_input_snapshot_rejects_publication_version_mismatch(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    producer_run, producer_node = create_producer_context(store)
    consumer_run, _consumer_node = create_producer_context(
        store,
        workflow_id="workflow-consumer",
        workflow_run_id="run-consumer",
        node_run_id="node-consumer",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id=producer_run.workflow_run_id,
        node_run_id=producer_node.node_run_id,
        logical_table_id="orders",
        version=1,
    )
    store.register_table_ref(orders)
    publication = store.create_shared_publication(
        publication_id="publication-v1",
        share_name="daily_report",
        producer_workflow_id="workflow-1",
        producer_run_id=producer_run.workflow_run_id,
        members={"orders": orders.table_ref_id},
    )

    with pytest.raises(
        ValueError,
        match="Input snapshot publication version mismatch: publication-v1",
    ):
        store.create_input_snapshot(
            input_snapshot_id="snapshot-1",
            workflow_run_id=consumer_run.workflow_run_id,
            inputs=[
                InputSnapshotEntry(
                    source_name="daily_report",
                    publication_id=publication.publication_id,
                    publication_version=publication.publication_version + 1,
                    selected_members=("orders",),
                )
            ],
        )

    assert store.get_input_snapshot("snapshot-1") is None
    assert row_count(database_path, "input_snapshots") == 0
    loaded_run = store.get_workflow_run(consumer_run.workflow_run_id)
    assert loaded_run is not None
    assert loaded_run.input_snapshot_id is None


def test_runtime_store_read_lease_round_trip_and_release(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    producer_run, producer_node = create_producer_context(store)
    consumer_run, _consumer_node = create_producer_context(
        store,
        workflow_id="workflow-consumer",
        workflow_run_id="run-consumer",
        node_run_id="node-consumer",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id=producer_run.workflow_run_id,
        node_run_id=producer_node.node_run_id,
        logical_table_id="orders",
        version=1,
    )
    store.register_table_ref(orders)
    publication = store.create_shared_publication(
        publication_id="publication-v1",
        share_name="daily_report",
        producer_workflow_id="workflow-1",
        producer_run_id=producer_run.workflow_run_id,
        members={"orders": orders.table_ref_id},
    )

    lease = store.create_read_lease(
        lease_id="lease-1",
        publication_id=publication.publication_id,
        publication_version=publication.publication_version,
        consumer_workflow_run_id=consumer_run.workflow_run_id,
        selected_members=("orders",),
        expires_at=utc_now() + timedelta(seconds=60),
    )

    assert lease.publication_id == publication.publication_id
    assert lease.publication_version == 1
    assert lease.selected_members == ("orders",)
    assert lease.consumer_workflow_run_id == consumer_run.workflow_run_id
    assert lease.released_at is None
    assert store.get_read_lease("lease-1") == lease
    assert store.list_read_leases_by_workflow_run(
        consumer_run.workflow_run_id,
        active_only=True,
    ) == [lease]

    released = store.release_read_lease("lease-1")

    assert released is not None
    assert released.released_at is not None
    assert store.get_read_lease("lease-1") == released
    assert store.list_read_leases_by_workflow_run(
        consumer_run.workflow_run_id,
        active_only=True,
    ) == []
    assert store.list_read_leases_by_workflow_run(
        consumer_run.workflow_run_id,
        active_only=False,
    ) == [released]


def test_runtime_store_read_lease_rejects_missing_consumer_run(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    producer_run, producer_node = create_producer_context(store)
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id=producer_run.workflow_run_id,
        node_run_id=producer_node.node_run_id,
        logical_table_id="orders",
        version=1,
    )
    store.register_table_ref(orders)
    publication = store.create_shared_publication(
        publication_id="publication-v1",
        share_name="daily_report",
        producer_workflow_id="workflow-1",
        producer_run_id=producer_run.workflow_run_id,
        members={"orders": orders.table_ref_id},
    )

    with pytest.raises(
        ValueError,
        match="Consumer workflow run not found: missing-run",
    ):
        store.create_read_lease(
            lease_id="lease-1",
            publication_id=publication.publication_id,
            publication_version=publication.publication_version,
            consumer_workflow_run_id="missing-run",
            selected_members=("orders",),
            expires_at=utc_now() + timedelta(seconds=60),
        )

    assert store.get_read_lease("lease-1") is None
    assert row_count(database_path, "read_leases") == 0


def test_runtime_store_read_lease_rejects_missing_publication(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    consumer_run, _consumer_node = create_producer_context(store)

    with pytest.raises(
        ValueError,
        match="Read lease publication not found: missing-publication",
    ):
        store.create_read_lease(
            lease_id="lease-1",
            publication_id="missing-publication",
            publication_version=1,
            consumer_workflow_run_id=consumer_run.workflow_run_id,
            selected_members=("orders",),
            expires_at=utc_now() + timedelta(seconds=60),
        )

    assert store.get_read_lease("lease-1") is None
    assert row_count(database_path, "read_leases") == 0


def test_runtime_store_read_lease_rejects_publication_version_mismatch(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    producer_run, producer_node = create_producer_context(store)
    consumer_run, _consumer_node = create_producer_context(
        store,
        workflow_id="workflow-consumer",
        workflow_run_id="run-consumer",
        node_run_id="node-consumer",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id=producer_run.workflow_run_id,
        node_run_id=producer_node.node_run_id,
        logical_table_id="orders",
        version=1,
    )
    store.register_table_ref(orders)
    publication = store.create_shared_publication(
        publication_id="publication-v1",
        share_name="daily_report",
        producer_workflow_id="workflow-1",
        producer_run_id=producer_run.workflow_run_id,
        members={"orders": orders.table_ref_id},
    )

    with pytest.raises(
        ValueError,
        match="Read lease publication version mismatch: publication-v1",
    ):
        store.create_read_lease(
            lease_id="lease-1",
            publication_id=publication.publication_id,
            publication_version=publication.publication_version + 1,
            consumer_workflow_run_id=consumer_run.workflow_run_id,
            selected_members=("orders",),
            expires_at=utc_now() + timedelta(seconds=60),
        )

    assert store.get_read_lease("lease-1") is None
    assert row_count(database_path, "read_leases") == 0


def test_runtime_store_read_lease_excludes_expired_from_active_list(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    producer_run, producer_node = create_producer_context(store)
    consumer_run, _consumer_node = create_producer_context(
        store,
        workflow_id="workflow-consumer",
        workflow_run_id="run-consumer",
        node_run_id="node-consumer",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id=producer_run.workflow_run_id,
        node_run_id=producer_node.node_run_id,
        logical_table_id="orders",
        version=1,
    )
    store.register_table_ref(orders)
    publication = store.create_shared_publication(
        publication_id="publication-v1",
        share_name="daily_report",
        producer_workflow_id="workflow-1",
        producer_run_id=producer_run.workflow_run_id,
        members={"orders": orders.table_ref_id},
    )
    expired = store.create_read_lease(
        lease_id="lease-expired",
        publication_id=publication.publication_id,
        publication_version=publication.publication_version,
        consumer_workflow_run_id=consumer_run.workflow_run_id,
        selected_members=("orders",),
        expires_at=utc_now() - timedelta(seconds=1),
    )

    assert store.list_read_leases_by_workflow_run(
        consumer_run.workflow_run_id,
        active_only=True,
    ) == []
    assert store.list_read_leases_by_workflow_run(
        consumer_run.workflow_run_id,
        active_only=False,
    ) == [expired]


def test_runtime_store_releases_unreleased_read_leases_for_workflow_run(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    producer_run, producer_node = create_producer_context(store)
    consumer_run, _consumer_node = create_producer_context(
        store,
        workflow_id="workflow-consumer",
        workflow_run_id="run-consumer",
        node_run_id="node-consumer",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id=producer_run.workflow_run_id,
        node_run_id=producer_node.node_run_id,
        logical_table_id="orders",
        version=1,
    )
    store.register_table_ref(orders)
    publication = store.create_shared_publication(
        publication_id="publication-v1",
        share_name="daily_report",
        producer_workflow_id="workflow-1",
        producer_run_id=producer_run.workflow_run_id,
        members={"orders": orders.table_ref_id},
    )
    active = store.create_read_lease(
        lease_id="lease-active",
        publication_id=publication.publication_id,
        publication_version=publication.publication_version,
        consumer_workflow_run_id=consumer_run.workflow_run_id,
        selected_members=("orders",),
        expires_at=utc_now() + timedelta(seconds=60),
    )
    expired = store.create_read_lease(
        lease_id="lease-expired",
        publication_id=publication.publication_id,
        publication_version=publication.publication_version,
        consumer_workflow_run_id=consumer_run.workflow_run_id,
        selected_members=("orders",),
        expires_at=utc_now() - timedelta(seconds=1),
    )

    released = store.release_unreleased_read_leases_for_workflow_run(
        consumer_run.workflow_run_id
    )

    assert [lease.lease_id for lease in released] == [
        active.lease_id,
        expired.lease_id,
    ]
    assert released[0].released_at is not None
    assert released[1].released_at is not None
    assert store.get_read_lease(active.lease_id).released_at is not None
    assert store.get_read_lease(expired.lease_id).released_at is not None
    assert store.list_read_leases_by_workflow_run(
        consumer_run.workflow_run_id,
        active_only=True,
    ) == []
    assert store.release_unreleased_read_leases_for_workflow_run(
        consumer_run.workflow_run_id
    ) == []


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


def test_runtime_event_sequence_numbers_are_atomic_under_concurrency(
    tmp_path: Path,
) -> None:
    from flowweaver.protocols.enums import EventType
    from flowweaver.protocols.events import EventModel

    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)

    def append_event(index: int) -> int:
        return store.append_runtime_event(
            EventModel(
                event_type=EventType.NODE_PROGRESS,
                payload={"index": index},
            )
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        sequence_numbers = list(executor.map(append_event, range(32)))

    assert sorted(sequence_numbers) == list(range(1, 33))
    assert len({event.event_id for event in store.list_runtime_events(limit=40)}) == 32
