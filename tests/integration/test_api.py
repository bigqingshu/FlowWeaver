from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from alembic import command
from alembic.config import Config

from workflow_platform.api.app import create_app
from workflow_platform.engine.runtime_store import RuntimeStore, sqlite_url
from workflow_platform.protocols.enums import WorkflowRunStatus


def make_client(tmp_path: Path) -> tuple[TestClient, RuntimeStore]:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    return TestClient(create_app(runtime_store=store)), store


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
    client, _store = make_client(tmp_path)

    response = client.get("/api/v1/health", headers={"x-request-id": "request-1"})

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {"status": "ok"},
        "error": None,
        "request_id": "request-1",
    }


def test_workflow_crud_api(tmp_path: Path) -> None:
    client, _store = make_client(tmp_path)

    created = response_data(
        client.post(
            "/api/v1/workflows",
            json={"name": "API workflow", "definition": {"nodes": []}},
        )
    )
    workflow_id = created["workflow_id"]

    assert created["name"] == "API workflow"
    assert created["version"] == 1

    loaded = response_data(client.get(f"/api/v1/workflows/{workflow_id}"))
    listed = response_data(client.get("/api/v1/workflows"))
    updated = response_data(
        client.put(
            f"/api/v1/workflows/{workflow_id}",
            json={"definition": {"nodes": [{"id": "n1"}]}},
        )
    )
    deleted = response_data(client.delete(f"/api/v1/workflows/{workflow_id}"))

    assert loaded["workflow_id"] == workflow_id
    assert [item["workflow_id"] for item in listed] == [workflow_id]
    assert updated["version"] == 2
    assert updated["definition"]["nodes"] == [{"id": "n1"}]
    assert deleted == {"workflow_id": workflow_id, "deleted": True}


def test_workflow_not_found_uses_error_envelope(tmp_path: Path) -> None:
    client, _store = make_client(tmp_path)

    response = client.get("/api/v1/workflows/missing")

    assert response.status_code == 404
    error = response_error(response)
    assert error["error_code"] == "WORKFLOW_NOT_FOUND"
    assert error["retryable"] is False


def test_run_query_api(tmp_path: Path) -> None:
    client, store = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="Run source",
        definition={"nodes": []},
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_version=workflow.version,
        workflow_run_id="run-1",
        status=WorkflowRunStatus.PENDING,
    )

    listed = response_data(client.get("/api/v1/runs"))
    loaded = response_data(client.get(f"/api/v1/runs/{run.workflow_run_id}"))
    filtered = response_data(client.get("/api/v1/runs", params={"status": "PENDING"}))

    assert [item["workflow_run_id"] for item in listed] == ["run-1"]
    assert loaded["workflow_id"] == "workflow-1"
    assert filtered[0]["status"] == "PENDING"


def test_run_not_found_uses_error_envelope(tmp_path: Path) -> None:
    client, _store = make_client(tmp_path)

    response = client.get("/api/v1/runs/missing")

    assert response.status_code == 404
    assert response_error(response)["error_code"] == "WORKFLOW_RUN_NOT_FOUND"


def test_websocket_events_connects(tmp_path: Path) -> None:
    client, _store = make_client(tmp_path)

    with client.websocket_connect("/ws/v1/events") as websocket:
        event = websocket.receive_json()

    assert event["event_type"] == "ENGINE_READY"
    assert event["payload"] == {"status": "connected"}


def test_create_app_can_migrate_default_store(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime" / "metadata" / "flowweaver.db"
    client = TestClient(create_app(database_url=sqlite_url(database_path)))

    response = client.get("/api/v1/workflows")

    assert database_path.exists()
    assert response_data(response) == []
