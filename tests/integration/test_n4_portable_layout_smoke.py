from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from types import ModuleType

from formal_smoke_helpers import (
    free_port,
    get_json,
    response_data,
    stop_process,
    wait_for_health,
)


def test_n4_portable_layout_enginehost_starts_from_generated_directory() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    create_portable_layout = _load_create_portable_layout(repo_root)
    output_dir = repo_root / ".tmp" / f"FlowWeaverPortableTest-{uuid.uuid4().hex}"
    portable_dir = create_portable_layout(
        repo_root=repo_root,
        output_dir=output_dir,
        include_python=False,
        include_desktop_build=False,
    )
    enginehost_dir = portable_dir / "EngineHost"

    assert (enginehost_dir / "alembic.ini").is_file()
    assert (enginehost_dir / "migrations" / "env.py").is_file()
    assert (enginehost_dir / "src" / "flowweaver" / "api" / "app.py").is_file()
    assert not (enginehost_dir / "runtime").exists()

    stdout_path = enginehost_dir / "uvicorn.stdout.log"
    stderr_path = enginehost_dir / "uvicorn.stderr.log"
    port = free_port()
    process: subprocess.Popen[bytes] | None = None
    process = _start_portable_enginehost(
        repo_root=repo_root,
        enginehost_dir=enginehost_dir,
        port=port,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    try:
        base_url = f"http://127.0.0.1:{port}"
        health = wait_for_health(
            process=process,
            base_url=base_url,
            stderr_path=stderr_path,
        )
        assert health["ok"] is True
        assert health["data"]["status"] == "ok"

        runtime_dir = enginehost_dir / "runtime"
        assert (runtime_dir / "metadata" / "flowweaver.db").is_file()
        assert (runtime_dir / "config" / "local_api_token").is_file()
        assert (runtime_dir / "workflow_runs").is_dir()
        assert (runtime_dir / "logs").is_dir()
        assert (runtime_dir / "temp").is_dir()

        token = (runtime_dir / "config" / "local_api_token").read_text(
            encoding="utf-8"
        ).strip()
        assert token

        workflows = response_data(
            get_json(f"{base_url}/api/v1/workflows", token=token)
        )
        assert workflows == []
    finally:
        if process is not None:
            stop_process(process)
        shutil.rmtree(output_dir, ignore_errors=True)


def _load_create_portable_layout(repo_root: Path):
    module_path = repo_root / "tools" / "create_portable_layout.py"
    spec = importlib.util.spec_from_file_location(
        "flowweaver_create_portable_layout",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    assert isinstance(module, ModuleType)
    spec.loader.exec_module(module)
    return module.create_portable_layout


def _start_portable_enginehost(
    *,
    repo_root: Path,
    enginehost_dir: Path,
    port: int,
    stdout_path: Path,
    stderr_path: Path,
) -> subprocess.Popen[bytes]:
    python_exe = repo_root / "python312" / "python.exe"
    executable = str(python_exe if python_exe.is_file() else sys.executable)
    stdout_file = stdout_path.open("wb")
    stderr_file = stderr_path.open("wb")
    try:
        return subprocess.Popen(
            [
                executable,
                "-m",
                "uvicorn",
                "--app-dir",
                str(enginehost_dir / "src"),
                "flowweaver.api.app:create_default_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=enginehost_dir,
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
        )
    finally:
        stdout_file.close()
        stderr_file.close()
