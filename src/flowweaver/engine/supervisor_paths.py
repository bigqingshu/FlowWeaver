from __future__ import annotations

import os
from pathlib import Path

from flowweaver.common.config import EngineConfig


def child_environment(*, src_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(src_path)
        if not existing_pythonpath
        else f"{src_path}{os.pathsep}{existing_pythonpath}"
    )
    return env


def workflow_process_log_paths(
    config: EngineConfig,
    workflow_run_id: str,
) -> tuple[Path, Path]:
    log_dir = config.resolved_log_dir() / "workflow_runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return (
        log_dir / f"{workflow_run_id}.stdout.log",
        log_dir / f"{workflow_run_id}.stderr.log",
    )


def executor_process_log_paths(
    config: EngineConfig,
    executor_id: str,
) -> tuple[Path, Path]:
    log_dir = config.resolved_log_dir() / "executors"
    log_dir.mkdir(parents=True, exist_ok=True)
    return (
        log_dir / f"{executor_id}.stdout.log",
        log_dir / f"{executor_id}.stderr.log",
    )


def workflow_process_runtime_event_path(
    config: EngineConfig,
    workflow_run_id: str,
    process_id: str,
) -> Path:
    event_dir = config.data_dir / "ipc" / "workflow_runs"
    event_dir.mkdir(parents=True, exist_ok=True)
    return event_dir / f"{workflow_run_id}.{process_id}.events.jsonl"
