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
from flowweaver.nodes.builtin_table import (
    CONDITION_FLAG_NODE_TYPE,
    CONDITIONAL_JUMP_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
    SAVE_RUN_TABLE_NODE_TYPE,
    SUB_WORKFLOW_NODE_TYPE,
)
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


def test_control_preview_nodes_run_as_plain_dag(
    tmp_path: Path,
) -> None:
    client, container = make_client(tmp_path)
    store = container.runtime_store
    try:
        workflow = response_data(
            client.post(
                "/api/v1/workflows",
                json={
                    "name": "Control preview DAG workflow",
                    "definition": {
                        "schema_version": "1.0",
                        "nodes": [
                            {
                                "node_instance_id": "generate",
                                "node_type": GENERATE_TEST_TABLE_NODE_TYPE,
                                "node_version": "1.0",
                                "config": {
                                    "rows": 2,
                                    "columns": ["row_id", "amount"],
                                    "seed": 0,
                                },
                            },
                            {
                                "node_instance_id": "condition",
                                "node_type": CONDITION_FLAG_NODE_TYPE,
                                "node_version": "1.0",
                                "config": {
                                    "condition_type": "row_count",
                                    "operator": "GE",
                                    "value": 1,
                                },
                            },
                            {
                                "node_instance_id": "conditional-jump",
                                "node_type": CONDITIONAL_JUMP_NODE_TYPE,
                                "node_version": "1.0",
                                "config": {
                                    "true_target_mode": "anchor",
                                    "true_target_anchor": "complete",
                                },
                            },
                            {
                                "node_instance_id": "subworkflow-preview",
                                "node_type": SUB_WORKFLOW_NODE_TYPE,
                                "node_version": "1.0",
                                "config": {
                                    "group_name": "preview_group",
                                    "nodes": [
                                        {
                                            "node_instance_id": "child-placeholder",
                                            "node_type": GENERATE_TEST_TABLE_NODE_TYPE,
                                        }
                                    ],
                                },
                            },
                            {
                                "node_instance_id": "save-status",
                                "node_type": SAVE_RUN_TABLE_NODE_TYPE,
                                "node_version": "1.0",
                                "config": {
                                    "transit_name": "control_status_transit",
                                },
                            },
                        ],
                        "connections": [
                            {
                                "connection_id": "generate-to-condition",
                                "source_node_id": "generate",
                                "source_port": "out",
                                "target_node_id": "condition",
                                "target_port": "in",
                            },
                            {
                                "connection_id": "condition-to-jump",
                                "source_node_id": "condition",
                                "source_port": "status",
                                "target_node_id": "conditional-jump",
                                "target_port": "condition",
                            },
                            {
                                "connection_id": "jump-to-subworkflow",
                                "source_node_id": "conditional-jump",
                                "source_port": "status",
                                "target_node_id": "subworkflow-preview",
                                "target_port": "in",
                            },
                            {
                                "connection_id": "subworkflow-to-save",
                                "source_node_id": "subworkflow-preview",
                                "source_port": "status",
                                "target_node_id": "save-status",
                                "target_port": "in",
                            },
                        ],
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
        node_runs = response_data(
            client.get(
                f"/api/v1/runs/{run.workflow_run_id}/nodes",
                headers=auth_headers(),
            )
        )
        table_refs = response_data(
            client.get(
                f"/api/v1/runs/{run.workflow_run_id}/table-refs",
                headers=auth_headers(),
            )
        )
        table_refs_by_name = {
            table_ref["logical_table_id"]: table_ref
            for table_ref in table_refs
        }
        control_status_ref = table_refs_by_name["conditional-jump_output"]
        control_rows = response_data(
            client.get(
                f"/api/v1/data/{control_status_ref['table_ref_id']}/rows",
                headers=auth_headers(),
            )
        )
        subworkflow_status_ref = table_refs_by_name["subworkflow-preview_output"]
        subworkflow_rows = response_data(
            client.get(
                f"/api/v1/data/{subworkflow_status_ref['table_ref_id']}/rows",
                headers=auth_headers(),
            )
        )

        assert run.status == WorkflowRunStatus.SUCCEEDED.value
        assert {
            node_run["node_instance_id"]: node_run["status"]
            for node_run in node_runs
        } == {
            "generate": "SUCCEEDED",
            "condition": "SUCCEEDED",
            "conditional-jump": "SUCCEEDED",
            "subworkflow-preview": "SUCCEEDED",
            "save-status": "SUCCEEDED",
        }
        assert control_rows["rows"] == [
            {
                "signal_type": "conditional_jump",
                "signal_status": "matched",
                "source_node_id": "conditional-jump",
                "target_node_id": "",
                "target_anchor": "complete",
                "condition_result": "true",
                "selected_branch": "true",
                "action": "jump_to_anchor",
                "actual_control": "false",
                "reason": "condition result is true",
                "details": control_rows["rows"][0]["details"],
            }
        ]
        assert subworkflow_rows["rows"][0] == {
            "signal_type": "subworkflow_plan",
            "signal_status": "planned",
            "source_node_id": "subworkflow-preview",
            "target_node_id": "",
            "target_anchor": "preview_group",
            "condition_result": "",
            "selected_branch": "",
            "action": "declare_subworkflow_plan",
            "actual_control": "false",
            "reason": "preview only; no child workflow run is created",
            "details": subworkflow_rows["rows"][0]["details"],
        }
        assert "control_status_transit" in table_refs_by_name
    finally:
        container.close()


def test_sql_mapping_node_definition_uses_generic_schema_contract(
    tmp_path: Path,
) -> None:
    client, container = make_client(tmp_path)
    try:
        definitions = response_data(
            client.get("/api/v1/node-definitions", headers=auth_headers())
        )
    finally:
        container.close()

    by_type = {definition["node_type"]: definition for definition in definitions}
    sql_mapping = by_type[SQL_MAPPING_NODE_TYPE]

    assert sql_mapping["display_name"] == "SQL Mapping"
    assert sql_mapping["input_ports"] == []
    assert sql_mapping["output_ports"] == [{"name": "out", "required": False}]
    assert set(sql_mapping["config_schema"]["properties"]) == {
        "database_path",
        "table_name",
        "query",
        "logical_table_id",
        "schema",
    }
    assert sql_mapping["config_schema"]["properties"]["database_path"][
        "required"
    ] is True
