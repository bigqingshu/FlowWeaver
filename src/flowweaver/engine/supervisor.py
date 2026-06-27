from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

from flowweaver.common.config import EngineConfig
from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore, WorkflowProcess


class Supervisor:
    def __init__(
        self,
        *,
        config: EngineConfig,
        runtime_store: RuntimeStore,
        python_executable: str | None = None,
    ) -> None:
        self._config = config
        self._runtime_store = runtime_store
        self._python_executable = python_executable or sys.executable
        self._children: dict[str, subprocess.Popen] = {}

    def start_workflow_process(self, workflow_run_id: str) -> str:
        process = self._runtime_store.create_workflow_process(
            workflow_run_id=workflow_run_id
        )
        src_path = Path(__file__).resolve().parents[2]
        command = [
            self._python_executable,
            "-c",
            (
                "import sys; "
                f"sys.path.insert(0, {str(src_path)!r}); "
                "from flowweaver.workflow_process.main import main; "
                "raise SystemExit(main())"
            ),
            "--database-url",
            self._runtime_store.database_url,
            "--workflow-run-id",
            workflow_run_id,
            "--process-id",
            process.process_id,
            "--heartbeat-interval-seconds",
            str(self._config.workflow_process_heartbeat_interval_seconds),
        ]
        try:
            child = subprocess.Popen(
                command,
                cwd=Path.cwd(),
                env=self._child_environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            self._runtime_store.mark_workflow_process_exited(
                process.process_id,
                exit_code=1,
                error={"message": str(exc)},
            )
            raise
        self._children[process.process_id] = child
        self._runtime_store.update_workflow_process_pid(process.process_id, child.pid)
        return process.process_id

    def stop_workflow_process(
        self,
        workflow_run_id: str,
        graceful_timeout_seconds: int,
    ) -> None:
        process = self.request_workflow_cancel(workflow_run_id)
        if process is None:
            return
        child = self._children.get(process.process_id)
        if child is None:
            return
        deadline = time.monotonic() + graceful_timeout_seconds
        while time.monotonic() < deadline:
            if child.poll() is not None:
                self._runtime_store.mark_workflow_process_exited(
                    process.process_id,
                    exit_code=child.returncode or 0,
                )
                return
            time.sleep(0.05)
        child.terminate()
        self._runtime_store.mark_workflow_process_exited(
            process.process_id,
            exit_code=1,
            error={"message": "Workflow process terminated after cancel timeout"},
        )

    def request_workflow_cancel(self, workflow_run_id: str) -> WorkflowProcess | None:
        return self._runtime_store.request_workflow_process_cancel(workflow_run_id)

    def sweep_exited_children(self) -> list[WorkflowProcess]:
        exited: list[WorkflowProcess] = []
        for process_id, child in list(self._children.items()):
            exit_code = child.poll()
            if exit_code is None:
                continue
            self._children.pop(process_id, None)
            process = self._runtime_store.mark_workflow_process_exited(
                process_id,
                exit_code=exit_code,
            )
            if process is not None:
                exited.append(process)
        return exited

    def mark_lost_workflow_processes(self) -> list[WorkflowProcess]:
        stale_before = utc_now() - timedelta(
            seconds=self._config.workflow_process_lost_threshold_seconds
        )
        return self._runtime_store.mark_lost_workflow_processes(
            stale_before=stale_before
        )

    def _child_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        src_path = Path(__file__).resolve().parents[2]
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            str(src_path)
            if not existing_pythonpath
            else f"{src_path}{os.pathsep}{existing_pythonpath}"
        )
        return env
