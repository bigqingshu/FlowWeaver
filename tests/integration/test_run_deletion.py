from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flowweaver.api.app import create_app
from flowweaver.common.config import EngineConfig
from flowweaver.common.database import sqlite_url
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    DataRefRecord,
    InputSnapshotRecord,
    LoopIterationNodeRunRecord,
    LoopIterationRunRecord,
    LoopIterationTableRefRecord,
    LoopRunRecord,
    NodeRunRecord,
    NodeTaskRecord,
    NodeTaskResultOutputBindingRecord,
    NodeTaskResultRecord,
    ReadLeaseRecord,
    RuntimeEventRecord,
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
    TableLeaseRecord,
    WorkflowProcessRecord,
    WorkflowRunRecord,
    WorkflowRunRuntimeOptionsRecord,
)
from flowweaver.engine.event_router import EventRouter
from flowweaver.engine.immediate_session import immediate_session
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_workflow_run_deletion import (
    delete_workflow_run_in_session,
)
from flowweaver.engine.service_container import ServiceContainer
from flowweaver.engine.supervisor import Supervisor
from flowweaver.engine.table_lease_manager import TableLeaseManager
from flowweaver.nodes.registry import NodeRegistry
from flowweaver.protocols.enums import (
    LifecycleStatus,
    NodeRunStatus,
    TableLeaseStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
    WorkflowRunStatus,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

TOKEN = "test-token"


@contextmanager
def _client_context(
    tmp_path: Path,
) -> Iterator[tuple[TestClient, RuntimeStore]]:
    database_path = tmp_path / "metadata.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")
    store = RuntimeStore.from_sqlite_path(database_path)
    engine_config = EngineConfig(
        data_dir=tmp_path / "runtime",
        local_api_token=TOKEN,
        enforce_single_instance=False,
        workflow_process_heartbeat_interval_seconds=0,
        supervisor_maintenance_interval_seconds=0.05,
    )
    event_router = EventRouter(store)
    container = ServiceContainer(
        config=engine_config,
        runtime_store=store,
        event_router=event_router,
        table_lease_manager=TableLeaseManager(store.engine),
        supervisor=Supervisor(
            config=engine_config,
            runtime_store=store,
            event_router=event_router,
        ),
        node_registry=NodeRegistry(),
    )
    with TestClient(create_app(container)) as client:
        yield client, store


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def _create_workflow(client: TestClient, name: str = "Deletion workflow") -> str:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": name,
            "definition": {
                "schema_version": "1.0",
                "nodes": [],
                "connections": [],
            },
        },
        headers=_headers(),
    )
    assert response.status_code == 201
    return response.json()["data"]["workflow_id"]


def _create_run(
    store: RuntimeStore,
    workflow_id: str,
    workflow_run_id: str,
    status: WorkflowRunStatus,
):
    return store.create_workflow_run(
        workflow_id=workflow_id,
        workflow_run_id=workflow_run_id,
        status=status,
    )


def _table_ref(
    *,
    table_ref_id: str,
    workflow_run_id: str,
    node_run_id: str,
    storage_kind: TableStorageKind,
    lifecycle_status: LifecycleStatus,
    database_path: Path,
) -> TableRefModel:
    return TableRefModel(
        table_ref_id=table_ref_id,
        role=TableRole.CURRENT,
        storage_kind=storage_kind,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.WORKING_MUTABLE,
        provider_id=(
            "sqlite_runtime"
            if storage_kind == TableStorageKind.RUNTIME_SQL
            else "sqlite_external"
        ),
        resource_profile_id=None,
        mount_id=None,
        logical_table_id=table_ref_id,
        opaque_handle={
            "database_path": str(database_path),
            "table_name": table_ref_id.replace("-", "_"),
        },
        schema=[
            FieldSchemaModel(
                field_id=f"{table_ref_id}-value",
                name="value",
                data_type="INTEGER",
                nullable=False,
                ordinal=0,
            )
        ],
        schema_fingerprint=f"{table_ref_id}-schema",
        version=1,
        capabilities={"READ", "WRITE"},
        lifecycle_status=lifecycle_status,
        created_by_workflow_run_id=workflow_run_id,
        created_by_node_run_id=node_run_id,
        created_at=utc_now(),
    )


def _error_code(response) -> str:
    payload = response.json()
    assert payload["ok"] is False
    return payload["error"]["error_code"]


def test_delete_run_rejects_non_terminal_run(tmp_path: Path) -> None:
    with _client_context(tmp_path) as (client, store):
        workflow_id = _create_workflow(client)
        _create_run(store, workflow_id, "run-pending", WorkflowRunStatus.PENDING)

        response = client.delete(
            "/api/v1/runs/run-pending",
            headers=_headers(),
        )

        assert response.status_code == 409
        assert _error_code(response) == "WORKFLOW_RUN_NOT_TERMINAL"
        assert store.get_workflow_run("run-pending") is not None


def test_delete_run_rejects_active_process(tmp_path: Path) -> None:
    with _client_context(tmp_path) as (client, store):
        workflow_id = _create_workflow(client)
        _create_run(store, workflow_id, "run-active-process", WorkflowRunStatus.FAILED)
        store.create_workflow_process(
            workflow_run_id="run-active-process",
            process_id="process-active",
        )

        response = client.delete(
            "/api/v1/runs/run-active-process",
            headers=_headers(),
        )

        assert response.status_code == 409
        assert _error_code(response) == "WORKFLOW_RUN_PROCESS_ACTIVE"
        assert response.json()["error"]["details"]["process_ids"] == [
            "process-active"
        ]


def test_delete_run_requires_internal_table_cleanup(tmp_path: Path) -> None:
    with _client_context(tmp_path) as (client, store):
        workflow_id = _create_workflow(client)
        _create_run(
            store,
            workflow_id,
            "run-needs-cleanup",
            WorkflowRunStatus.SUCCEEDED,
        )
        node_run = store.create_node_run(
            workflow_run_id="run-needs-cleanup",
            node_instance_id="source",
            node_type="core.source",
            status=NodeRunStatus.SUCCEEDED,
        )
        store.register_table_ref(
            _table_ref(
                table_ref_id="runtime-table",
                workflow_run_id="run-needs-cleanup",
                node_run_id=node_run.node_run_id,
                storage_kind=TableStorageKind.RUNTIME_SQL,
                lifecycle_status=LifecycleStatus.ACTIVE,
                database_path=tmp_path / "runtime.db",
            )
        )

        response = client.delete(
            "/api/v1/runs/run-needs-cleanup",
            headers=_headers(),
        )

        assert response.status_code == 409
        assert _error_code(response) == "WORKFLOW_RUN_TABLES_NOT_CLEANED"
        assert response.json()["error"]["details"]["table_ref_ids"] == [
            "runtime-table"
        ]


def test_delete_run_rejects_active_table_lease(tmp_path: Path) -> None:
    with _client_context(tmp_path) as (client, store):
        workflow_id = _create_workflow(client)
        _create_run(store, workflow_id, "run-leased", WorkflowRunStatus.SUCCEEDED)
        node_run = store.create_node_run(
            workflow_run_id="run-leased",
            node_instance_id="source",
            node_type="core.source",
            status=NodeRunStatus.SUCCEEDED,
        )
        store.register_table_ref(
            _table_ref(
                table_ref_id="leased-ref",
                workflow_run_id="run-leased",
                node_run_id=node_run.node_run_id,
                storage_kind=TableStorageKind.RUNTIME_SQL,
                lifecycle_status=LifecycleStatus.RELEASED,
                database_path=tmp_path / "runtime.db",
            )
        )
        now = utc_now()
        with immediate_session(store.engine) as session:
            session.add(
                TableLeaseRecord(
                    lease_id="active-lease",
                    table_ref_id="leased-ref",
                    lease_type="READ",
                    owner_id="reader",
                    status=TableLeaseStatus.ACTIVE.value,
                    acquired_at=now.isoformat(),
                    last_heartbeat_at=now.isoformat(),
                    expires_at=(now + timedelta(minutes=5)).isoformat(),
                    released_at=None,
                    metadata_json="{}",
                )
            )

        response = client.delete("/api/v1/runs/run-leased", headers=_headers())

        assert response.status_code == 409
        assert _error_code(response) == "WORKFLOW_RUN_DELETE_BLOCKED"
        assert response.json()["error"]["details"]["blocker"] == (
            "active_table_lease"
        )


def test_delete_run_rejects_active_shared_publication(tmp_path: Path) -> None:
    with _client_context(tmp_path) as (client, store):
        workflow_id = _create_workflow(client)
        _create_run(store, workflow_id, "run-publisher", WorkflowRunStatus.SUCCEEDED)
        now_text = utc_now().isoformat()
        with immediate_session(store.engine) as session:
            session.add(
                SharedPublicationRecord(
                    publication_id="active-publication",
                    share_name="active-share",
                    publication_version=1,
                    producer_workflow_id=workflow_id,
                    producer_run_id="run-publisher",
                    status="PUBLISHED",
                    input_snapshot_id=None,
                    retention_policy_json="{}",
                    created_at=now_text,
                    expires_at=None,
                    release_started_at=None,
                    cleanup_last_progress_at=None,
                    released_at=None,
                    cleanup_attempt_count=0,
                    last_cleanup_error_json=None,
                )
            )

        response = client.delete("/api/v1/runs/run-publisher", headers=_headers())

        assert response.status_code == 409
        assert _error_code(response) == "WORKFLOW_RUN_DELETE_BLOCKED"
        assert response.json()["error"]["details"]["blocker"] == (
            "active_shared_publication"
        )


def test_delete_run_rejects_active_reader_of_released_publication(
    tmp_path: Path,
) -> None:
    with _client_context(tmp_path) as (client, store):
        workflow_id = _create_workflow(client)
        _create_run(store, workflow_id, "run-publisher", WorkflowRunStatus.SUCCEEDED)
        _create_run(store, workflow_id, "run-reader", WorkflowRunStatus.SUCCEEDED)
        now = utc_now()
        now_text = now.isoformat()
        with immediate_session(store.engine) as session:
            session.add(
                SharedPublicationRecord(
                    publication_id="released-publication",
                    share_name="released-share",
                    publication_version=1,
                    producer_workflow_id=workflow_id,
                    producer_run_id="run-publisher",
                    status="RELEASED",
                    input_snapshot_id=None,
                    retention_policy_json="{}",
                    created_at=now_text,
                    expires_at=now_text,
                    release_started_at=now_text,
                    cleanup_last_progress_at=now_text,
                    released_at=now_text,
                    cleanup_attempt_count=1,
                    last_cleanup_error_json=None,
                )
            )
            session.flush()
            session.add(
                ReadLeaseRecord(
                    lease_id="active-reader",
                    publication_id="released-publication",
                    publication_version=1,
                    consumer_workflow_run_id="run-reader",
                    selected_members_json="[]",
                    acquired_at=now_text,
                    expires_at=(now + timedelta(minutes=5)).isoformat(),
                    released_at=None,
                )
            )

        response = client.delete("/api/v1/runs/run-publisher", headers=_headers())

        assert response.status_code == 409
        assert _error_code(response) == "WORKFLOW_RUN_DELETE_BLOCKED"
        assert response.json()["error"]["details"]["blocker"] == (
            "active_publication_read_lease"
        )


def test_delete_run_rejects_cross_run_table_reference(tmp_path: Path) -> None:
    with _client_context(tmp_path) as (client, store):
        workflow_id = _create_workflow(client)
        _create_run(store, workflow_id, "run-producer", WorkflowRunStatus.SUCCEEDED)
        _create_run(store, workflow_id, "run-consumer", WorkflowRunStatus.SUCCEEDED)
        producer_node = store.create_node_run(
            workflow_run_id="run-producer",
            node_instance_id="producer",
            node_type="core.source",
            status=NodeRunStatus.SUCCEEDED,
        )
        store.register_table_ref(
            _table_ref(
                table_ref_id="shared-ref",
                workflow_run_id="run-producer",
                node_run_id=producer_node.node_run_id,
                storage_kind=TableStorageKind.RUNTIME_SQL,
                lifecycle_status=LifecycleStatus.RELEASED,
                database_path=tmp_path / "runtime.db",
            )
        )
        now_text = utc_now().isoformat()
        with immediate_session(store.engine) as session:
            loop = LoopRunRecord(
                loop_run_id="consumer-loop",
                workflow_run_id="run-consumer",
                loop_id="loop",
                start_node_instance_id="start",
                judge_node_instance_id="judge",
                status="ENDED",
                state_version=1,
                current_iteration=1,
                max_iterations=1,
                exit_reason="completed",
                started_at=now_text,
                finished_at=now_text,
                error_json=None,
                created_at=now_text,
            )
            session.add(loop)
            session.flush()
            session.add(
                LoopIterationRunRecord(
                    loop_iteration_id="consumer-iteration",
                    loop_run_id="consumer-loop",
                    iteration_index=0,
                    status="SUCCEEDED",
                    state_version=1,
                    input_table_ref_id="shared-ref",
                    input_selector_json=None,
                    output_table_ref_id=None,
                    failed_node_run_id=None,
                    started_at=now_text,
                    finished_at=now_text,
                    error_json=None,
                    created_at=now_text,
                )
            )

        response = client.delete("/api/v1/runs/run-producer", headers=_headers())

        assert response.status_code == 409
        assert _error_code(response) == "WORKFLOW_RUN_DELETE_BLOCKED"
        assert response.json()["error"]["details"]["blocker"] == (
            "cross_run_loop_iteration"
        )


def test_delete_run_removes_associated_metadata_but_keeps_external_sql(
    tmp_path: Path,
) -> None:
    external_database = tmp_path / "external.db"
    with sqlite3.connect(external_database) as connection:
        connection.execute("CREATE TABLE keep_me (value INTEGER NOT NULL)")
        connection.execute("INSERT INTO keep_me (value) VALUES (42)")

    with _client_context(tmp_path) as (client, store):
        workflow_id = _create_workflow(client)
        _create_run(store, workflow_id, "run-delete", WorkflowRunStatus.SUCCEEDED)
        node_run = store.create_node_run(
            workflow_run_id="run-delete",
            node_instance_id="source",
            node_type="core.source",
            node_run_id="node-delete",
            status=NodeRunStatus.SUCCEEDED,
        )
        store.register_table_ref(
            _table_ref(
                table_ref_id="internal-ref",
                workflow_run_id="run-delete",
                node_run_id=node_run.node_run_id,
                storage_kind=TableStorageKind.RUNTIME_SQL,
                lifecycle_status=LifecycleStatus.RELEASED,
                database_path=tmp_path / "runtime.db",
            )
        )
        store.register_table_ref(
            _table_ref(
                table_ref_id="external-ref",
                workflow_run_id="run-delete",
                node_run_id=node_run.node_run_id,
                storage_kind=TableStorageKind.EXTERNAL_SQL,
                lifecycle_status=LifecycleStatus.ACTIVE,
                database_path=external_database,
            )
        )
        _seed_associated_records(store)

        response = client.delete("/api/v1/runs/run-delete", headers=_headers())

        assert response.status_code == 200
        assert response.json()["data"] == {
            "workflow_run_id": "run-delete",
            "deleted": True,
        }
        assert store.get_workflow_run("run-delete") is None
        _assert_associated_records_deleted(store)

    with sqlite3.connect(external_database) as connection:
        assert connection.execute("SELECT value FROM keep_me").fetchone() == (42,)


def test_run_deletion_changes_roll_back_with_outer_transaction(
    tmp_path: Path,
) -> None:
    with _client_context(tmp_path) as (client, store):
        workflow_id = _create_workflow(client)
        _create_run(store, workflow_id, "run-rollback", WorkflowRunStatus.FAILED)
        store.create_node_run(
            workflow_run_id="run-rollback",
            node_instance_id="source",
            node_type="core.source",
            node_run_id="node-rollback",
            status=NodeRunStatus.FAILED,
        )

        with pytest.raises(RuntimeError, match="force rollback"):
            with immediate_session(store.engine) as session:
                delete_workflow_run_in_session(session, "run-rollback")
                raise RuntimeError("force rollback")

        assert store.get_workflow_run("run-rollback") is not None
        assert store.get_node_run("node-rollback") is not None


def test_delete_run_returns_not_found_after_success(tmp_path: Path) -> None:
    with _client_context(tmp_path) as (client, store):
        workflow_id = _create_workflow(client)
        _create_run(store, workflow_id, "run-once", WorkflowRunStatus.CANCELLED)

        first = client.delete("/api/v1/runs/run-once", headers=_headers())
        second = client.delete("/api/v1/runs/run-once", headers=_headers())

        assert first.status_code == 200
        assert second.status_code == 404
        assert _error_code(second) == "WORKFLOW_RUN_NOT_FOUND"


def _seed_associated_records(store: RuntimeStore) -> None:
    now = utc_now()
    now_text = now.isoformat()
    with immediate_session(store.engine) as session:
        session.add_all(
            [
                WorkflowProcessRecord(
                    process_id="process-delete",
                    workflow_run_id="run-delete",
                    os_pid=None,
                    process_generation=1,
                    fencing_token="fence",
                    status="EXITED",
                    started_at=now_text,
                    last_heartbeat_at=now_text,
                    cancel_requested_at=None,
                    exited_at=now_text,
                    exit_code=0,
                    error_json=None,
                ),
                WorkflowRunRuntimeOptionsRecord(
                    workflow_run_id="run-delete",
                    requested_version=1,
                    applied_version=1,
                    overlay_json="{}",
                    requested_at=now_text,
                    applied_at=now_text,
                ),
                InputSnapshotRecord(
                    input_snapshot_id="snapshot-delete",
                    workflow_run_id="run-delete",
                    snapshot_json="[]",
                    created_at=now_text,
                ),
                RuntimeEventRecord(
                    event_id="event-delete",
                    event_version="1.0",
                    event_type="WORKFLOW_FINISHED",
                    timestamp=now_text,
                    workflow_run_id="run-delete",
                    node_run_id="node-delete",
                    payload_json="{}",
                ),
                LoopRunRecord(
                    loop_run_id="loop-delete",
                    workflow_run_id="run-delete",
                    loop_id="loop",
                    start_node_instance_id="source",
                    judge_node_instance_id="source",
                    status="ENDED",
                    state_version=1,
                    current_iteration=1,
                    max_iterations=1,
                    exit_reason="completed",
                    started_at=now_text,
                    finished_at=now_text,
                    error_json=None,
                    created_at=now_text,
                ),
                TableLeaseRecord(
                    lease_id="released-table-lease",
                    table_ref_id="internal-ref",
                    lease_type="READ",
                    owner_id="run-delete",
                    status=TableLeaseStatus.RELEASED.value,
                    acquired_at=now_text,
                    last_heartbeat_at=now_text,
                    expires_at=now_text,
                    released_at=now_text,
                    metadata_json="{}",
                ),
                SharedPublicationRecord(
                    publication_id="publication-delete",
                    share_name="deleted-share",
                    publication_version=1,
                    producer_workflow_id="workflow-delete",
                    producer_run_id="run-delete",
                    status="RELEASED",
                    input_snapshot_id="snapshot-delete",
                    retention_policy_json="{}",
                    created_at=now_text,
                    expires_at=now_text,
                    release_started_at=now_text,
                    cleanup_last_progress_at=now_text,
                    released_at=now_text,
                    cleanup_attempt_count=1,
                    last_cleanup_error_json=None,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                NodeTaskRecord(
                    task_id="task-delete",
                    workflow_run_id="run-delete",
                    workflow_process_id="process-delete",
                    process_generation=1,
                    node_run_id="node-delete",
                    node_instance_id="source",
                    node_type="core.source",
                    node_version="1.0",
                    attempt=1,
                    input_refs_json="[]",
                    input_slot_bindings_json="{}",
                    config_json="{}",
                    runtime_feedback_policy_json=None,
                    runtime_options_version=1,
                    timeout_seconds=60,
                    created_at=now_text,
                ),
                LoopIterationRunRecord(
                    loop_iteration_id="iteration-delete",
                    loop_run_id="loop-delete",
                    iteration_index=0,
                    status="SUCCEEDED",
                    state_version=1,
                    input_table_ref_id="internal-ref",
                    input_selector_json=None,
                    output_table_ref_id="external-ref",
                    failed_node_run_id=None,
                    started_at=now_text,
                    finished_at=now_text,
                    error_json=None,
                    created_at=now_text,
                ),
                SharedPublicationMemberRecord(
                    publication_id="publication-delete",
                    export_name="main",
                    table_ref_id="internal-ref",
                    exact_table_version=1,
                ),
                ReadLeaseRecord(
                    lease_id="released-read-lease",
                    publication_id="publication-delete",
                    publication_version=1,
                    consumer_workflow_run_id="run-delete",
                    selected_members_json='["main"]',
                    acquired_at=now_text,
                    expires_at=(now + timedelta(minutes=1)).isoformat(),
                    released_at=now_text,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                NodeTaskResultRecord(
                    result_id="result-delete",
                    task_id="task-delete",
                    node_run_id="node-delete",
                    attempt=1,
                    executor_id="executor",
                    process_generation=1,
                    status="SUCCEEDED",
                    output_refs_json='["internal-ref"]',
                    output_slot_bindings_json='{"out":"internal-ref"}',
                    summary_json="{}",
                    error_json=None,
                    started_at=now_text,
                    finished_at=now_text,
                ),
                LoopIterationTableRefRecord(
                    loop_iteration_id="iteration-delete",
                    table_ref_id="internal-ref",
                    role="INPUT",
                    created_at=now_text,
                ),
                LoopIterationNodeRunRecord(
                    loop_iteration_id="iteration-delete",
                    node_run_id="node-delete",
                    node_instance_id="source",
                    role="BODY",
                    created_at=now_text,
                ),
            ]
        )
        session.flush()
        session.add(
            NodeTaskResultOutputBindingRecord(
                result_id="result-delete",
                task_id="task-delete",
                node_run_id="node-delete",
                output_slot="out",
                output_ref_id="internal-ref",
            )
        )


def _assert_associated_records_deleted(store: RuntimeStore) -> None:
    record_types = (
        WorkflowRunRecord,
        WorkflowProcessRecord,
        WorkflowRunRuntimeOptionsRecord,
        NodeRunRecord,
        NodeTaskRecord,
        NodeTaskResultRecord,
        NodeTaskResultOutputBindingRecord,
        RuntimeEventRecord,
        LoopRunRecord,
        LoopIterationRunRecord,
        LoopIterationTableRefRecord,
        LoopIterationNodeRunRecord,
        DataRefRecord,
        TableLeaseRecord,
        SharedPublicationRecord,
        SharedPublicationMemberRecord,
        InputSnapshotRecord,
        ReadLeaseRecord,
    )
    with Session(store.engine) as session:
        for record_type in record_types:
            remaining = session.scalar(
                select(func.count()).select_from(record_type)
            )
            assert remaining == 0, record_type.__tablename__
