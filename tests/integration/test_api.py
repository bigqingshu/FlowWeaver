from __future__ import annotations

import queue
import threading
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from flowweaver.api.app import create_app
from flowweaver.common.config import EngineConfig
from flowweaver.engine.bootstrap import EngineHostBootstrap
from flowweaver.engine.event_router import EventRouter
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.service_container import ServiceContainer
from flowweaver.engine.supervisor import Supervisor
from flowweaver.engine.table_lease_manager import TableLeaseManager
from flowweaver.nodes.registry import NodeDefinitionSpec, NodePortSpec, NodeRegistry
from flowweaver.protocols.enums import EventType, WorkflowRunStatus
from flowweaver.protocols.events import EventModel

TOKEN = "test-token"


def valid_definition() -> dict:
    return {"schema_version": "1.0", "nodes": [], "connections": []}


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def make_client(tmp_path: Path) -> tuple[TestClient, RuntimeStore, ServiceContainer]:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    config = EngineConfig(
        data_dir=tmp_path / "runtime",
        local_api_token=TOKEN,
        enforce_single_instance=False,
        workflow_process_heartbeat_interval_seconds=0,
        supervisor_maintenance_interval_seconds=0.05,
    )
    node_registry = NodeRegistry()
    node_registry.register(
        NodeDefinitionSpec(
            node_type="core.source",
            node_version="1.0",
            display_name="Source",
            output_ports=(NodePortSpec("out"),),
        )
    )
    node_registry.register(
        NodeDefinitionSpec(
            node_type="core.transform",
            node_version="1.0",
            display_name="Transform",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
        )
    )
    event_router = EventRouter(store)
    container = ServiceContainer(
        config=config,
        runtime_store=store,
        event_router=event_router,
        table_lease_manager=TableLeaseManager(store.engine),
        supervisor=Supervisor(
            config=config,
            runtime_store=store,
            event_router=event_router,
        ),
        node_registry=node_registry,
    )
    return TestClient(create_app(container)), store, container


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def response_data(response):
    payload = response.json()
    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["request_id"]
    return payload["data"]


def response_error(response):
    payload = response.json()
    assert payload["ok"] is False
    assert payload["data"] is None
    assert payload["request_id"]
    return payload["error"]


def test_health_returns_uniform_response(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    response = client.get("/api/v1/health", headers={"x-request-id": "request-1"})

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {"status": "ok"},
        "error": None,
        "request_id": "request-1",
    }


def test_workflow_crud_api(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    created = response_data(
        client.post(
            "/api/v1/workflows",
            json={"name": "API workflow", "definition": valid_definition()},
            headers=auth_headers(),
        )
    )
    workflow_id = created["workflow_id"]

    assert created["name"] == "API workflow"
    assert created["version"] == 1
    assert created["revision_id"]

    loaded = response_data(
        client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers())
    )
    listed = response_data(client.get("/api/v1/workflows", headers=auth_headers()))
    updated = response_data(
        client.put(
            f"/api/v1/workflows/{workflow_id}",
            json={
                "definition": {
                    "schema_version": "1.0",
                    "nodes": [],
                    "connections": [],
                    "outputs": [],
                }
            },
            headers=auth_headers(),
        )
    )
    revisions = response_data(
        client.get(
            f"/api/v1/workflows/{workflow_id}/revisions",
            headers=auth_headers(),
        )
    )
    first_revision = response_data(
        client.get(
            f"/api/v1/workflows/{workflow_id}/revisions/{created['revision_id']}",
            headers=auth_headers(),
        )
    )
    deleted = response_data(
        client.delete(f"/api/v1/workflows/{workflow_id}", headers=auth_headers())
    )

    assert loaded["workflow_id"] == workflow_id
    assert [item["workflow_id"] for item in listed] == [workflow_id]
    assert updated["version"] == 2
    assert updated["revision_id"] != created["revision_id"]
    assert [revision["version"] for revision in revisions] == [1, 2]
    assert first_revision["definition"] == valid_definition()
    assert deleted == {"workflow_id": workflow_id, "deleted": True}


def test_workflow_not_found_uses_error_envelope(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    response = client.get("/api/v1/workflows/missing", headers=auth_headers())

    assert response.status_code == 404
    error = response_error(response)
    assert error["error_code"] == "WORKFLOW_NOT_FOUND"
    assert error["retryable"] is False


def test_run_query_api(tmp_path: Path) -> None:
    client, store, _container = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="Run source",
        definition=valid_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
        status=WorkflowRunStatus.PENDING,
    )

    listed = response_data(client.get("/api/v1/runs", headers=auth_headers()))
    loaded = response_data(
        client.get(f"/api/v1/runs/{run.workflow_run_id}", headers=auth_headers())
    )
    filtered = response_data(
        client.get(
            "/api/v1/runs",
            params={"status": "PENDING"},
            headers=auth_headers(),
        )
    )

    assert [item["workflow_run_id"] for item in listed] == ["run-1"]
    assert loaded["workflow_id"] == "workflow-1"
    assert loaded["revision_id"] == workflow.revision_id
    assert filtered[0]["status"] == "PENDING"


def test_start_empty_workflow_run_completes_in_process(tmp_path: Path) -> None:
    client, store, container = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="Empty run",
        definition=valid_definition(),
        workflow_id="workflow-1",
    )

    started = response_data(
        client.post(
            f"/api/v1/workflows/{workflow.workflow_id}/runs",
            headers=auth_headers(),
        )
    )
    run_id = started["workflow_run_id"]
    deadline = time.monotonic() + 5
    loaded = store.get_workflow_run(run_id)
    while time.monotonic() < deadline:
        loaded = store.get_workflow_run(run_id)
        if loaded is not None and loaded.status == "SUCCEEDED":
            break
        time.sleep(0.05)

    process = store.get_workflow_process_for_run(run_id)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        container.supervisor.sweep_exited_children()
        process = store.get_workflow_process_for_run(run_id)
        if process is not None and process.status == "EXITED":
            break
        time.sleep(0.05)
    events = store.list_runtime_events()

    assert loaded is not None
    assert loaded.status == "SUCCEEDED"
    assert process is not None
    assert process.os_pid is not None
    assert process.status == "EXITED"
    assert [event.event_type for event in events] == [
        "WORKFLOW_STARTED",
        "WORKFLOW_FINISHED",
    ]


def test_start_non_empty_workflow_initializes_node_runs(tmp_path: Path) -> None:
    client, store, _container = make_client(tmp_path)
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": "DAG run",
            "definition": {
                "schema_version": "1.0",
                "nodes": [
                    {
                        "node_instance_id": "source",
                        "node_type": "core.source",
                        "node_version": "1.0",
                    },
                    {
                        "node_instance_id": "transform",
                        "node_type": "core.transform",
                        "node_version": "1.0",
                    },
                ],
                "connections": [
                    {
                        "connection_id": "c1",
                        "source_node_id": "source",
                        "source_port": "out",
                        "target_node_id": "transform",
                        "target_port": "in",
                    }
                ],
            },
        },
        headers=auth_headers(),
    )
    workflow = response_data(response)
    run = response_data(
        client.post(
            f"/api/v1/workflows/{workflow['workflow_id']}/runs",
            headers=auth_headers(),
        )
    )

    deadline = time.monotonic() + 5
    node_runs = []
    while time.monotonic() < deadline:
        node_runs = store.list_node_runs(run["workflow_run_id"])
        if len(node_runs) == 2:
            break
        time.sleep(0.05)

    api_node_runs = response_data(
        client.get(
            f"/api/v1/runs/{run['workflow_run_id']}/nodes",
            headers=auth_headers(),
        )
    )

    assert {node.node_instance_id: node.status for node in node_runs} == {
        "source": "READY",
        "transform": "WAITING_DEPENDENCY",
    }
    assert [item["node_instance_id"] for item in api_node_runs] == [
        "source",
        "transform",
    ]
    assert store.get_workflow_run(run["workflow_run_id"]).status == "RUNNING"
    client.post(
        f"/api/v1/runs/{run['workflow_run_id']}/cancel",
        headers=auth_headers(),
    )
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        loaded = store.get_workflow_run(run["workflow_run_id"])
        if loaded is not None and loaded.status == "CANCELLED":
            break
        time.sleep(0.05)


def test_cancel_run_marks_process_cancel_requested(tmp_path: Path) -> None:
    client, store, _container = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="Cancelable",
        definition=valid_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(workflow_id=workflow.workflow_id)
    process = store.create_workflow_process(workflow_run_id=run.workflow_run_id)

    response = client.post(
        f"/api/v1/runs/{run.workflow_run_id}/cancel",
        headers=auth_headers(),
    )
    data = response_data(response)

    assert process.process_id == data["process_id"]
    assert data["status"] == "CANCEL_REQUESTED"
    assert data["cancel_requested_at"] is not None


def test_run_not_found_uses_error_envelope(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    response = client.get("/api/v1/runs/missing", headers=auth_headers())

    assert response.status_code == 404
    assert response_error(response)["error_code"] == "WORKFLOW_RUN_NOT_FOUND"


def test_websocket_events_connects(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    with client.websocket_connect(f"/ws/v1/events?token={TOKEN}") as websocket:
        event = websocket.receive_json()

    assert event["event_type"] == "ENGINE_READY"
    assert event["event_id"]
    assert event["sequence_number"] == 1
    assert event["payload"] == {"status": "connected"}


def test_websocket_receives_workflow_process_runtime_event(tmp_path: Path) -> None:
    client, store, _container = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="WebSocket runtime event",
        definition=valid_definition(),
        workflow_id="workflow-1",
    )

    with client.websocket_connect(f"/ws/v1/events?token={TOKEN}") as websocket:
        ready = websocket.receive_json()
        assert ready["event_type"] == "ENGINE_READY"
        time.sleep(0.1)
        received: queue.Queue[object] = queue.Queue()

        def receive_one() -> None:
            try:
                received.put(websocket.receive_json())
            except Exception as exc:
                received.put(exc)

        thread = threading.Thread(target=receive_one, daemon=True)
        thread.start()
        started = response_data(
            client.post(
                f"/api/v1/workflows/{workflow.workflow_id}/runs",
                headers=auth_headers(),
            )
        )
        event = received.get(timeout=5)

    assert not isinstance(event, Exception)
    assert event["event_type"] == "WORKFLOW_STARTED"
    assert event["workflow_run_id"] == started["workflow_run_id"]


def test_runtime_events_can_be_restored_through_rest(tmp_path: Path) -> None:
    client, store, _container = make_client(tmp_path)
    store.append_runtime_event(
        EventModel(event_type=EventType.WORKFLOW_STARTED, payload={"run": "1"})
    )
    store.append_runtime_event(
        EventModel(event_type=EventType.NODE_STARTED, payload={"node": "a"})
    )

    response = client.get(
        "/api/v1/events",
        params={"after_sequence_number": 1},
        headers=auth_headers(),
    )
    data = response_data(response)

    assert [event["sequence_number"] for event in data] == [2]
    assert data[0]["event_type"] == "NODE_STARTED"


def test_create_app_can_migrate_default_store(tmp_path: Path) -> None:
    data_dir = tmp_path / "runtime"
    container = EngineHostBootstrap(
        EngineConfig(data_dir=data_dir, local_api_token=TOKEN)
    ).initialize()
    client = TestClient(create_app(container))

    response = client.get("/api/v1/workflows", headers=auth_headers())

    assert (data_dir / "metadata" / "flowweaver.db").exists()
    assert response_data(response) == []
    container.close()


def test_api_rejects_missing_token(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    response = client.get("/api/v1/workflows")

    assert response.status_code == 401
    assert response_error(response)["error_code"] == "UNAUTHORIZED"


def test_validate_api_rejects_unknown_node(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    response = client.post(
        "/api/v1/workflows/validate",
        json={
            "definition": {
                "schema_version": "1.0",
                "nodes": [
                    {
                        "node_instance_id": "n1",
                        "node_type": "missing.node",
                        "node_version": "1.0",
                    }
                ],
                "connections": [],
            },
        },
        headers=auth_headers(),
    )

    result = response_data(response)
    assert result["valid"] is False
    assert result["errors"][0]["code"] == "UNKNOWN_NODE_TYPE"
