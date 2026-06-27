from __future__ import annotations

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
from flowweaver.nodes.registry import NodeRegistry
from flowweaver.protocols.enums import WorkflowRunStatus

TOKEN = "test-token"


def valid_definition() -> dict:
    return {"schema_version": "1.0", "nodes": [], "connections": []}


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def make_client(tmp_path: Path) -> tuple[TestClient, RuntimeStore, ServiceContainer]:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    container = ServiceContainer(
        config=EngineConfig(
            data_dir=tmp_path / "runtime",
            local_api_token=TOKEN,
            enforce_single_instance=False,
        ),
        runtime_store=store,
        event_router=EventRouter(store),
        node_registry=NodeRegistry(),
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
