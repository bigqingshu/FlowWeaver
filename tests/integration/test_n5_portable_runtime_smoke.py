from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from types import ModuleType

from formal_smoke_helpers import (
    consumer_definition,
    free_port,
    get_json,
    post_json,
    producer_definition,
    response_data,
    stop_process,
    wait_for_health,
    wait_for_runtime_events,
    wait_for_terminal_run,
)


def test_n5_portable_python_runs_full_backend_runtime_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    create_portable_layout = _load_create_portable_layout(repo_root)
    output_dir = (
        repo_root / ".tmp" / f"FlowWeaverPortableRuntimeTest-{uuid.uuid4().hex}"
    )
    portable_dir = create_portable_layout(
        repo_root=repo_root,
        output_dir=output_dir,
        include_python=True,
        include_desktop_build=False,
    )
    enginehost_dir = portable_dir / "EngineHost"
    python_exe = enginehost_dir / "python312" / "python.exe"
    assert python_exe.is_file()

    port = free_port()
    stdout_path = enginehost_dir / "uvicorn.n5.stdout.log"
    stderr_path = enginehost_dir / "uvicorn.n5.stderr.log"
    process: subprocess.Popen[bytes] | None = None
    process = _start_portable_enginehost(
        enginehost_dir=enginehost_dir,
        python_exe=python_exe,
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
        token_path = enginehost_dir / "runtime" / "config" / "local_api_token"
        token = token_path.read_text(encoding="utf-8").strip()
        assert token

        producer_workflow = response_data(
            post_json(
                f"{base_url}/api/v1/workflows",
                token=token,
                payload={
                    "name": "N5 portable producer",
                    "definition": producer_definition("n5.orders"),
                },
            )
        )
        producer_run = response_data(
            post_json(
                f"{base_url}/api/v1/workflows/{producer_workflow['workflow_id']}/runs",
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
        assert len(
            [
                ref
                for ref in producer_table_refs
                if ref["lifecycle_status"] == "PUBLISHED"
            ]
        ) == 2

        publications = response_data(
            get_json(
                f"{base_url}/api/v1/shared-publications?share_name=n5.orders",
                token=token,
            )
        )
        assert len(publications) == 1
        assert publications[0]["publication_version"] == 1
        assert [member["export_name"] for member in publications[0]["members"]] == [
            "orders"
        ]

        versions = response_data(
            get_json(
                f"{base_url}/api/v1/shared-publications/n5.orders/versions",
                token=token,
            )
        )
        assert [item["publication_version"] for item in versions] == [1]

        consumer_workflow = response_data(
            post_json(
                f"{base_url}/api/v1/workflows",
                token=token,
                payload={
                    "name": "N5 portable consumer",
                    "definition": consumer_definition("n5.orders"),
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

        workflow_logs_dir = enginehost_dir / "runtime" / "logs" / "workflow_runs"
        assert any(workflow_logs_dir.glob("*.stdout.log"))
        assert any(workflow_logs_dir.glob("*.stderr.log"))
    finally:
        if process is not None:
            stop_process(process)
        shutil.rmtree(output_dir, ignore_errors=True)


def _load_create_portable_layout(repo_root: Path):
    module_path = repo_root / "tools" / "create_portable_layout.py"
    spec = importlib.util.spec_from_file_location(
        "flowweaver_create_portable_layout_n5",
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
    enginehost_dir: Path,
    python_exe: Path,
    port: int,
    stdout_path: Path,
    stderr_path: Path,
) -> subprocess.Popen[bytes]:
    stdout_file = stdout_path.open("wb")
    stderr_file = stderr_path.open("wb")
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    try:
        return subprocess.Popen(
            [
                str(python_exe),
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
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
        )
    finally:
        stdout_file.close()
        stderr_file.close()
