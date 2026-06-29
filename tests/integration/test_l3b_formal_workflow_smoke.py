from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from websockets.sync.client import connect

TERMINAL_RUN_STATUSES = {"SUCCEEDED", "FAILED", "CANCELLED", "ABORTED"}


def test_l3b_default_enginehost_runs_formal_workflow_shared_and_websocket_smoke(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "enginehost-formal-workflow"
    run_root.mkdir()
    shutil.copy2(repo_root / "alembic.ini", run_root / "alembic.ini")
    shutil.copytree(repo_root / "migrations", run_root / "migrations")

    port = _free_port()
    stdout_path = run_root / "uvicorn.stdout.log"
    stderr_path = run_root / "uvicorn.stderr.log"
    process = _start_default_enginehost(
        repo_root=repo_root,
        run_root=run_root,
        port=port,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    try:
        base_url = f"http://127.0.0.1:{port}"
        _wait_for_health(
            process=process,
            base_url=base_url,
            stderr_path=stderr_path,
        )
        token = (run_root / "runtime" / "config" / "local_api_token").read_text(
            encoding="utf-8"
        ).strip()
        assert token

        websocket_url = _runtime_events_websocket_url(port=port, token=token)
        with connect(websocket_url, open_timeout=5, close_timeout=2) as websocket:
            ready = json.loads(websocket.recv(timeout=5))
            assert ready["event_type"] == "ENGINE_READY"

            producer_workflow = _response_data(
                _post_json(
                    f"{base_url}/api/v1/workflows",
                    token=token,
                    payload={
                        "name": "L3b producer",
                        "definition": _producer_definition(),
                    },
                )
            )
            listed_workflows = _response_data(
                _get_json(f"{base_url}/api/v1/workflows", token=token)
            )
            assert [item["workflow_id"] for item in listed_workflows] == [
                producer_workflow["workflow_id"]
            ]

            producer_run = _response_data(
                _post_json(
                    (
                        f"{base_url}/api/v1/workflows/"
                        f"{producer_workflow['workflow_id']}/runs"
                    ),
                    token=token,
                    payload=None,
                )
            )
            producer = _wait_for_terminal_run(
                base_url=base_url,
                token=token,
                workflow_run_id=producer_run["workflow_run_id"],
                stderr_path=stderr_path,
            )
            assert producer["status"] == "SUCCEEDED"

            websocket_events = _collect_websocket_events(
                websocket,
                workflow_run_id=producer["workflow_run_id"],
                required_event_types={"WORKFLOW_STARTED", "WORKFLOW_FINISHED"},
            )
            assert {
                item["event_type"] for item in websocket_events
            } >= {"WORKFLOW_STARTED", "WORKFLOW_FINISHED"}

        producer_nodes = _response_data(
            _get_json(
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

        producer_table_refs = _response_data(
            _get_json(
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

        publications = _response_data(
            _get_json(
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

        versions = _response_data(
            _get_json(
                f"{base_url}/api/v1/shared-publications/l3b.orders/versions",
                token=token,
            )
        )
        assert [item["publication_version"] for item in versions] == [1]

        consumer_workflow = _response_data(
            _post_json(
                f"{base_url}/api/v1/workflows",
                token=token,
                payload={
                    "name": "L3b consumer",
                    "definition": _consumer_definition(),
                },
            )
        )
        consumer_run = _response_data(
            _post_json(
                f"{base_url}/api/v1/workflows/{consumer_workflow['workflow_id']}/runs",
                token=token,
                payload=None,
            )
        )
        consumer = _wait_for_terminal_run(
            base_url=base_url,
            token=token,
            workflow_run_id=consumer_run["workflow_run_id"],
            stderr_path=stderr_path,
        )
        assert consumer["status"] == "SUCCEEDED"
        assert consumer["input_snapshot_id"] is not None

        consumer_nodes = _response_data(
            _get_json(
                f"{base_url}/api/v1/runs/{consumer['workflow_run_id']}/nodes",
                token=token,
            )
        )
        consumer_node_statuses = {
            node["node_instance_id"]: node["status"] for node in consumer_nodes
        }
        assert consumer_node_statuses == {"read": "SUCCEEDED"}

        consumer_table_refs = _response_data(
            _get_json(
                f"{base_url}/api/v1/runs/{consumer['workflow_run_id']}/table-refs",
                token=token,
            )
        )
        assert consumer_table_refs == []

        producer_events = _wait_for_runtime_events(
            base_url=base_url,
            token=token,
            workflow_run_id=producer["workflow_run_id"],
            required_event_types={"WORKFLOW_STARTED", "WORKFLOW_FINISHED"},
        )
        assert {event["event_type"] for event in producer_events} >= {
            "WORKFLOW_STARTED",
            "WORKFLOW_FINISHED",
        }

        consumer_events = _wait_for_runtime_events(
            base_url=base_url,
            token=token,
            workflow_run_id=consumer["workflow_run_id"],
            required_event_types={"WORKFLOW_STARTED", "WORKFLOW_FINISHED"},
        )
        assert {event["event_type"] for event in consumer_events} >= {
            "WORKFLOW_STARTED",
            "WORKFLOW_FINISHED",
        }

        producer_audit = _response_data(
            _get_json(
                (
                    f"{base_url}/api/v1/audit-events?"
                    f"workflow_run_id={producer['workflow_run_id']}"
                ),
                token=token,
            )
        )
        consumer_audit = _response_data(
            _get_json(
                (
                    f"{base_url}/api/v1/audit-events?"
                    f"workflow_run_id={consumer['workflow_run_id']}"
                ),
                token=token,
            )
        )
        assert producer_audit
        assert consumer_audit

        all_runs = _response_data(_get_json(f"{base_url}/api/v1/runs", token=token))
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
        _stop_process(process)


def _start_default_enginehost(
    *,
    repo_root: Path,
    run_root: Path,
    port: int,
    stdout_path: Path,
    stderr_path: Path,
) -> subprocess.Popen[bytes]:
    stdout_file = stdout_path.open("wb")
    stderr_file = stderr_path.open("wb")
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "--app-dir",
                str(repo_root / "src"),
                "flowweaver.api.app:create_default_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=run_root,
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
        )
    finally:
        stdout_file.close()
        stderr_file.close()
    return process


def _wait_for_health(
    *,
    process: subprocess.Popen[bytes],
    base_url: str,
    stderr_path: Path,
    timeout_seconds: float = 20,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(
                {
                    "message": "EngineHost exited before health became ok",
                    "exit_code": process.returncode,
                    "stderr": _read_tail(stderr_path),
                }
            )
        try:
            return _get_json(f"{base_url}/api/v1/health")
        except Exception as exc:  # pragma: no cover - failure detail only
            last_error = exc
            time.sleep(0.1)
    raise AssertionError(
        {
            "message": "EngineHost health did not become ok",
            "last_error": str(last_error),
            "stderr": _read_tail(stderr_path),
        }
    )


def _wait_for_terminal_run(
    *,
    base_url: str,
    token: str,
    workflow_run_id: str,
    stderr_path: Path,
    timeout_seconds: float = 20,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_run: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        run = _response_data(
            _get_json(f"{base_url}/api/v1/runs/{workflow_run_id}", token=token)
        )
        last_run = run
        if run["status"] in TERMINAL_RUN_STATUSES:
            return run
        time.sleep(0.2)
    raise AssertionError(
        {
            "message": "Workflow run did not finish",
            "workflow_run_id": workflow_run_id,
            "last_run": last_run,
            "stderr": _read_tail(stderr_path),
        }
    )


def _collect_websocket_events(
    websocket: Any,
    *,
    workflow_run_id: str,
    required_event_types: set[str],
    timeout_seconds: float = 10,
) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    events: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        remaining = max(0.1, deadline - time.monotonic())
        try:
            message = websocket.recv(timeout=remaining)
        except TimeoutError:
            break
        event = json.loads(message)
        if event.get("workflow_run_id") == workflow_run_id:
            events.append(event)
            if required_event_types.issubset(
                {item["event_type"] for item in events}
            ):
                return events
    raise AssertionError(
        {
            "message": "Required WebSocket runtime events were not observed",
            "workflow_run_id": workflow_run_id,
            "required_event_types": sorted(required_event_types),
            "observed_event_types": sorted({item["event_type"] for item in events}),
        }
    )


def _wait_for_runtime_events(
    *,
    base_url: str,
    token: str,
    workflow_run_id: str,
    required_event_types: set[str],
    timeout_seconds: float = 10,
) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    events: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        events = _response_data(
            _get_json(
                f"{base_url}/api/v1/events?workflow_run_id={workflow_run_id}",
                token=token,
            )
        )
        if required_event_types.issubset({event["event_type"] for event in events}):
            return events
        time.sleep(0.2)
    raise AssertionError(
        {
            "message": "Required REST runtime events were not observed",
            "workflow_run_id": workflow_run_id,
            "required_event_types": sorted(required_event_types),
            "observed_event_types": sorted({event["event_type"] for event in events}),
        }
    )


def _get_json(url: str, *, token: str | None = None) -> dict[str, Any]:
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(
    url: str,
    *,
    token: str,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _response_data(response: dict[str, Any]) -> Any:
    assert response["ok"] is True
    assert response["error"] is None
    assert response["request_id"]
    return response["data"]


def _runtime_events_websocket_url(*, port: int, token: str) -> str:
    query = urllib.parse.urlencode({"token": token})
    return f"ws://127.0.0.1:{port}/ws/v1/events?{query}"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _read_tail(path: Path, *, max_chars: int = 4000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]


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
                    "share_name": "l3b.orders",
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
                    "share_name": "l3b.orders",
                    "version_policy": "LATEST",
                    "selected_members": ["orders"],
                },
            }
        ],
        "connections": [],
    }
