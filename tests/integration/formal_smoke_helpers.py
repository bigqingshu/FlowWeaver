from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

TERMINAL_RUN_STATUSES = {"SUCCEEDED", "FAILED", "CANCELLED", "ABORTED"}


def prepare_enginehost_run_root(*, repo_root: Path, run_root: Path) -> None:
    run_root.mkdir()
    shutil.copy2(repo_root / "alembic.ini", run_root / "alembic.ini")
    shutil.copytree(repo_root / "migrations", run_root / "migrations")


def start_default_enginehost(
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


def wait_for_health(
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
                    "stderr": read_tail(stderr_path),
                }
            )
        try:
            return get_json(f"{base_url}/api/v1/health")
        except Exception as exc:  # pragma: no cover - failure detail only
            last_error = exc
            time.sleep(0.1)
    raise AssertionError(
        {
            "message": "EngineHost health did not become ok",
            "last_error": str(last_error),
            "stderr": read_tail(stderr_path),
        }
    )


def wait_for_terminal_run(
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
        run = response_data(
            get_json(f"{base_url}/api/v1/runs/{workflow_run_id}", token=token)
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
            "stderr": read_tail(stderr_path),
        }
    )


def collect_websocket_events(
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


def wait_for_runtime_events(
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
        events = response_data(
            get_json(
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


def get_json(url: str, *, token: str | None = None) -> dict[str, Any]:
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(
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


def response_data(response: dict[str, Any]) -> Any:
    assert response["ok"] is True
    assert response["error"] is None
    assert response["request_id"]
    return response["data"]


def runtime_events_websocket_url(*, port: int, token: str) -> str:
    query = urllib.parse.urlencode({"token": token})
    return f"ws://127.0.0.1:{port}/ws/v1/events?{query}"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def read_tail(path: Path, *, max_chars: int = 4000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]


def producer_definition(share_name: str) -> dict[str, Any]:
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
                    "share_name": share_name,
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


def consumer_definition(share_name: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "read",
                "node_type": "ReadSharedTablesNode",
                "node_version": "1.0",
                "config": {
                    "share_name": share_name,
                    "version_policy": "LATEST",
                    "selected_members": ["orders"],
                },
            }
        ],
        "connections": [],
    }
