from __future__ import annotations

import json
from pathlib import Path

from formal_smoke_helpers import (
    consumer_definition,
    free_port,
    get_json,
    post_json,
    prepare_enginehost_run_root,
    producer_definition,
    response_data,
    runtime_events_websocket_url,
    start_default_enginehost,
    stop_process,
    wait_for_health,
    wait_for_runtime_events,
    wait_for_terminal_run,
)
from websockets.sync.client import connect


def test_l3c_default_enginehost_restores_state_after_restart(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "enginehost-restart-runtime"
    prepare_enginehost_run_root(repo_root=repo_root, run_root=run_root)

    first_port = free_port()
    first_base_url = f"http://127.0.0.1:{first_port}"
    first_stderr_path = run_root / "uvicorn.first.stderr.log"
    first_process = start_default_enginehost(
        repo_root=repo_root,
        run_root=run_root,
        port=first_port,
        stdout_path=run_root / "uvicorn.first.stdout.log",
        stderr_path=first_stderr_path,
    )
    try:
        wait_for_health(
            process=first_process,
            base_url=first_base_url,
            stderr_path=first_stderr_path,
        )
        token_path = run_root / "runtime" / "config" / "local_api_token"
        first_token = token_path.read_text(encoding="utf-8").strip()
        assert first_token

        producer_workflow = response_data(
            post_json(
                f"{first_base_url}/api/v1/workflows",
                token=first_token,
                payload={
                    "name": "L3c producer",
                    "definition": producer_definition("l3c.orders"),
                },
            )
        )
        producer_run = response_data(
            post_json(
                (
                    f"{first_base_url}/api/v1/workflows/"
                    f"{producer_workflow['workflow_id']}/runs"
                ),
                token=first_token,
                payload=None,
            )
        )
        producer = wait_for_terminal_run(
            base_url=first_base_url,
            token=first_token,
            workflow_run_id=producer_run["workflow_run_id"],
            stderr_path=first_stderr_path,
        )
        assert producer["status"] == "SUCCEEDED"

        consumer_workflow = response_data(
            post_json(
                f"{first_base_url}/api/v1/workflows",
                token=first_token,
                payload={
                    "name": "L3c consumer",
                    "definition": consumer_definition("l3c.orders"),
                },
            )
        )
        consumer_run = response_data(
            post_json(
                (
                    f"{first_base_url}/api/v1/workflows/"
                    f"{consumer_workflow['workflow_id']}/runs"
                ),
                token=first_token,
                payload=None,
            )
        )
        consumer = wait_for_terminal_run(
            base_url=first_base_url,
            token=first_token,
            workflow_run_id=consumer_run["workflow_run_id"],
            stderr_path=first_stderr_path,
        )
        assert consumer["status"] == "SUCCEEDED"

        wait_for_runtime_events(
            base_url=first_base_url,
            token=first_token,
            workflow_run_id=producer["workflow_run_id"],
            required_event_types={"WORKFLOW_STARTED", "WORKFLOW_FINISHED"},
        )
        wait_for_runtime_events(
            base_url=first_base_url,
            token=first_token,
            workflow_run_id=consumer["workflow_run_id"],
            required_event_types={"WORKFLOW_STARTED", "WORKFLOW_FINISHED"},
        )
    finally:
        stop_process(first_process)

    second_port = free_port()
    second_base_url = f"http://127.0.0.1:{second_port}"
    second_stderr_path = run_root / "uvicorn.second.stderr.log"
    second_process = start_default_enginehost(
        repo_root=repo_root,
        run_root=run_root,
        port=second_port,
        stdout_path=run_root / "uvicorn.second.stdout.log",
        stderr_path=second_stderr_path,
    )
    try:
        wait_for_health(
            process=second_process,
            base_url=second_base_url,
            stderr_path=second_stderr_path,
        )
        second_token = token_path.read_text(encoding="utf-8").strip()
        assert second_token == first_token

        workflows = response_data(
            get_json(f"{second_base_url}/api/v1/workflows", token=second_token)
        )
        assert {item["workflow_id"] for item in workflows} == {
            producer_workflow["workflow_id"],
            consumer_workflow["workflow_id"],
        }

        runs = response_data(
            get_json(f"{second_base_url}/api/v1/runs", token=second_token)
        )
        assert {
            item["workflow_run_id"]: item["status"] for item in runs
        } == {
            producer["workflow_run_id"]: "SUCCEEDED",
            consumer["workflow_run_id"]: "SUCCEEDED",
        }

        producer_nodes = response_data(
            get_json(
                f"{second_base_url}/api/v1/runs/{producer['workflow_run_id']}/nodes",
                token=second_token,
            )
        )
        assert {
            node["node_instance_id"]: node["status"] for node in producer_nodes
        } == {
            "generate": "SUCCEEDED",
            "filter": "SUCCEEDED",
            "publish": "SUCCEEDED",
        }

        consumer_nodes = response_data(
            get_json(
                f"{second_base_url}/api/v1/runs/{consumer['workflow_run_id']}/nodes",
                token=second_token,
            )
        )
        assert {
            node["node_instance_id"]: node["status"] for node in consumer_nodes
        } == {"read": "SUCCEEDED"}

        producer_table_refs = response_data(
            get_json(
                (
                    f"{second_base_url}/api/v1/runs/"
                    f"{producer['workflow_run_id']}/table-refs"
                ),
                token=second_token,
            )
        )
        assert len(
            [
                ref
                for ref in producer_table_refs
                if ref["lifecycle_status"] == "PUBLISHED"
            ]
        ) == 2

        publications = response_data(
            get_json(
                f"{second_base_url}/api/v1/shared-publications?share_name=l3c.orders",
                token=second_token,
            )
        )
        assert [item["publication_version"] for item in publications] == [1]

        versions = response_data(
            get_json(
                f"{second_base_url}/api/v1/shared-publications/l3c.orders/versions",
                token=second_token,
            )
        )
        assert [item["publication_version"] for item in versions] == [1]

        producer_events = response_data(
            get_json(
                (
                    f"{second_base_url}/api/v1/events?"
                    f"workflow_run_id={producer['workflow_run_id']}"
                ),
                token=second_token,
            )
        )
        consumer_events = response_data(
            get_json(
                (
                    f"{second_base_url}/api/v1/events?"
                    f"workflow_run_id={consumer['workflow_run_id']}"
                ),
                token=second_token,
            )
        )
        assert {event["event_type"] for event in producer_events} >= {
            "WORKFLOW_STARTED",
            "WORKFLOW_FINISHED",
        }
        assert {event["event_type"] for event in consumer_events} >= {
            "WORKFLOW_STARTED",
            "WORKFLOW_FINISHED",
        }

        producer_audit = response_data(
            get_json(
                (
                    f"{second_base_url}/api/v1/audit-events?"
                    f"workflow_run_id={producer['workflow_run_id']}"
                ),
                token=second_token,
            )
        )
        consumer_audit = response_data(
            get_json(
                (
                    f"{second_base_url}/api/v1/audit-events?"
                    f"workflow_run_id={consumer['workflow_run_id']}"
                ),
                token=second_token,
            )
        )
        assert producer_audit
        assert consumer_audit

        websocket_url = runtime_events_websocket_url(
            port=second_port,
            token=second_token,
        )
        with connect(websocket_url, open_timeout=5, close_timeout=2) as websocket:
            ready = json.loads(websocket.recv(timeout=5))
        assert ready["event_type"] == "ENGINE_READY"
    finally:
        stop_process(second_process)
