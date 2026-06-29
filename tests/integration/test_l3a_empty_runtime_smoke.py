from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest


def test_l3a_default_enginehost_creates_empty_runtime_and_returns_empty_lists(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "enginehost-empty-runtime"
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
        health = _wait_for_health(
            process=process,
            base_url=base_url,
            stderr_path=stderr_path,
        )
        assert health["ok"] is True
        assert health["data"]["status"] == "ok"

        runtime_dir = run_root / "runtime"
        assert (runtime_dir / "metadata" / "flowweaver.db").is_file()
        assert (runtime_dir / "config" / "local_api_token").is_file()
        assert (runtime_dir / "workflow_runs").is_dir()
        assert (runtime_dir / "logs").is_dir()
        assert (runtime_dir / "temp").is_dir()

        token = (runtime_dir / "config" / "local_api_token").read_text(
            encoding="utf-8"
        ).strip()
        assert token

        expected_empty_routes = (
            "/api/v1/workflows",
            "/api/v1/runs",
            "/api/v1/events",
            "/api/v1/audit-events",
            "/api/v1/shared-publications",
        )
        for route in expected_empty_routes:
            payload = _get_json(f"{base_url}{route}", token=token)
            assert payload["ok"] is True
            assert payload["error"] is None
            assert payload["data"] == []

        with pytest.raises(urllib.error.HTTPError) as error:
            _get_json(f"{base_url}/api/v1/workflows", token="invalid-token")
        assert error.value.code == 401
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


def _get_json(url: str, *, token: str | None = None) -> dict[str, Any]:
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


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
