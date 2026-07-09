from __future__ import annotations

import subprocess
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path

from flowweaver.common.config import EngineConfig
from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.event_router import EventRouter, RuntimeEvent
from flowweaver.engine.runtime_store import RuntimeStore, WorkflowProcess
from flowweaver.engine.supervisor_child_processes import terminate_child_process
from flowweaver.engine.supervisor_commands import (
    node_executor_command as _node_executor_command,
)
from flowweaver.engine.supervisor_commands import (
    workflow_process_command as _workflow_process_command,
)
from flowweaver.engine.supervisor_executor_events import (
    publish_executor_exited as _publish_executor_exited,
)
from flowweaver.engine.supervisor_paths import (
    child_environment as _child_environment,
)
from flowweaver.engine.supervisor_paths import (
    executor_process_log_paths as _executor_process_log_paths,
)
from flowweaver.engine.supervisor_paths import (
    workflow_process_log_paths as _workflow_process_log_paths,
)
from flowweaver.engine.supervisor_paths import (
    workflow_process_runtime_event_path as _workflow_process_runtime_event_path,
)
from flowweaver.engine.supervisor_process_launch import (
    launch_child_process as _launch_child_process,
)
from flowweaver.engine.supervisor_runtime_events import SupervisorRuntimeEventChannels
from flowweaver.engine.supervisor_workflow_processes import (
    close_workflow_children as _close_workflow_children,
)
from flowweaver.engine.supervisor_workflow_processes import (
    finish_workflow_process as _finish_workflow_process,
)
from flowweaver.engine.supervisor_workflow_processes import (
    handle_lost_workflow_process as _handle_lost_workflow_process,
)


class Supervisor:
    def __init__(
        self,
        *,
        config: EngineConfig,
        runtime_store: RuntimeStore,
        event_router: EventRouter | None = None,
        python_executable: str | None = None,
    ) -> None:
        self._config = config
        self._runtime_store = runtime_store
        self._event_router = event_router
        self._python_executable = python_executable or sys.executable
        self._children: dict[str, subprocess.Popen] = {}
        self._executor_children: dict[str, subprocess.Popen] = {}
        self._runtime_events = SupervisorRuntimeEventChannels(event_router)
        self._stop_event = threading.Event()
        self._maintenance_thread: threading.Thread | None = None

    def start_workflow_process(self, workflow_run_id: str) -> str:
        self.start()
        process = self._runtime_store.claim_workflow_process(
            workflow_run_id=workflow_run_id
        )
        if process is None:
            raise RuntimeError("RUN_ALREADY_OWNED")
        runtime_event_path = self._workflow_process_runtime_event_path(
            workflow_run_id,
            process.process_id,
        )
        self._runtime_events.register(process.process_id, runtime_event_path)
        command = _workflow_process_command(
            python_executable=self._python_executable,
            src_path=Path(__file__).resolve().parents[2],
            database_url=self._runtime_store.database_url,
            workflow_run_id=workflow_run_id,
            process=process,
            config=self._config,
            runtime_event_path=runtime_event_path,
        )
        stdout_path, stderr_path = self._workflow_process_log_paths(workflow_run_id)
        try:
            child = _launch_child_process(
                command,
                cwd=Path(__file__).resolve().parents[2],
                env=self._child_environment(),
                stdin=subprocess.DEVNULL,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            )
        except Exception as exc:
            self._runtime_store.mark_workflow_process_exited(
                process.process_id,
                exit_code=1,
                error={"message": str(exc)},
            )
            self._runtime_store.abort_workflow_run_for_process(
                process.process_id,
                reason="WORKFLOW_PROCESS_START_FAILED",
            )
            self._runtime_events.forget(process.process_id)
            raise
        self._children[process.process_id] = child
        self._runtime_store.update_workflow_process_pid(process.process_id, child.pid)
        return process.process_id

    def start_executor_process(self, *, executor_id: str | None = None) -> str:
        self.start()
        executor_id = executor_id or new_id()
        command = _node_executor_command(
            python_executable=self._python_executable,
            src_path=Path(__file__).resolve().parents[2],
            executor_id=executor_id,
        )
        stdout_path, stderr_path = self._executor_process_log_paths(executor_id)
        child = _launch_child_process(
            command,
            cwd=Path(__file__).resolve().parents[2],
            env=self._child_environment(),
            stdin=subprocess.PIPE,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        self._executor_children[executor_id] = child
        return executor_id

    def start(self) -> None:
        if self._maintenance_thread is not None and self._maintenance_thread.is_alive():
            return
        self._stop_event.clear()
        self._maintenance_thread = threading.Thread(
            target=self.maintenance_loop,
            name="flowweaver-supervisor-maintenance",
            daemon=True,
        )
        self._maintenance_thread.start()

    def maintenance_loop(self) -> None:
        interval = max(
            float(self._config.supervisor_maintenance_interval_seconds),
            0.05,
        )
        while not self._stop_event.is_set():
            try:
                self.drain_runtime_events()
                self.sweep_exited_children()
                self.sweep_exited_executors()
                self.drain_runtime_events()
                self.mark_lost_workflow_processes()
            except Exception:
                pass
            self._stop_event.wait(interval)

    def close(self) -> None:
        self._stop_event.set()
        if self._maintenance_thread is not None:
            self._maintenance_thread.join(timeout=2)
            self._maintenance_thread = None
        _close_workflow_children(
            self._runtime_store,
            self._children,
            graceful_timeout_seconds=(
                self._config.workflow_process_cancel_grace_seconds
            ),
            drain_runtime_events_for_process=self._drain_runtime_events_for_process,
            forget_runtime_event_channel=self._forget_runtime_event_channel,
        )
        for executor_id, child in list(self._executor_children.items()):
            if child.poll() is None:
                terminate_child_process(child, graceful_timeout_seconds=2)
            self._executor_children.pop(executor_id, None)
            _publish_executor_exited(
                event_router=self._event_router,
                runtime_store=self._runtime_store,
                executor_id=executor_id,
                exit_code=child.returncode if child.returncode is not None else 1,
                pid=child.pid,
            )

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
                self._drain_runtime_events_for_process(process.process_id)
                self._children.pop(process.process_id, None)
                self._finish_workflow_process(
                    process.process_id,
                    exit_code=child.returncode or 0,
                )
                self._forget_runtime_event_channel(process.process_id)
                return
            time.sleep(0.05)
        terminate_child_process(
            child,
            graceful_timeout_seconds=self._config.workflow_process_cancel_grace_seconds,
        )
        self._drain_runtime_events_for_process(process.process_id)
        self._children.pop(process.process_id, None)
        self._finish_workflow_process(
            process.process_id,
            exit_code=child.returncode if child.returncode not in (None, 0) else 1,
            error={"message": "Workflow process terminated after cancel timeout"},
        )
        self._forget_runtime_event_channel(process.process_id)

    def request_workflow_cancel(self, workflow_run_id: str) -> WorkflowProcess | None:
        return self._runtime_store.request_workflow_process_cancel(workflow_run_id)

    def sweep_exited_children(self) -> list[WorkflowProcess]:
        exited: list[WorkflowProcess] = []
        for process_id, child in list(self._children.items()):
            exit_code = child.poll()
            if exit_code is None:
                continue
            self._drain_runtime_events_for_process(process_id)
            self._children.pop(process_id, None)
            process = self._finish_workflow_process(process_id, exit_code=exit_code)
            self._drain_runtime_events_for_process(process_id)
            self._forget_runtime_event_channel(process_id)
            if process is not None:
                exited.append(process)
        return exited

    def sweep_exited_executors(self) -> list[str]:
        exited: list[str] = []
        for executor_id, child in list(self._executor_children.items()):
            exit_code = child.poll()
            if exit_code is None:
                continue
            self._executor_children.pop(executor_id, None)
            _publish_executor_exited(
                event_router=self._event_router,
                runtime_store=self._runtime_store,
                executor_id=executor_id,
                exit_code=exit_code,
                pid=child.pid,
            )
            exited.append(executor_id)
        return exited

    def mark_lost_workflow_processes(self) -> list[WorkflowProcess]:
        stale_before = utc_now() - timedelta(
            seconds=self._config.workflow_process_lost_threshold_seconds
        )
        starting_stale_before = utc_now() - timedelta(
            seconds=self._config.workflow_process_start_timeout_seconds
        )
        lost = self._runtime_store.mark_lost_workflow_processes(
            stale_before=stale_before,
            starting_stale_before=starting_stale_before,
        )
        for process in lost:
            _handle_lost_workflow_process(
                self._runtime_store,
                self._children,
                process,
                drain_runtime_events_for_process=(
                    self._drain_runtime_events_for_process
                ),
                forget_runtime_event_channel=self._forget_runtime_event_channel,
            )
        return lost

    def drain_runtime_events(self) -> list[RuntimeEvent]:
        return self._runtime_events.drain_all()

    def _child_environment(self) -> dict[str, str]:
        return _child_environment(src_path=Path(__file__).resolve().parents[2])

    def _workflow_process_log_paths(self, workflow_run_id: str) -> tuple[Path, Path]:
        return _workflow_process_log_paths(self._config, workflow_run_id)

    def _executor_process_log_paths(self, executor_id: str) -> tuple[Path, Path]:
        return _executor_process_log_paths(self._config, executor_id)

    def _workflow_process_runtime_event_path(
        self,
        workflow_run_id: str,
        process_id: str,
    ) -> Path:
        return _workflow_process_runtime_event_path(
            self._config,
            workflow_run_id,
            process_id,
        )

    def _drain_runtime_events_for_process(self, process_id: str) -> list[RuntimeEvent]:
        return self._runtime_events.drain_process(process_id)

    def _forget_runtime_event_channel(self, process_id: str) -> None:
        self._runtime_events.forget(process_id)

    def _finish_workflow_process(
        self,
        process_id: str,
        *,
        exit_code: int,
        error: dict[str, str] | None = None,
    ) -> WorkflowProcess | None:
        return _finish_workflow_process(
            self._runtime_store,
            process_id,
            exit_code=exit_code,
            error=error,
        )
