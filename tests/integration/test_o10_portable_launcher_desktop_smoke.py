from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from types import ModuleType

import pytest
from formal_smoke_helpers import free_port, get_json, response_data

pytestmark = [
    pytest.mark.skipif(os.name != "nt", reason="Desktop smoke is Windows-only."),
    pytest.mark.skipif(
        os.environ.get("FLOWWEAVER_RUN_DESKTOP_SMOKE") != "1",
        reason="Set FLOWWEAVER_RUN_DESKTOP_SMOKE=1 to run real Desktop smoke.",
    ),
]


def test_o10_portable_launcher_starts_real_desktop_and_cleans_up() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    create_portable_layout = _load_create_portable_layout(repo_root)
    publish_desktop = _load_publish_desktop(repo_root)
    output_dir = (
        repo_root / ".tmp" / f"FlowWeaverPortableDesktopTest-{uuid.uuid4().hex}"
    )
    portable_dir = create_portable_layout(
        repo_root=repo_root,
        output_dir=output_dir,
        include_python=True,
        include_desktop_build=False,
    )
    publish_desktop(
        repo_root=repo_root,
        output_dir=portable_dir / "Desktop",
        configuration="Release",
        runtime="win-x64",
        self_contained=False,
    )

    enginehost_dir = portable_dir / "EngineHost"
    python_exe = enginehost_dir / "python312" / "python.exe"
    desktop_exe = portable_dir / "Desktop" / "Avalonia_UI.exe"
    log_dir = enginehost_dir / "runtime" / "logs"
    launcher_log_path = log_dir / "portable-launcher.log"
    engine_stdout_path = log_dir / "enginehost.stdout.log"
    engine_stderr_path = log_dir / "enginehost.stderr.log"
    desktop_stdout_path = log_dir / "desktop.stdout.log"
    desktop_stderr_path = log_dir / "desktop.stderr.log"
    token_path = enginehost_dir / "runtime" / "config" / "local_api_token"
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"

    assert desktop_exe.is_file()

    process: subprocess.Popen[bytes] | None = None
    stdout_text = ""
    stderr_text = ""
    stop_returncode: int | None = None
    token: str | None = None
    desktop_pid: int | None = None
    health_ready = False
    launcher_log_after_stop = ""
    engine_stdout_after_stop = ""
    engine_stderr_after_stop = ""
    desktop_stdout_after_stop = ""
    desktop_stderr_after_stop = ""
    engine_stdout_exists = False
    engine_stderr_exists = False
    desktop_stdout_exists = False
    desktop_stderr_exists = False

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

            launcher_log = _wait_for_text(
                launcher_log_path,
                expected="Desktop pid=",
                process=process,
                timeout_seconds=20,
            )
            desktop_pid = _extract_desktop_pid(launcher_log)
            assert desktop_pid is not None
            assert "EngineHost ready" in launcher_log
            assert "Starting Desktop" in launcher_log
            assert token not in launcher_log
        finally:
            if process is not None:
                stdout_text, stderr_text, stop_returncode = _stop_launcher(process)
                engine_stdout_exists = engine_stdout_path.is_file()
                engine_stderr_exists = engine_stderr_path.is_file()
                desktop_stdout_exists = desktop_stdout_path.is_file()
                desktop_stderr_exists = desktop_stderr_path.is_file()
                launcher_log_after_stop = _read_text(launcher_log_path)
                engine_stdout_after_stop = _read_text(engine_stdout_path)
                engine_stderr_after_stop = _read_text(engine_stderr_path)
                desktop_stdout_after_stop = _read_text(desktop_stdout_path)
                desktop_stderr_after_stop = _read_text(desktop_stderr_path)
            if health_ready:
                _wait_until_health_unreachable(base_url)
            if desktop_pid is not None:
                _wait_until_process_exits(desktop_pid)
    finally:
        if process is not None and process.poll() is None:
            _force_kill_process_tree(process.pid)
        if desktop_pid is not None and _process_exists(desktop_pid):
            _force_kill_process_tree(desktop_pid)
        shutil.rmtree(output_dir, ignore_errors=True)

    assert stop_returncode in {0, 130}
    assert "EngineHost ready." in stdout_text
    assert "Desktop started." in stdout_text
    assert "Launcher interrupted by user" in launcher_log_after_stop
    assert "Desktop stopped" in launcher_log_after_stop
    assert "EngineHost stopped" in launcher_log_after_stop
    assert engine_stdout_exists
    assert engine_stderr_exists
    assert desktop_stdout_exists
    assert desktop_stderr_exists

    if token is not None:
        assert token not in stdout_text
        assert token not in stderr_text
        assert token not in launcher_log_after_stop
        assert token not in engine_stdout_after_stop
        assert token not in engine_stderr_after_stop
        assert token not in desktop_stdout_after_stop
        assert token not in desktop_stderr_after_stop


def _load_create_portable_layout(repo_root: Path):
    module_path = repo_root / "tools" / "create_portable_layout.py"
    spec = importlib.util.spec_from_file_location(
        "flowweaver_create_portable_layout_o10",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    assert isinstance(module, ModuleType)
    spec.loader.exec_module(module)
    return module.create_portable_layout


def _load_publish_desktop(repo_root: Path):
    module_path = repo_root / "tools" / "publish_desktop.py"
    spec = importlib.util.spec_from_file_location(
        "flowweaver_publish_desktop_o10",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    assert isinstance(module, ModuleType)
    spec.loader.exec_module(module)
    return module.publish_desktop


def _start_portable_launcher(
    *,
    portable_dir: Path,
    python_exe: Path,
    port: int,
) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return subprocess.Popen(
        [
            str(python_exe),
            "portable_launcher.py",
            "--port",
            str(port),
            "--health-timeout-seconds",
            "30",
        ],
        cwd=portable_dir,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )


def _wait_for_health(
    *,
    process: subprocess.Popen[bytes],
    base_url: str,
    timeout_seconds: float = 30,
) -> dict[str, object]:
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
    timeout_seconds: float = 30,
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
    timeout_seconds: float,
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


def _stop_launcher(process: subprocess.Popen[bytes]) -> tuple[str, str, int | None]:
    if process.poll() is None:
        process.send_signal(signal.CTRL_BREAK_EVENT)
    try:
        stdout, stderr = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        _force_kill_process_tree(process.pid)
        stdout, stderr = process.communicate(timeout=5)
    return (
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
        process.returncode,
    )


def _wait_until_health_unreachable(
    base_url: str,
    *,
    timeout_seconds: float = 10,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            _get_json_short(f"{base_url}/api/v1/health", timeout_seconds=0.5)
        except (OSError, TimeoutError, urllib.error.URLError):
            return
        time.sleep(0.1)
    raise AssertionError("EngineHost health remained reachable after launcher exit")


def _wait_until_process_exits(pid: int, *, timeout_seconds: float = 10) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _process_exists(pid):
            return
        time.sleep(0.1)
    raise AssertionError(f"Desktop process remained alive after launcher exit: {pid}")


def _extract_desktop_pid(log_text: str) -> int | None:
    match = re.search(r"Desktop pid=(\d+)", log_text)
    return None if match is None else int(match.group(1))


def _process_exists(pid: int) -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
        check=False,
        capture_output=True,
        text=True,
    )
    return str(pid) in result.stdout


def _force_kill_process_tree(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        check=False,
        capture_output=True,
        text=True,
    )


def _get_json_short(url: str, *, timeout_seconds: float = 1) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _pipe_tail(pipe: object, *, max_chars: int = 2000) -> str:
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
