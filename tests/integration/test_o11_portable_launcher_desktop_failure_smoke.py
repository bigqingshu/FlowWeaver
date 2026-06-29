from __future__ import annotations

import importlib.util
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

import pytest
from formal_smoke_helpers import free_port

pytestmark = pytest.mark.skipif(
    os.name != "nt",
    reason="Desktop lifecycle failure smoke is Windows-only.",
)


def test_o11_launcher_rejects_missing_desktop_before_enginehost_start() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    create_portable_layout = _load_create_portable_layout(repo_root)
    output_dir = (
        repo_root / ".tmp" / f"FlowWeaverPortableDesktopMissing-{uuid.uuid4().hex}"
    )
    portable_dir = create_portable_layout(
        repo_root=repo_root,
        output_dir=output_dir,
        include_python=True,
        include_desktop_build=False,
    )
    enginehost_dir = portable_dir / "EngineHost"
    python_exe = enginehost_dir / "python312" / "python.exe"
    desktop_exe = portable_dir / "Desktop" / "Avalonia_UI.exe"

    try:
        process = _start_launcher(
            portable_dir=portable_dir,
            python_exe=python_exe,
            port=free_port(),
        )
        stdout_text, stderr_text = _communicate(process)

        assert process.returncode == 2
        assert stdout_text == ""
        assert "configuration error" in stderr_text
        assert str(desktop_exe) in stderr_text
        assert not (enginehost_dir / "runtime").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_o11_launcher_stops_enginehost_when_desktop_executable_is_invalid() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    create_portable_layout = _load_create_portable_layout(repo_root)
    output_dir = (
        repo_root / ".tmp" / f"FlowWeaverPortableDesktopInvalid-{uuid.uuid4().hex}"
    )
    portable_dir = create_portable_layout(
        repo_root=repo_root,
        output_dir=output_dir,
        include_python=True,
        include_desktop_build=False,
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
    token: str | None = None

    desktop_exe.write_text("not a valid windows executable", encoding="utf-8")

    try:
        process = _start_launcher(
            portable_dir=portable_dir,
            python_exe=python_exe,
            port=port,
        )
        stdout_text, stderr_text = _communicate(process, timeout_seconds=40)
        token = _read_token_if_available(token_path)
        launcher_log = _read_text(launcher_log_path)
        engine_stdout = _read_text(engine_stdout_path)
        engine_stderr = _read_text(engine_stderr_path)
        desktop_stdout = _read_text(desktop_stdout_path)
        desktop_stderr = _read_text(desktop_stderr_path)

        assert process.returncode == 1
        assert "EngineHost ready." in stdout_text
        assert "Desktop started." not in stdout_text
        assert "runtime error: Failed to start Desktop" in stderr_text
        assert "EngineHost ready" in launcher_log
        assert "Starting Desktop" in launcher_log
        assert "Launcher runtime error: Failed to start Desktop" in launcher_log
        assert "EngineHost stopped" in launcher_log
        assert "Desktop pid=" not in launcher_log
        assert desktop_stdout_path.is_file()
        assert desktop_stderr_path.is_file()
        _wait_until_health_unreachable(base_url)

        if token is not None:
            assert token not in stdout_text
            assert token not in stderr_text
            assert token not in launcher_log
            assert token not in engine_stdout
            assert token not in engine_stderr
            assert token not in desktop_stdout
            assert token not in desktop_stderr
    finally:
        if "process" in locals() and process.poll() is None:
            process.send_signal(signal.CTRL_BREAK_EVENT)
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                _force_kill_process_tree(process.pid)
        shutil.rmtree(output_dir, ignore_errors=True)


def _load_create_portable_layout(repo_root: Path):
    module_path = repo_root / "tools" / "create_portable_layout.py"
    spec = importlib.util.spec_from_file_location(
        "flowweaver_create_portable_layout_o11",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    assert isinstance(module, ModuleType)
    spec.loader.exec_module(module)
    return module.create_portable_layout


def _start_launcher(
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
            "20",
        ],
        cwd=portable_dir,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )


def _communicate(
    process: subprocess.Popen[bytes],
    *,
    timeout_seconds: float = 20,
) -> tuple[str, str]:
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _force_kill_process_tree(process.pid)
        stdout, stderr = process.communicate(timeout=5)
    return (
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


def _read_token_if_available(token_path: Path) -> str | None:
    if not token_path.is_file():
        return None
    token = token_path.read_text(encoding="utf-8").strip()
    return token or None


def _wait_until_health_unreachable(
    base_url: str,
    *,
    timeout_seconds: float = 10,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"{base_url}/api/v1/health", timeout=0.5).close()
        except (OSError, TimeoutError, urllib.error.URLError):
            return
        time.sleep(0.1)
    raise AssertionError("EngineHost health remained reachable after launcher exit")


def _force_kill_process_tree(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        check=False,
        capture_output=True,
        text=True,
    )


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")
