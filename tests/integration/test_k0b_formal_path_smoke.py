from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from flowweaver.api.app import create_app
from flowweaver.common.config import EngineConfig
from flowweaver.engine.bootstrap import EngineHostBootstrap
from flowweaver.engine.runtime_store import RuntimeStore, WorkflowRun
from flowweaver.engine.service_container import ServiceContainer
from flowweaver.protocols.enums import (
    LifecycleStatus,
    WorkflowProcessStatus,
    WorkflowRunStatus,
)

TOKEN = "test-token"


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def response_data(response):
    payload = response.json()
    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["request_id"]
    return payload["data"]


def make_default_client(tmp_path: Path) -> tuple[TestClient, ServiceContainer]:
    container = EngineHostBootstrap(
        EngineConfig(
            data_dir=tmp_path / "runtime",
            local_api_token=TOKEN,
            enforce_single_instance=False,
            workflow_process_heartbeat_interval_seconds=0,
            supervisor_maintenance_interval_seconds=0.05,
        )
    ).initialize()
    return TestClient(create_app(container)), container


def wait_for_terminal_run(
    *,
    container: ServiceContainer,
    store: RuntimeStore,
    workflow_run_id: str,
    timeout_seconds: float = 10,
) -> WorkflowRun:
    deadline = time.monotonic() + timeout_seconds
    terminal_run: WorkflowRun | None = None
    while time.monotonic() < deadline:
        container.supervisor.sweep_exited_children()
        container.supervisor.drain_runtime_events()
        run = store.get_workflow_run(workflow_run_id)
        if run is not None and run.status in {
            WorkflowRunStatus.SUCCEEDED.value,
            WorkflowRunStatus.FAILED.value,
            WorkflowRunStatus.CANCELLED.value,
            WorkflowRunStatus.ABORTED.value,
        }:
            terminal_run = run
            process = store.get_workflow_process_for_run(workflow_run_id)
            if process is None or process.status in {
                WorkflowProcessStatus.EXITED.value,
                WorkflowProcessStatus.FAILED.value,
                WorkflowProcessStatus.LOST.value,
            }:
                return run
        time.sleep(0.05)
    if terminal_run is not None:
        process = store.get_workflow_process_for_run(workflow_run_id)
        raise AssertionError(
            {
                "message": "Workflow run finished before process cleanup completed",
                "workflow_run_id": workflow_run_id,
                "run_status": terminal_run.status,
                "process_status": process.status if process is not None else None,
            }
        )
    raise AssertionError(f"Workflow run did not finish: {workflow_run_id}")


def wait_for_websocket_subscription(
    container: ServiceContainer,
    *,
    timeout_seconds: float = 2,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if container.event_router._subscribers:
            return
        time.sleep(0.01)
    raise AssertionError("WebSocket event subscription was not registered")


def test_k0b_default_enginehost_runs_formal_table_and_shared_smoke(
    tmp_path: Path,
) -> None:
    client, container = make_default_client(tmp_path)
    store = container.runtime_store
    try:
        loaded = response_data(client.get("/api/v1/workflows", headers=auth_headers()))
        assert loaded == []

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
            wait_for_websocket_subscription(container)

            producer_workflow = response_data(
                client.post(
                    "/api/v1/workflows",
                    json={
                        "name": "K0b producer",
                        "definition": _producer_definition(),
                    },
                    headers=auth_headers(),
                )
            )
            producer_run = response_data(
                client.post(
                    f"/api/v1/workflows/{producer_workflow['workflow_id']}/runs",
                    headers=auth_headers(),
                )
            )
            producer = wait_for_terminal_run(
                container=container,
                store=store,
                workflow_run_id=producer_run["workflow_run_id"],
            )
            try:
                event = received.get(timeout=5)
            except queue.Empty as exc:
                stored_events = [
                    (item.sequence_number, item.event_type, item.workflow_run_id)
                    for item in store.list_runtime_events()
                ]
                process = store.get_workflow_process_for_run(
                    producer.workflow_run_id
                )
                node_runs = [
                    (node.node_instance_id, node.status, node.error)
                    for node in store.list_node_runs(producer.workflow_run_id)
                ]
                raise AssertionError(
                    {
                        "events": stored_events,
                        "run": (producer.status, producer.error),
                        "process": (
                            process.status if process is not None else None,
                            process.exit_code if process is not None else None,
                            process.error if process is not None else None,
                        ),
                        "nodes": node_runs,
                    }
                ) from exc

        assert not isinstance(event, Exception)
        assert event["event_type"] == "WORKFLOW_STARTED"
        assert event["workflow_run_id"] == producer.workflow_run_id
        assert producer.status == WorkflowRunStatus.SUCCEEDED.value

        api_node_runs = response_data(
            client.get(
                f"/api/v1/runs/{producer.workflow_run_id}/nodes",
                headers=auth_headers(),
            )
        )
        assert {node["node_instance_id"]: node["status"] for node in api_node_runs} == {
            "generate": "SUCCEEDED",
            "filter": "SUCCEEDED",
            "publish": "SUCCEEDED",
        }

        producer_refs = store.list_table_refs_by_workflow_run(
            producer.workflow_run_id
        )
        published_refs = [
            ref
            for ref in producer_refs
            if ref.lifecycle_status == LifecycleStatus.PUBLISHED
        ]
        assert len(published_refs) == 2
        publication = store.get_latest_shared_publication("k0b.orders")
        assert publication is not None
        assert publication.publication_version == 1
        assert [member.export_name for member in publication.members] == ["orders"]

        consumer_workflow = response_data(
            client.post(
                "/api/v1/workflows",
                json={
                    "name": "K0b consumer",
                    "definition": _consumer_definition(),
                },
                headers=auth_headers(),
            )
        )
        consumer_run = response_data(
            client.post(
                f"/api/v1/workflows/{consumer_workflow['workflow_id']}/runs",
                headers=auth_headers(),
            )
        )
        consumer = wait_for_terminal_run(
            container=container,
            store=store,
            workflow_run_id=consumer_run["workflow_run_id"],
        )
        assert consumer.status == WorkflowRunStatus.SUCCEEDED.value

        leases = store.list_read_leases_by_workflow_run(consumer.workflow_run_id)
        assert len(leases) == 1
        assert leases[0].released_at is not None
        assert (
            store.list_read_leases_by_workflow_run(
                consumer.workflow_run_id,
                active_only=True,
            )
            == []
        )

        restored_events = response_data(
            client.get("/api/v1/events", headers=auth_headers())
        )
        assert "WORKFLOW_STARTED" in {
            event["event_type"] for event in restored_events
        }

        with client.websocket_connect(f"/ws/v1/events?token={TOKEN}") as websocket:
            reconnected = websocket.receive_json()
        assert reconnected["event_type"] == "ENGINE_READY"
    finally:
        container.close()


def _producer_definition() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "generate",
                "node_type": "GenerateTestTableNode",
                "node_version": "1.0",
                "config": {
                    "rows": 3,
                    "columns": ["row_id", "amount"],
                },
            },
            {
                "node_instance_id": "filter",
                "node_type": "FilterRowsNode",
                "node_version": "1.0",
                "config": {
                    "field": "row_id",
                    "operator": "GE",
                    "value": 2,
                },
            },
            {
                "node_instance_id": "publish",
                "node_type": "PublishSharedTablesNode",
                "node_version": "1.0",
                "config": {
                    "share_name": "k0b.orders",
                    "export_names": ["orders"],
                },
            },
        ],
        "connections": [
            {
                "connection_id": "generate-filter",
                "source_node_id": "generate",
                "source_port": "out",
                "target_node_id": "filter",
                "target_port": "in",
            },
            {
                "connection_id": "filter-publish",
                "source_node_id": "filter",
                "source_port": "out",
                "target_node_id": "publish",
                "target_port": "in",
            },
        ],
    }


def _consumer_definition() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "read",
                "node_type": "ReadSharedTablesNode",
                "node_version": "1.0",
                "config": {
                    "share_name": "k0b.orders",
                    "version_policy": "LATEST",
                    "selected_members": ["orders"],
                },
            }
        ],
        "connections": [],
    }
