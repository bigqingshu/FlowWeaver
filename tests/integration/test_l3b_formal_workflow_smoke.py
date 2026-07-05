from __future__ import annotations

import json
from pathlib import Path

from formal_smoke_helpers import (
    collect_websocket_events,
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


def test_l3b_default_enginehost_runs_formal_workflow_shared_and_websocket_smoke(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "enginehost-formal-workflow"
    prepare_enginehost_run_root(repo_root=repo_root, run_root=run_root)

    port = free_port()
    stdout_path = run_root / "uvicorn.stdout.log"
    stderr_path = run_root / "uvicorn.stderr.log"
    process = start_default_enginehost(
        repo_root=repo_root,
        run_root=run_root,
        port=port,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    try:
        base_url = f"http://127.0.0.1:{port}"
        wait_for_health(
            process=process,
            base_url=base_url,
            stderr_path=stderr_path,
        )
        token = (run_root / "runtime" / "config" / "local_api_token").read_text(
            encoding="utf-8"
        ).strip()
        assert token

        websocket_url = runtime_events_websocket_url(port=port, token=token)
        with connect(websocket_url, open_timeout=5, close_timeout=2) as websocket:
            ready = json.loads(websocket.recv(timeout=5))
            assert ready["event_type"] == "ENGINE_READY"

            producer_workflow = response_data(
                post_json(
                    f"{base_url}/api/v1/workflows",
                    token=token,
                    payload={
                        "name": "L3b producer",
                        "definition": producer_definition("l3b.orders"),
                    },
                )
            )
            listed_workflows = response_data(
                get_json(f"{base_url}/api/v1/workflows", token=token)
            )
            assert [item["workflow_id"] for item in listed_workflows] == [
                producer_workflow["workflow_id"]
            ]

            producer_run = response_data(
                post_json(
                    (
                        f"{base_url}/api/v1/workflows/"
                        f"{producer_workflow['workflow_id']}/runs"
                    ),
                    token=token,
                    payload=None,
                )
            )
            producer = wait_for_terminal_run(
                base_url=base_url,
                token=token,
                workflow_run_id=producer_run["workflow_run_id"],
                stderr_path=stderr_path,
            )
            assert producer["status"] == "SUCCEEDED"

            websocket_events = collect_websocket_events(
                websocket,
                workflow_run_id=producer["workflow_run_id"],
                required_event_types={"WORKFLOW_STARTED", "WORKFLOW_FINISHED"},
            )
            assert {
                item["event_type"] for item in websocket_events
            } >= {"WORKFLOW_STARTED", "WORKFLOW_FINISHED"}

        producer_nodes = response_data(
            get_json(
                f"{base_url}/api/v1/runs/{producer['workflow_run_id']}/nodes",
                token=token,
            )
        )
        producer_node_statuses = {
            node["node_instance_id"]: node["status"] for node in producer_nodes
        }
        assert producer_node_statuses == {
            "generate": "SUCCEEDED",
            "filter": "SUCCEEDED",
            "publish": "SUCCEEDED",
        }

        producer_table_refs = response_data(
            get_json(
                f"{base_url}/api/v1/runs/{producer['workflow_run_id']}/table-refs",
                token=token,
            )
        )
        published_refs = [
            ref
            for ref in producer_table_refs
            if ref["lifecycle_status"] == "PUBLISHED"
        ]
        assert len(published_refs) == 2

        publications = response_data(
            get_json(
                f"{base_url}/api/v1/shared-publications?share_name=l3b.orders",
                token=token,
            )
        )
        assert len(publications) == 1
        assert publications[0]["share_name"] == "l3b.orders"
        assert publications[0]["publication_version"] == 1
        assert [member["export_name"] for member in publications[0]["members"]] == [
            "orders"
        ]

        versions = response_data(
            get_json(
                f"{base_url}/api/v1/shared-publications/l3b.orders/versions",
                token=token,
            )
        )
        assert [item["publication_version"] for item in versions] == [1]

        consumer_workflow = response_data(
            post_json(
                f"{base_url}/api/v1/workflows",
                token=token,
                payload={
                    "name": "L3b consumer",
                    "definition": consumer_definition("l3b.orders"),
                },
            )
        )
        consumer_run = response_data(
            post_json(
                f"{base_url}/api/v1/workflows/{consumer_workflow['workflow_id']}/runs",
                token=token,
                payload=None,
            )
        )
        consumer = wait_for_terminal_run(
            base_url=base_url,
            token=token,
            workflow_run_id=consumer_run["workflow_run_id"],
            stderr_path=stderr_path,
        )
        assert consumer["status"] == "SUCCEEDED"
        assert consumer["input_snapshot_id"] is not None

        consumer_nodes = response_data(
            get_json(
                f"{base_url}/api/v1/runs/{consumer['workflow_run_id']}/nodes",
                token=token,
            )
        )
        consumer_node_statuses = {
            node["node_instance_id"]: node["status"] for node in consumer_nodes
        }
        assert consumer_node_statuses == {"read": "SUCCEEDED"}

        consumer_table_refs = response_data(
            get_json(
                f"{base_url}/api/v1/runs/{consumer['workflow_run_id']}/table-refs",
                token=token,
            )
        )
        assert consumer_table_refs == []

        producer_events = wait_for_runtime_events(
            base_url=base_url,
            token=token,
            workflow_run_id=producer["workflow_run_id"],
            required_event_types={"WORKFLOW_STARTED", "WORKFLOW_FINISHED"},
        )
        assert {event["event_type"] for event in producer_events} >= {
            "WORKFLOW_STARTED",
            "WORKFLOW_FINISHED",
        }

        consumer_events = wait_for_runtime_events(
            base_url=base_url,
            token=token,
            workflow_run_id=consumer["workflow_run_id"],
            required_event_types={"WORKFLOW_STARTED", "WORKFLOW_FINISHED"},
        )
        assert {event["event_type"] for event in consumer_events} >= {
            "WORKFLOW_STARTED",
            "WORKFLOW_FINISHED",
        }

        all_runs = response_data(get_json(f"{base_url}/api/v1/runs", token=token))
        assert {
            item["workflow_run_id"]: item["status"] for item in all_runs
        } == {
            producer["workflow_run_id"]: "SUCCEEDED",
            consumer["workflow_run_id"]: "SUCCEEDED",
        }

        with connect(websocket_url, open_timeout=5, close_timeout=2) as websocket:
            reconnected = json.loads(websocket.recv(timeout=5))
        assert reconnected["event_type"] == "ENGINE_READY"
    finally:
        stop_process(process)
