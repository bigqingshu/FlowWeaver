from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path

from flowweaver.common.config import EngineConfig
from flowweaver.engine.runtime_store import RuntimeStore, WorkflowProcess
from flowweaver.engine.supervisor_commands import (
    node_executor_command as _node_executor_command,
)
from flowweaver.engine.supervisor_commands import (
    workflow_process_command as _workflow_process_command,
)
from flowweaver.engine.supervisor_paths import (
    executor_process_log_paths as _executor_process_log_paths,
)
from flowweaver.engine.supervisor_paths import (
    workflow_process_log_paths as _workflow_process_log_paths,
)
from flowweaver.engine.supervisor_process_launch import (
    launch_child_process as _launch_child_process,
)


def start_workflow_child_process(
    *,
    config: EngineConfig,
    runtime_store: RuntimeStore,
    python_executable: str,
    workflow_run_id: str,
    process: WorkflowProcess,
    runtime_event_path: Path,
    env: Mapping[str, str],
) -> subprocess.Popen:
    src_path = Path(__file__).resolve().parents[2]
    command = _workflow_process_command(
        python_executable=python_executable,
        src_path=src_path,
        database_url=runtime_store.database_url,
        workflow_run_id=workflow_run_id,
        process=process,
        config=config,
        runtime_event_path=runtime_event_path,
    )
    stdout_path, stderr_path = _workflow_process_log_paths(config, workflow_run_id)
    try:
        return _launch_child_process(
            command,
            cwd=src_path,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
    except Exception as exc:
        runtime_store.mark_workflow_process_exited(
            process.process_id,
            exit_code=1,
            error={"message": str(exc)},
        )
        runtime_store.abort_workflow_run_for_process(
            process.process_id,
            reason="WORKFLOW_PROCESS_START_FAILED",
        )
        raise


def start_executor_child_process(
    *,
    config: EngineConfig,
    python_executable: str,
    executor_id: str,
    env: Mapping[str, str],
) -> subprocess.Popen:
    src_path = Path(__file__).resolve().parents[2]
    command = _node_executor_command(
        python_executable=python_executable,
        src_path=src_path,
        executor_id=executor_id,
    )
    stdout_path, stderr_path = _executor_process_log_paths(config, executor_id)
    return _launch_child_process(
        command,
        cwd=src_path,
        env=env,
        stdin=subprocess.PIPE,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
