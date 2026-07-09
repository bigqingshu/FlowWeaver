from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path

from flowweaver.common.config import EngineConfig
from flowweaver.common.ids import new_id
from flowweaver.common.subprocess_command import python_module_command
from flowweaver.common.time import utc_now
from flowweaver.engine.event_router import EventRouter, RuntimeEvent
from flowweaver.engine.runtime_store import RuntimeStore, WorkflowProcess
from flowweaver.engine.supervisor_runtime_events import SupervisorRuntimeEventChannels
from flowweaver.protocols.enums import EventType
from flowweaver.protocols.events import EventModel


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
        command = [
            *python_module_command(
                python_executable=self._python_executable,
                module_name="flowweaver.workflow_process.main",
                src_path=Path(__file__).resolve().parents[2],
            ),
            "--database-url",
            self._runtime_store.database_url,
            "--workflow-run-id",
            workflow_run_id,
            "--process-id",
            process.process_id,
            "--process-generation",
            str(process.process_generation),
            "--heartbeat-interval-seconds",
            str(self._config.workflow_process_heartbeat_interval_seconds),
            "--execution-mode",
            self._config.workflow_process_execution_mode,
            "--max-concurrent-node-tasks",
            str(self._config.workflow_process_max_concurrent_node_tasks),
            "--runtime-dir",
            str(self._config.resolved_runtime_dir()),
            "--runtime-event-path",
            str(runtime_event_path),
        ]
        stdout_path, stderr_path = self._workflow_process_log_paths(workflow_run_id)
        stdout_file = stdout_path.open("ab")
        stderr_file = stderr_path.open("ab")
        try:
            child = subprocess.Popen(
                command,
                cwd=Path(__file__).resolve().parents[2],
                env=self._child_environment(),
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
            )
        except Exception as exc:
            stdout_file.close()
            stderr_file.close()
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
        finally:
            if not stdout_file.closed:
                stdout_file.close()
            if not stderr_file.closed:
                stderr_file.close()
        self._children[process.process_id] = child
        self._runtime_store.update_workflow_process_pid(process.process_id, child.pid)
        return process.process_id

    def start_executor_process(self, *, executor_id: str | None = None) -> str:
        self.start()
        executor_id = executor_id or new_id()
        command = [
            *python_module_command(
                python_executable=self._python_executable,
                module_name="flowweaver.node_executor.process",
                src_path=Path(__file__).resolve().parents[2],
            ),
            "--executor-id",
            executor_id,
        ]
        stdout_path, stderr_path = self._executor_process_log_paths(executor_id)
        stdout_file = stdout_path.open("ab")
        stderr_file = stderr_path.open("ab")
        try:
            child = subprocess.Popen(
                command,
                cwd=Path(__file__).resolve().parents[2],
                env=self._child_environment(),
                stdin=subprocess.PIPE,
                stdout=stdout_file,
                stderr=stderr_file,
            )
        finally:
            stdout_file.close()
            stderr_file.close()
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
        for process_id, child in list(self._children.items()):
            forced = False
            if child.poll() is None:
                forced = True
                child.terminate()
                try:
                    child.wait(timeout=self._config.workflow_process_cancel_grace_seconds)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=2)
            self._drain_runtime_events_for_process(process_id)
            exit_code = child.returncode if child.returncode is not None else 1
            if forced and exit_code == 0:
                exit_code = 1
            self._children.pop(process_id, None)
            self._finish_workflow_process(
                process_id,
                exit_code=exit_code,
                error=(
                    {"message": "Workflow process terminated during supervisor close"}
                    if forced
                    else None
                ),
            )
            self._forget_runtime_event_channel(process_id)
        for executor_id, child in list(self._executor_children.items()):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=2)
            self._executor_children.pop(executor_id, None)
            self._publish_executor_exited(
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
        child.terminate()
        try:
            child.wait(timeout=self._config.workflow_process_cancel_grace_seconds)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=2)
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
            self._publish_executor_exited(
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
            self._drain_runtime_events_for_process(process.process_id)
            self._children.pop(process.process_id, None)
            self._forget_runtime_event_channel(process.process_id)
            self._runtime_store.abort_workflow_run_for_process(
                process.process_id,
                reason="WORKFLOW_PROCESS_LOST",
            )
        return lost

    def drain_runtime_events(self) -> list[RuntimeEvent]:
        return self._runtime_events.drain_all()

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

    def _workflow_process_log_paths(self, workflow_run_id: str) -> tuple[Path, Path]:
        log_dir = self._config.resolved_log_dir() / "workflow_runs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return (
            log_dir / f"{workflow_run_id}.stdout.log",
            log_dir / f"{workflow_run_id}.stderr.log",
        )

    def _executor_process_log_paths(self, executor_id: str) -> tuple[Path, Path]:
        log_dir = self._config.resolved_log_dir() / "executors"
        log_dir.mkdir(parents=True, exist_ok=True)
        return (
            log_dir / f"{executor_id}.stdout.log",
            log_dir / f"{executor_id}.stderr.log",
        )

    def _workflow_process_runtime_event_path(
        self,
        workflow_run_id: str,
        process_id: str,
    ) -> Path:
        event_dir = self._config.data_dir / "ipc" / "workflow_runs"
        event_dir.mkdir(parents=True, exist_ok=True)
        return event_dir / f"{workflow_run_id}.{process_id}.events.jsonl"

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
        process = self._runtime_store.mark_workflow_process_exited(
            process_id,
            exit_code=exit_code,
            error=error,
        )
        if process is not None and exit_code != 0:
            self._runtime_store.abort_workflow_run_for_process(
                process_id,
                reason="WORKFLOW_PROCESS_EXITED_ABNORMALLY",
            )
        return process

    def _publish_executor_exited(
        self,
        *,
        executor_id: str,
        exit_code: int,
        pid: int | None,
    ) -> RuntimeEvent | None:
        event = EventModel(
            event_type=EventType.EXECUTOR_EXITED,
            payload={
                "executor_id": executor_id,
                "exit_code": exit_code,
                "pid": pid,
                "abnormal": exit_code != 0,
            },
        )
        if self._event_router is not None:
            return self._event_router.publish_event(event)
        self._runtime_store.append_runtime_event(event)
        return None
