from __future__ import annotations

import importlib.util
import json
import os
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from types import ModuleType
from typing import Any

from formal_smoke_helpers import free_port, get_json, response_data


def test_o4_portable_launcher_no_desktop_runs_enginehost_end_to_end() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    create_portable_layout = _load_create_portable_layout(repo_root)
    output_dir = (
        repo_root
        / ".tmp"
        / f"FlowWeaverPortableLauncherTest-{uuid.uuid4().hex}"
    )
    portable_dir = create_portable_layout(
        repo_root=repo_root,
        output_dir=output_dir,
        include_python=True,
        include_desktop_build=False,
    )

    enginehost_dir = portable_dir / "EngineHost"
    python_exe = enginehost_dir / "python312" / "python.exe"
    log_dir = enginehost_dir / "runtime" / "logs"
    launcher_log_path = log_dir / "portable-launcher.log"
    engine_stdout_path = log_dir / "enginehost.stdout.log"
    engine_stderr_path = log_dir / "enginehost.stderr.log"
    token_path = enginehost_dir / "runtime" / "config" / "local_api_token"
    enginehost_lock_path = enginehost_dir / "runtime" / "enginehost.lock"
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"

    process: subprocess.Popen[bytes] | None = None
    stdout_text = ""
    stderr_text = ""
    stop_returncode: int | None = None
    token: str | None = None
    health_ready = False
    launcher_log_after_stop = ""
    engine_stdout_after_stop = ""
    engine_stderr_after_stop = ""

    try:
        try:
            process = _start_portable_launcher(
                portable_dir=portable_dir,
                python_exe=python_exe,
                port=port,
            )

            health = _wait_for_health(process=process, base_url=base_url)
            health_ready = True
            assert health["ok"] is True
            assert health["data"]["status"] == "ok"

            token = _wait_for_token(token_path=token_path, process=process)
            workflows = response_data(
                get_json(f"{base_url}/api/v1/workflows", token=token)
            )
            assert workflows == []

            assert engine_stdout_path.is_file()
            assert engine_stderr_path.is_file()
            assert launcher_log_path.is_file()

            launcher_log = _wait_for_text(
                launcher_log_path,
                expected="EngineHost ready",
                process=process,
            )
            assert "EngineHost ready" in launcher_log
            assert f"BaseUrl={base_url}" in launcher_log
            assert f"token_file={token_path}" in launcher_log
            assert token not in launcher_log
        finally:
            if process is not None:
                stdout_text, stderr_text, stop_returncode = (
                    _stop_launcher_gracefully(process)
                )
                launcher_log_after_stop = _read_text(launcher_log_path)
                engine_stdout_after_stop = _read_text(engine_stdout_path)
                engine_stderr_after_stop = _read_text(engine_stderr_path)
            if health_ready:
                _wait_until_health_unreachable(base_url)
                assert not enginehost_lock_path.exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)

    assert stop_returncode in {0, 130}
    assert "EngineHost ready." in stdout_text
    assert f"BaseUrl: {base_url}" in stdout_text
    assert f"Token file: {token_path}" in stdout_text

    if token is not None:
        assert token not in stdout_text
        assert token not in stderr_text
        assert token not in engine_stdout_after_stop
        assert token not in engine_stderr_after_stop
        assert token not in launcher_log_after_stop

    assert "Launcher interrupted by user" in launcher_log_after_stop
    assert "EngineHost stopped" in launcher_log_after_stop


def _load_create_portable_layout(repo_root: Path):
    module_path = repo_root / "tools" / "create_portable_layout.py"
    spec = importlib.util.spec_from_file_location(
        "flowweaver_create_portable_layout_o4",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    assert isinstance(module, ModuleType)
    spec.loader.exec_module(module)
    return module.create_portable_layout


def _start_portable_launcher(
    *,
    portable_dir: Path,
    python_exe: Path,
    port: int,
) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    kwargs: dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(
        [
            str(python_exe),
            "portable_launcher.py",
            "--no-desktop",
            "--port",
            str(port),
            "--health-timeout-seconds",
            "20",
        ],
        cwd=portable_dir,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    )


def _wait_for_health(
    *,
    process: subprocess.Popen[bytes],
    base_url: str,
    timeout_seconds: float = 20,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(
                {
                    "message": "launcher exited before EngineHost health was ok",
                    "exit_code": process.returncode,
                    "stdout": _pipe_tail(process.stdout),
                    "stderr": _pipe_tail(process.stderr),
                }
            )
        try:
            return _get_json_short(f"{base_url}/api/v1/health")
        except Exception as exc:  # pragma: no cover - failure detail only
            last_error = exc
            time.sleep(0.1)
    raise AssertionError(
        {
            "message": "EngineHost health did not become ok through launcher",
            "last_error": str(last_error),
        }
    )


def _wait_for_token(
    *,
    token_path: Path,
    process: subprocess.Popen[bytes],
    timeout_seconds: float = 20,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(
                {
                    "message": "launcher exited before token was ready",
                    "exit_code": process.returncode,
                }
            )
        if token_path.is_file():
            token = token_path.read_text(encoding="utf-8").strip()
            if token:
                return token
        time.sleep(0.1)
    raise AssertionError(f"token file was not ready: {token_path}")


def _wait_for_text(
    path: Path,
    *,
    expected: str,
    process: subprocess.Popen[bytes],
    timeout_seconds: float = 5,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    content = ""
    while time.monotonic() < deadline:
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
            if expected in content:
                return content
        if process.poll() is not None:
            raise AssertionError(
                {
                    "message": f"launcher exited before {expected!r} was logged",
                    "exit_code": process.returncode,
                    "content": content,
                }
            )
        time.sleep(0.1)
    raise AssertionError(
        {
            "message": f"timed out waiting for {expected!r}",
            "path": str(path),
            "content": content,
        }
    )


def _stop_launcher_gracefully(
    process: subprocess.Popen[bytes],
) -> tuple[str, str, int | None]:
    if process.poll() is None:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.send_signal(signal.SIGINT)
    try:
        stdout, stderr = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
    return (
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
        process.returncode,
    )


def _wait_until_health_unreachable(
    base_url: str,
    *,
    timeout_seconds: float = 5,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            _get_json_short(f"{base_url}/api/v1/health", timeout_seconds=0.5)
        except (OSError, TimeoutError, urllib.error.URLError):
            return
        time.sleep(0.1)
    raise AssertionError("EngineHost health remained reachable after launcher exit")


def _get_json_short(url: str, *, timeout_seconds: float = 1) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _pipe_tail(pipe: Any, *, max_chars: int = 2000) -> str:
    if pipe is None:
        return ""
    try:
        data = pipe.read()
    except Exception:  # pragma: no cover - failure detail only
        return ""
    return data.decode("utf-8", errors="replace")[-max_chars:]


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")
