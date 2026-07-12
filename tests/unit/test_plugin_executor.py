from __future__ import annotations

import json
from pathlib import Path

from flowweaver.common.config import MemoryTableLimits
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.plugin_runtime.discovery import discover_plugins
from flowweaver.plugin_runtime.process_command import (
    plugin_process_command,
    plugin_process_environment,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.workflow_process.executor_owner import (
    DefaultWorkflowProcessExecutorOwner,
)


def test_plugin_process_command_uses_isolated_python_arguments(tmp_path: Path) -> None:
    runner = tmp_path / "runner.py"
    runner.write_text("print('runner')\n", encoding="utf-8")

    command = plugin_process_command(
        runner,
        executor_id="plugin-task-1",
        python_executable="python.exe",
    )

    assert command == [
        "python.exe",
        "-E",
        "-s",
        str(runner),
        "--executor-id",
        "plugin-task-1",
    ]


def test_plugin_process_environment_uses_allowlist() -> None:
    environment = plugin_process_environment(
        {
            "PATH": "bin",
            "SYSTEMROOT": "windows",
            "PYTHONPATH": "unsafe",
            "FLOWWEAVER_TEST_SECRET": "secret",
        }
    )

    assert environment == {
        "PATH": "bin",
        "SYSTEMROOT": "windows",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    }


def test_executor_owner_routes_plugin_namespace_to_plugin_executor(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    package = plugin_root / "example"
    package.mkdir(parents=True)
    (package / "runner.py").write_text("print('runner')\n", encoding="utf-8")
    (package / "plugin.json").write_text(
        json.dumps(_manifest()),
        encoding="utf-8",
    )
    catalog = discover_plugins(plugin_root)
    created: list[object] = []

    class TrackingPluginExecutor:
        executor_id = "tracking-plugin-executor"

        def __init__(self, *, plugin_catalog) -> None:
            self.plugin_catalog = plugin_catalog
            self.closed = False
            created.append(self)

        def execute(self, task):
            raise AssertionError(task)

        def close(self) -> None:
            self.closed = True

    store = RuntimeStore("sqlite:///:memory:")
    owner = DefaultWorkflowProcessExecutorOwner(
        store=store,
        runtime_dir=tmp_path / "runtime",
        memory_table_limits=MemoryTableLimits(),
        plugin_catalog=catalog,
        plugin_executor_factory=TrackingPluginExecutor,
    )
    task = _task()

    first = owner.executor_for_task(task)
    second = owner.executor_for_task(task)
    owner.close()
    store.dispose()

    assert first is second
    assert created == [first]
    assert first.closed is True


def _task() -> NodeTaskModel:
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
        config={"enable_execute": True},
        timeout_seconds=60,
    )


def _manifest() -> dict:
    return {
        "manifest_version": "1",
        "plugin_id": "example.echo",
        "plugin_version": "1.0.0",
        "node_type": "plugin.example.echo",
        "node_version": "1.0",
        "display_name": "Echo",
        "category": "test",
        "config_schema": {"type": "object", "properties": {}},
        "input_ports": [],
        "output_ports": [],
        "input_table_slots": [],
        "output_table_slots": [],
        "execution_mode": "external_process",
        "protocol": "flowweaver.plugin-jsonl.v1",
        "entrypoint": "runner.py",
        "external_actions": False,
    }
