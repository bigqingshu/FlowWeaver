from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any

from formal_smoke_helpers import free_port, get_json, response_data


def test_p4_portable_archive_clean_room_backend_only_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    create_portable_layout = _load_create_portable_layout(repo_root)
    create_portable_archive = _load_create_portable_archive(repo_root)
    layout_dir = repo_root / ".tmp" / f"FlowWeaverPortableP4Layout-{uuid.uuid4().hex}"
    archive_output_dir = repo_root / ".tmp" / f"dist-p4-smoke-{uuid.uuid4().hex}"
    clean_room_parent = (
        Path(tempfile.gettempdir())
        / f"FlowWeaver Clean Room 中文路径 {uuid.uuid4().hex}"
    )
    assert repo_root.resolve() not in clean_room_parent.resolve().parents

    process: subprocess.Popen[bytes] | None = None
    stdout_text = ""
    stderr_text = ""
    token: str | None = None
    base_url: str | None = None
    health_ready = False

    try:
        portable_layout = create_portable_layout(
            repo_root=repo_root,
            output_dir=layout_dir,
            include_python=True,
            include_desktop_build=False,
        )
        archive_result = create_portable_archive(
            repo_root=repo_root,
            input_dir=portable_layout,
            output_dir=archive_output_dir,
        )
        _assert_sha256_file(
            archive_path=archive_result.archive_path,
            sha256_path=archive_result.sha256_path,
        )

        clean_room_parent.mkdir(parents=True)
        with zipfile.ZipFile(archive_result.archive_path) as archive:
            archive.extractall(clean_room_parent)

        portable_root = clean_room_parent / "FlowWeaverPortable"
        enginehost_dir = portable_root / "EngineHost"
        python_exe = enginehost_dir / "python312" / "python.exe"
        runtime_dir = enginehost_dir / "runtime"
        token_path = runtime_dir / "config" / "local_api_token"
        log_dir = runtime_dir / "logs"
        launcher_log_path = log_dir / "portable-launcher.log"
        manifest_path = portable_root / "release-manifest.json"
        user_manual_path = portable_root / "docs" / "FlowWeaver_便携版用户手册.md"

        assert portable_root.is_dir()
        assert python_exe.is_file()
        assert manifest_path.is_file()
        assert user_manual_path.is_file()
        assert "FlowWeaver 便携版用户手册" in user_manual_path.read_text(
            encoding="utf-8"
        )
        assert not runtime_dir.exists()
        assert repo_root.resolve() not in portable_root.resolve().parents
        assert " " in str(portable_root)
        assert "中文路径" in str(portable_root)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["package_kind"] == "portable"
        assert manifest["target_runtime"] == "win-x64"
        assert manifest["desktop_publish_mode"] == "framework-dependent"
        assert manifest["runtime_audit_status"] in {"checked", "warning"}
        entries = {entry["path"]: entry for entry in manifest["entries"]}
        assert "FlowWeaverPortable/docs/FlowWeaver_便携版用户手册.md" in entries

        port = free_port()
        base_url = f"http://127.0.0.1:{port}"
        process = _start_portable_launcher(
            portable_root=portable_root,
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

        assert (runtime_dir / "metadata" / "flowweaver.db").is_file()
        assert token_path.is_file()
        assert log_dir.is_dir()
        launcher_log = _wait_for_text(
            launcher_log_path,
            expected="EngineHost ready",
            process=process,
        )
        assert "EngineHost ready" in launcher_log
        assert token not in launcher_log
    finally:
        if process is not None:
            stdout_text, stderr_text = _stop_launcher_gracefully(process)
        if health_ready and base_url is not None:
            _wait_until_health_unreachable(base_url)
        shutil.rmtree(layout_dir, ignore_errors=True)
        shutil.rmtree(archive_output_dir, ignore_errors=True)
        shutil.rmtree(clean_room_parent, ignore_errors=True)

    if token is not None:
        assert token not in stdout_text
        assert token not in stderr_text


def _load_create_portable_layout(repo_root: Path):
    module_path = repo_root / "tools" / "create_portable_layout.py"
    spec = importlib.util.spec_from_file_location(
        "flowweaver_create_portable_layout_p4",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    assert isinstance(module, ModuleType)
    spec.loader.exec_module(module)
    return module.create_portable_layout


def _load_create_portable_archive(repo_root: Path):
    module_path = repo_root / "tools" / "create_portable_archive.py"
    spec = importlib.util.spec_from_file_location(
        "flowweaver_create_portable_archive_p4",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    assert isinstance(module, ModuleType)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.create_portable_archive


def _assert_sha256_file(*, archive_path: Path, sha256_path: Path) -> None:
    expected = f"{_sha256_file(archive_path)}  {archive_path.name}\n"
    assert sha256_path.read_text(encoding="utf-8") == expected


def _start_portable_launcher(
    *,
    portable_root: Path,
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
            "30",
        ],
        cwd=portable_root,
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
    timeout_seconds: float = 30,
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
            "message": "EngineHost health did not become ok in clean-room",
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
    timeout_seconds: float = 10,
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


def _stop_launcher_gracefully(process: subprocess.Popen[bytes]) -> tuple[str, str]:
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


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
