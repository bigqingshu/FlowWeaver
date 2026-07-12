from __future__ import annotations

import json
import sys
from pathlib import Path
from textwrap import dedent

from alembic import command
from alembic.config import Config

from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.plugin_runtime.discovery import discover_plugins
from flowweaver.plugin_runtime.executor import PluginExternalProcessExecutor
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.workflow_process.main import run_workflow_process


def test_plugin_executor_runs_isolated_process_and_closes_it(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_plugin(plugin_root, mode="success")
    monkeypatch.setenv("PYTHONPATH", "unsafe-pythonpath")
    monkeypatch.setenv("FLOWWEAVER_TEST_SECRET", "secret")
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
        startup_timeout_seconds=1,
    )

    result = executor.execute(_task(config={"enable_execute": True, "value": 3}))

    assert result.status == NodeResultStatus.SUCCEEDED
    assert result.executor_id == "plugin-external-process-executor"
    assert result.summary["config"] == {"value": 3}
    assert result.summary["cwd"] == str(package)
    assert result.summary["pythonpath"] is None
    assert result.summary["secret"] is None
    assert (package / "runner.closed").is_file()
    assert executor.closed is False
    executor.close()
    assert executor.closed is True


def test_workflow_process_runs_discovered_plugin_end_to_end(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_plugin(plugin_root, mode="success")
    store = _make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Plugin workflow",
        workflow_id="workflow-plugin",
        definition={
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "plugin",
                    "node_type": "plugin.example.echo",
                    "node_version": "1.0",
                    "config": {"enable_execute": True, "value": 7},
                }
            ],
            "connections": [],
        },
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-plugin",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-plugin",
    )
    assert process is not None

    try:
        exit_code = run_workflow_process(
            store=store,
            workflow_run_id=run.workflow_run_id,
            process_id=process.process_id,
            process_generation=process.process_generation,
            heartbeat_interval_seconds=0,
            runtime_dir=tmp_path / "runtime" / "workflow_runs",
            plugin_dir=plugin_root,
        )

        completed_run = store.get_workflow_run(run.workflow_run_id)
        node_run = store.list_node_runs(run.workflow_run_id)[0]
        result = store.get_latest_succeeded_node_task_result_for_node_run(
            node_run.node_run_id
        )
    finally:
        store.dispose()

    assert exit_code == 0
    assert completed_run is not None
    assert completed_run.status == "SUCCEEDED", {
        "run_error": completed_run.error,
        "node_status": node_run.status,
        "node_error": node_run.error,
    }
    assert node_run.status == "SUCCEEDED"
    assert result is not None
    assert result.executor_id == "plugin-external-process-executor"
    assert result.summary["config"] == {"value": 7}
    assert (package / "runner.closed").is_file()


def test_plugin_executor_reports_ready_timeout(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    _write_plugin(plugin_root, mode="slow_ready")
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
        startup_timeout_seconds=0.05,
    )

    result = executor.execute(_task())

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["error_code"] == "PLUGIN_START_FAILED"
    assert "did not become ready" in result.error["message"]


def test_plugin_executor_rejects_invalid_stdout(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    _write_plugin(plugin_root, mode="invalid_ready")
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
        startup_timeout_seconds=1,
    )

    result = executor.execute(_task())

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["error_code"] == "PLUGIN_START_FAILED"


def test_plugin_executor_returns_bounded_stderr_when_process_exits(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    _write_plugin(plugin_root, mode="stderr_exit")
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
        startup_timeout_seconds=1,
    )

    result = executor.execute(_task())

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["message"] == (
        "Node executor subprocess exited before completing task"
    )
    assert result.error["exit_code"] == 3
    assert result.error["stderr"].endswith("forced executor exit")
    assert len(result.error["stderr"]) <= 2000


def test_plugin_executor_rejects_result_identity_mismatch(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    _write_plugin(plugin_root, mode="identity_mismatch")
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
        startup_timeout_seconds=1,
    )

    result = executor.execute(_task())

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["error_code"] == "PLUGIN_RESULT_IDENTITY_MISMATCH"
    assert "task_id" in result.error["message"]


def test_plugin_executor_blocks_external_actions_before_start(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_plugin(
        plugin_root,
        mode="success",
        external_actions=True,
    )
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
    )

    result = executor.execute(
        _task(config={"enable_execute": True, "allow_external_actions": False})
    )

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["error_code"] == "PLUGIN_EXTERNAL_ACTIONS_BLOCKED"
    assert not (package / "runner.started").exists()


def test_plugin_executor_requires_enable_execute(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_plugin(plugin_root, mode="success")
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
    )

    result = executor.execute(_task(config={"enable_execute": False}))

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["error_code"] == "PLUGIN_EXECUTION_DISABLED"
    assert not (package / "runner.started").exists()


def _task(*, config: dict | None = None) -> NodeTaskModel:
    return NodeTaskModel(
        task_id="task-plugin",
        workflow_run_id="run-plugin",
        workflow_process_id="process-plugin",
        process_generation=1,
        node_run_id="node-run-plugin",
        node_instance_id="plugin",
        node_type="plugin.example.echo",
        node_version="1.0",
        attempt=1,
        input_refs=[],
        config=config or {"enable_execute": True},
        timeout_seconds=60,
    )


def _make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")
    return RuntimeStore.from_sqlite_path(database_path)


def _write_plugin(
    plugin_root: Path,
    *,
    mode: str,
    external_actions: bool = False,
) -> Path:
    package = plugin_root / "echo"
    package.mkdir(parents=True)
    runner_path = package / "runner.py"
    runner_path.write_text(_runner_source(mode), encoding="utf-8")
    manifest = {
        "manifest_version": "1",
        "plugin_id": "example.echo",
        "plugin_version": "1.0.0",
        "node_type": "plugin.example.echo",
        "node_version": "1.0",
        "display_name": "Echo",
        "category": "test",
        "config_schema": {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
        },
        "input_ports": [],
        "output_ports": [],
        "input_table_slots": [],
        "output_table_slots": [],
        "execution_mode": "external_process",
        "protocol": "flowweaver.plugin-jsonl.v1",
        "entrypoint": "runner.py",
        "external_actions": external_actions,
    }
    (package / "plugin.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    return package


def _runner_source(mode: str) -> str:
    return dedent(
        f"""
        import argparse
        import json
        import os
        import sys
        import time
        from pathlib import Path

        MODE = {mode!r}
        parser = argparse.ArgumentParser()
        parser.add_argument("--executor-id", required=True)
        args = parser.parse_args()
        Path("runner.started").write_text(str(os.getpid()), encoding="utf-8")

        def emit(message_type, payload):
            print(
                json.dumps({{"message_type": message_type, "payload": payload}}),
                flush=True,
            )

        if MODE == "slow_ready":
            time.sleep(5)
        if MODE == "invalid_ready":
            print("not-json", flush=True)
        else:
            emit("EXECUTOR_READY", {{"executor_id": args.executor_id}})

        try:
            for line in sys.stdin:
                message = json.loads(line)
                if message.get("message_type") != "NODE_TASK_SUBMIT":
                    continue
                task = message["payload"]
                if MODE == "stderr_exit":
                    sys.stderr.write("x" * 10000 + "forced executor exit")
                    sys.stderr.flush()
                    raise SystemExit(3)
                task_id = (
                    "wrong-task"
                    if MODE == "identity_mismatch"
                    else task["task_id"]
                )
                result = {{
                    "task_id": task_id,
                    "node_run_id": task["node_run_id"],
                    "attempt": task["attempt"],
                    "executor_id": args.executor_id,
                    "process_generation": task["process_generation"],
                    "status": "SUCCEEDED",
                    "summary": {{
                        "config": task["config"],
                        "cwd": os.getcwd(),
                        "pythonpath": os.environ.get("PYTHONPATH"),
                        "secret": os.environ.get("FLOWWEAVER_TEST_SECRET"),
                    }},
                }}
                emit("NODE_TASK_COMPLETED", {{"result": result}})
        finally:
            Path("runner.closed").write_text("closed", encoding="utf-8")
        """
    )
