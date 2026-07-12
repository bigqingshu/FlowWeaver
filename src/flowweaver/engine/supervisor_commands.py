from __future__ import annotations

from pathlib import Path

from flowweaver.common.config import EngineConfig
from flowweaver.common.subprocess_command import python_module_command
from flowweaver.engine.runtime_models import WorkflowProcess


def workflow_process_command(
    *,
    python_executable: str,
    src_path: Path,
    database_url: str,
    workflow_run_id: str,
    process: WorkflowProcess,
    config: EngineConfig,
    runtime_event_path: Path,
) -> list[str]:
    return [
        *python_module_command(
            python_executable=python_executable,
            module_name="flowweaver.workflow_process.main",
            src_path=src_path,
        ),
        "--database-url",
        database_url,
        "--workflow-run-id",
        workflow_run_id,
        "--process-id",
        process.process_id,
        "--process-generation",
        str(process.process_generation),
        "--heartbeat-interval-seconds",
        str(config.workflow_process_heartbeat_interval_seconds),
        "--execution-mode",
        config.workflow_process_execution_mode,
        "--max-concurrent-node-tasks",
        str(config.workflow_process_max_concurrent_node_tasks),
        "--memory-table-soft-row-limit",
        str(config.memory_table_soft_row_limit),
        "--runtime-dir",
        str(config.resolved_runtime_dir()),
        "--plugin-dir",
        str(config.resolved_plugin_dir()),
        "--runtime-event-path",
        str(runtime_event_path),
        "--wait-for-start-signal",
    ]


def node_executor_command(
    *,
    python_executable: str,
    src_path: Path,
    executor_id: str,
) -> list[str]:
    return [
        *python_module_command(
            python_executable=python_executable,
            module_name="flowweaver.node_executor.process",
            src_path=src_path,
        ),
        "--executor-id",
        executor_id,
    ]
