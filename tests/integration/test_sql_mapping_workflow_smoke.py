from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from flowweaver.api.app import create_app
from flowweaver.common.config import EngineConfig
from flowweaver.engine.bootstrap import EngineHostBootstrap
from flowweaver.engine.runtime_store import RuntimeStore, WorkflowRun
from flowweaver.engine.service_container import ServiceContainer
from flowweaver.nodes.builtin_sql import SQL_MAPPING_NODE_TYPE
from flowweaver.protocols.enums import WorkflowProcessStatus, WorkflowRunStatus

TOKEN = "test-token"


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def response_data(response):
    payload = response.json()
    assert payload["ok"] is True
    assert payload["error"] is None
    return payload["data"]


def make_external_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "external.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE orders (row_id INTEGER NOT NULL, amount REAL NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO orders (row_id, amount) VALUES (?, ?)",
            [(1, 8.0), (2, 12.5)],
        )
    return database_path


def make_client(tmp_path: Path) -> tuple[TestClient, ServiceContainer]:
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
            process = store.get_workflow_process_for_run(workflow_run_id)
            if process is None or process.status in {
                WorkflowProcessStatus.EXITED.value,
                WorkflowProcessStatus.FAILED.value,
                WorkflowProcessStatus.LOST.value,
            }:
                return run
        time.sleep(0.05)
    raise AssertionError(f"Workflow run did not finish: {workflow_run_id}")


def test_sql_mapping_workflow_run_exposes_external_sql_rows(
    tmp_path: Path,
) -> None:
    external_database_path = make_external_database(tmp_path)
    client, container = make_client(tmp_path)
    store = container.runtime_store
    try:
        workflow = response_data(
            client.post(
                "/api/v1/workflows",
                json={
                    "name": "SQL mapping workflow",
                    "definition": {
                        "schema_version": "1.0",
                        "nodes": [
                            {
                                "node_instance_id": "sql-source",
                                "node_type": SQL_MAPPING_NODE_TYPE,
                                "node_version": "1.0",
                                "config": {
                                    "database_path": external_database_path.as_posix(),
                                    "table_name": "orders",
                                    "logical_table_id": "orders",
                                },
                            }
                        ],
                        "connections": [],
                    },
                },
                headers=auth_headers(),
            )
        )
        started = response_data(
            client.post(
                f"/api/v1/workflows/{workflow['workflow_id']}/runs",
                headers=auth_headers(),
            )
        )

        run = wait_for_terminal_run(
            container=container,
            store=store,
            workflow_run_id=started["workflow_run_id"],
        )
        table_refs = response_data(
            client.get(
                f"/api/v1/runs/{run.workflow_run_id}/table-refs",
                headers=auth_headers(),
            )
        )
        assert run.status == WorkflowRunStatus.SUCCEEDED.value
        assert len(table_refs) == 1
        assert table_refs[0]["storage_kind"] == "EXTERNAL_SQL"
        assert table_refs[0]["logical_table_id"] == "orders"

        rows = response_data(
            client.get(
                f"/api/v1/data/{table_refs[0]['table_ref_id']}/rows",
                params=[("order_by", "row_id")],
                headers=auth_headers(),
            )
        )
        assert rows["rows"] == [
            {"row_id": 1, "amount": 8.0},
            {"row_id": 2, "amount": 12.5},
        ]
    finally:
        container.close()

