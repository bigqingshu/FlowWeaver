from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from textwrap import dedent
from threading import Thread

import pytest
from alembic import command
from alembic.config import Config

from flowweaver.common.config import EngineConfig
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.supervisor import Supervisor
from flowweaver.plugin_runtime.discovery import discover_plugins
from flowweaver.plugin_runtime.executor import PluginExternalProcessExecutor
from flowweaver.protocols.enums import IPCMessageType, NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
    RuntimeFeedbackPolicyOverlayModel,
)
from flowweaver.workflow_process.main import run_workflow_process


def test_plugin_applies_dynamic_runtime_feedback_before_sending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "flowweaver.workflow_process.runtime_options_controller."
        "RUNTIME_OPTIONS_POLL_INTERVAL_SECONDS",
        0.01,
    )
    plugin_root = tmp_path / "plugins"
    package = _write_runtime_plugin(plugin_root)
    store = _make_store(tmp_path)
    run, process = _create_claimed_run(
        store,
        workflow_id="workflow-plugin-feedback",
        workflow_run_id="run-plugin-feedback",
        mode="feedback",
        marker="feedback",
        runtime_options={"workflow": {"profile": "diagnostic"}},
    )
    exit_codes: list[int] = []
    worker = Thread(
        target=lambda: exit_codes.append(
            run_workflow_process(
                store=store,
                workflow_run_id=run.workflow_run_id,
                process_id=process.process_id,
                process_generation=process.process_generation,
                heartbeat_interval_seconds=0.01,
                runtime_dir=tmp_path / "runtime" / "workflow_runs",
                plugin_dir=plugin_root,
            )
        )
    )
    worker.start()
    try:
        assert _wait_until(lambda: (package / "feedback.started").is_file())
        assert _wait_until(
            lambda: _event_message_exists(store, "pre-debug")
            and _event_stage_exists(store, "pre-update")
        )
        initial_node = store.list_node_runs(run.workflow_run_id)[0]
        initial_heartbeat = initial_node.last_heartbeat
        requested = store.replace_workflow_run_runtime_options(
            run.workflow_run_id,
            expected_version=0,
            overlay=RuntimeFeedbackPolicyOverlayModel.model_validate(
                {
                    "workflow": {
                        "telemetry": {
                            "log_level": "WARN",
                            "event_level": "basic",
                            "progress_enabled": False,
                        },
                        "diagnostics": {
                            "include_metrics": False,
                            "redact_columns": ["password"],
                            "mask_policy": "full",
                        },
                    }
                }
            ),
        )
        worker.join(timeout=10)
        assert not worker.is_alive()
        queued_event = next(
            event
            for event in store.list_runtime_events()
            if event.event_type == "NODE_QUEUED"
        )
        stored_task = store.get_node_task(queued_event.payload["task_id"])
        node_run = store.list_node_runs(run.workflow_run_id)[0]
        events = store.list_runtime_events()
    finally:
        if worker.is_alive():
            store.request_workflow_process_cancel(run.workflow_run_id)
            worker.join(timeout=5)
        store.dispose()

    assert exit_codes == [0]
    assert stored_task is not None
    assert stored_task.runtime_options_version == requested.requested_version
    assert node_run.executor_id == "plugin-external-process-executor"
    assert node_run.last_heartbeat is not None
    assert initial_heartbeat is not None
    assert node_run.last_heartbeat > initial_heartbeat
    messages = [
        event.payload["message"]
        for event in events
        if event.event_type == "NODE_LOG"
    ]
    assert "pre-debug" in messages
    assert "post-warn" in messages
    assert "post-debug" not in messages
    assert "post-info" not in messages
    assert "spoofed-log" not in messages
    assert not _event_stage_exists_in(events, "post-update")
    post_warn = next(
        event
        for event in events
        if event.event_type == "NODE_LOG"
        and event.payload["message"] == "post-warn"
    )
    assert post_warn.payload["context"] == {
        "password": "***",
        "message": "kept",
    }
    sent_events = _read_json_lines(package / "feedback.sent-events.jsonl")
    sent_messages = [
        event["payload"]["message"]
        for event in sent_events
        if event["message_type"] == "NODE_TASK_LOG"
    ]
    assert "post-warn" in sent_messages
    assert "post-debug" not in sent_messages
    assert "post-info" not in sent_messages
    assert not any(
        event["message_type"] == "NODE_TASK_PROGRESS"
        and event["payload"].get("current_stage") == "post-update"
        for event in sent_events
    )
    assert (package / "feedback.runtime-update-count").read_text(
        encoding="utf-8"
    ) == "1"


def test_plugin_rejects_wrong_task_and_old_runtime_options_update(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_runtime_plugin(plugin_root)
    policy = _feedback_policy(log_level="DEBUG", progress_enabled=True)
    updated_policy = _feedback_policy(log_level="WARN", progress_enabled=False)
    task = NodeTaskModel(
        task_id="task-direct-update",
        workflow_run_id="run-direct-update",
        workflow_process_id="process-direct-update",
        process_generation=1,
        node_run_id="node-direct-update",
        node_instance_id="plugin",
        node_type="plugin.example.runtime_feedback",
        node_version="1.0",
        attempt=1,
        input_refs=[],
        config={
            "enable_execute": True,
            "mode": "feedback",
            "marker": "direct-update",
        },
        runtime_feedback_policy=policy,
        runtime_options_version=0,
        timeout_seconds=30,
    )
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
    )
    events = []
    executor.set_event_handler(lambda _task, envelope: events.append(envelope))
    results = []
    worker = Thread(target=lambda: results.append(executor.execute(task)))
    worker.start()
    try:
        assert _wait_until(lambda: (package / "direct-update.started").is_file())
        wrong_task = task.model_copy(update={"task_id": "wrong-task"})
        assert executor.request_runtime_options_update(
            wrong_task,
            runtime_options_version=1,
            runtime_feedback_policy=updated_policy,
        ) is False
        assert executor.request_runtime_options_update(
            task,
            runtime_options_version=0,
            runtime_feedback_policy=updated_policy,
        ) is True
        time.sleep(0.05)
        assert not (package / "direct-update.runtime-update-count").exists()
        assert executor.request_runtime_options_update(
            task,
            runtime_options_version=1,
            runtime_feedback_policy=updated_policy,
        ) is True
        worker.join(timeout=10)
    finally:
        if worker.is_alive():
            executor.close()
            worker.join(timeout=5)
        executor.close()

    assert len(results) == 1
    assert results[0].status == NodeResultStatus.SUCCEEDED
    applied = [
        event
        for event in events
        if event.message_type == IPCMessageType.NODE_TASK_RUNTIME_OPTIONS_APPLIED
    ]
    assert [event.payload["runtime_options_version"] for event in applied] == [1]
    assert (package / "direct-update.runtime-update-count").read_text(
        encoding="utf-8"
    ) == "1"


def test_plugin_cooperative_cancel_closes_process(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_runtime_plugin(plugin_root)
    store = _make_store(tmp_path)
    run, process = _create_claimed_run(
        store,
        workflow_id="workflow-plugin-cancel",
        workflow_run_id="run-plugin-cancel",
        mode="cooperative_cancel",
        marker="cancel",
    )
    exit_codes: list[int] = []
    worker = Thread(
        target=lambda: exit_codes.append(
            run_workflow_process(
                store=store,
                workflow_run_id=run.workflow_run_id,
                process_id=process.process_id,
                process_generation=process.process_generation,
                heartbeat_interval_seconds=0.01,
                runtime_dir=tmp_path / "runtime" / "workflow_runs",
                plugin_dir=plugin_root,
                execution_mode="threaded",
                cancel_grace_seconds=2,
            )
        )
    )
    worker.start()
    try:
        pid_path = package / "cancel.plugin.pid"
        assert _wait_until(pid_path.is_file)
        plugin_pid = int(pid_path.read_text(encoding="utf-8"))
        store.request_workflow_process_cancel(run.workflow_run_id)
        worker.join(timeout=10)
        node_run = store.list_node_runs(run.workflow_run_id)[0]
        workflow_run = store.get_workflow_run(run.workflow_run_id)
    finally:
        if worker.is_alive():
            store.request_workflow_process_cancel(run.workflow_run_id)
            worker.join(timeout=5)
        store.dispose()

    assert exit_codes == [0]
    assert (package / "cancel.cancel-received").is_file()
    assert workflow_run is not None
    assert workflow_run.status == "CANCELLED"
    assert node_run.status == "CANCELLED"
    assert _wait_until(lambda: not _process_exists(plugin_pid))


def test_plugin_timeout_forces_process_exit(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_runtime_plugin(plugin_root)
    store = _make_store(tmp_path)
    run, process = _create_claimed_run(
        store,
        workflow_id="workflow-plugin-timeout",
        workflow_run_id="run-plugin-timeout",
        mode="ignore_cancel",
        marker="timeout",
        timeout_seconds=1,
    )

    try:
        exit_code = run_workflow_process(
            store=store,
            workflow_run_id=run.workflow_run_id,
            process_id=process.process_id,
            process_generation=process.process_generation,
            heartbeat_interval_seconds=0.01,
            runtime_dir=tmp_path / "runtime" / "workflow_runs",
            plugin_dir=plugin_root,
            execution_mode="threaded",
        )
        plugin_pid = int(
            (package / "timeout.plugin.pid").read_text(encoding="utf-8")
        )
        node_run = store.list_node_runs(run.workflow_run_id)[0]
        workflow_run = store.get_workflow_run(run.workflow_run_id)
    finally:
        store.dispose()

    assert exit_code == 0
    assert workflow_run is not None
    assert workflow_run.status == "FAILED"
    assert node_run.status == "TIMED_OUT"
    assert node_run.error is not None
    assert node_run.error["timeout_seconds"] == 1
    assert _wait_until(lambda: not _process_exists(plugin_pid))


def test_plugin_ignoring_cancel_is_forced_after_grace(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_runtime_plugin(plugin_root)
    store = _make_store(tmp_path)
    run, process = _create_claimed_run(
        store,
        workflow_id="workflow-plugin-forced-cancel",
        workflow_run_id="run-plugin-forced-cancel",
        mode="ignore_cancel",
        marker="forced-cancel",
    )
    exit_codes: list[int] = []
    worker = Thread(
        target=lambda: exit_codes.append(
            run_workflow_process(
                store=store,
                workflow_run_id=run.workflow_run_id,
                process_id=process.process_id,
                process_generation=process.process_generation,
                heartbeat_interval_seconds=0.01,
                runtime_dir=tmp_path / "runtime" / "workflow_runs",
                plugin_dir=plugin_root,
                execution_mode="threaded",
                cancel_grace_seconds=0.1,
            )
        )
    )
    worker.start()
    try:
        pid_path = package / "forced-cancel.plugin.pid"
        assert _wait_until(pid_path.is_file)
        plugin_pid = _read_pid(pid_path)
        store.request_workflow_process_cancel(run.workflow_run_id)
        worker.join(timeout=10)
        node_run = store.list_node_runs(run.workflow_run_id)[0]
        workflow_run = store.get_workflow_run(run.workflow_run_id)
    finally:
        if worker.is_alive():
            store.request_workflow_process_cancel(run.workflow_run_id)
            worker.join(timeout=5)
        store.dispose()

    assert exit_codes == [0]
    assert workflow_run is not None
    assert workflow_run.status == "CANCELLED"
    assert node_run.status == "CANCELLED"
    assert node_run.error is not None
    assert node_run.error["reason"] == "WORKFLOW_CANCEL_GRACE_EXPIRED"
    assert _wait_until(lambda: not _process_exists(plugin_pid))


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Object test")
def test_workflow_job_closes_only_its_plugin_process_tree(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_runtime_plugin(plugin_root)
    store = _make_store(tmp_path)
    first_run = _create_run(
        store,
        workflow_id="workflow-tree-first",
        workflow_run_id="run-tree-first",
        mode="process_tree",
        marker="tree-first",
    )
    second_run = _create_run(
        store,
        workflow_id="workflow-tree-second",
        workflow_run_id="run-tree-second",
        mode="process_tree",
        marker="tree-second",
    )
    supervisor = Supervisor(
        config=EngineConfig(
            data_dir=tmp_path / "runtime",
            plugin_dir=plugin_root,
            enforce_single_instance=False,
            workflow_process_heartbeat_interval_seconds=0,
            supervisor_maintenance_interval_seconds=60,
        ),
        runtime_store=store,
        python_executable=sys.executable,
    )
    first_process_id = supervisor.start_workflow_process(
        first_run.workflow_run_id
    )
    second_process_id = supervisor.start_workflow_process(
        second_run.workflow_run_id
    )
    first_plugin_pid = first_child_pid = second_plugin_pid = 0
    try:
        assert _wait_until(
            lambda: (package / "tree-first.child.pid").is_file()
            and (package / "tree-second.child.pid").is_file(),
            timeout_seconds=15,
        )
        first_plugin_pid = _read_pid(package / "tree-first.plugin.pid")
        first_child_pid = _read_pid(package / "tree-first.child.pid")
        second_plugin_pid = _read_pid(package / "tree-second.plugin.pid")
        first_workflow_child = supervisor._children[first_process_id]
        first_workflow_child.kill()
        first_workflow_child.wait(timeout=5)
        supervisor.sweep_exited_children()

        assert _wait_until(lambda: not _process_exists(first_plugin_pid))
        assert _wait_until(lambda: not _process_exists(first_child_pid))
        assert supervisor._children[second_process_id].poll() is None
        assert _process_exists(second_plugin_pid)
        assert first_process_id not in supervisor._workflow_jobs
        assert second_process_id in supervisor._workflow_jobs
    finally:
        supervisor.close()
        store.dispose()

    assert _wait_until(lambda: not _process_exists(second_plugin_pid))


def _create_claimed_run(
    store: RuntimeStore,
    *,
    workflow_id: str,
    workflow_run_id: str,
    mode: str,
    marker: str,
    timeout_seconds: int | None = None,
    runtime_options: dict | None = None,
):
    run = _create_run(
        store,
        workflow_id=workflow_id,
        workflow_run_id=workflow_run_id,
        mode=mode,
        marker=marker,
        timeout_seconds=timeout_seconds,
        runtime_options=runtime_options,
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id=f"process-{marker}",
    )
    assert process is not None
    return run, process


def _create_run(
    store: RuntimeStore,
    *,
    workflow_id: str,
    workflow_run_id: str,
    mode: str,
    marker: str,
    timeout_seconds: int | None = None,
    runtime_options: dict | None = None,
):
    config: dict[str, object] = {
        "enable_execute": True,
        "mode": mode,
        "marker": marker,
    }
    if timeout_seconds is not None:
        config["timeout_seconds"] = timeout_seconds
    definition: dict[str, object] = {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "plugin",
                "node_type": "plugin.example.runtime_feedback",
                "node_version": "1.0",
                "config": config,
            }
        ],
        "connections": [],
    }
    if runtime_options is not None:
        definition["runtime_options"] = runtime_options
    workflow = store.create_workflow_definition(
        name=f"Plugin runtime {marker}",
        workflow_id=workflow_id,
        definition=definition,
    )
    return store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id=workflow_run_id,
    )


def _make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")
    return RuntimeStore.from_sqlite_path(database_path)


def _write_runtime_plugin(plugin_root: Path) -> Path:
    package = plugin_root / "runtime_feedback"
    package.mkdir(parents=True)
    (package / "runner.py").write_text(_runner_source(), encoding="utf-8")
    manifest = {
        "manifest_version": "1",
        "plugin_id": "example.runtime_feedback",
        "plugin_version": "1.0.0",
        "node_type": "plugin.example.runtime_feedback",
        "node_version": "1.0",
        "display_name": "Runtime Feedback",
        "category": "test",
        "config_schema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "enum",
                    "required": True,
                    "enum": [
                        "feedback",
                        "cooperative_cancel",
                        "ignore_cancel",
                        "process_tree",
                    ],
                },
                "marker": {"type": "string", "required": True},
            },
        },
        "input_ports": [],
        "output_ports": [],
        "input_table_slots": [],
        "output_table_slots": [],
        "execution_mode": "external_process",
        "protocol": "flowweaver.plugin-jsonl.v1",
        "entrypoint": "runner.py",
        "external_actions": False,
    }
    (package / "plugin.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    return package


def _runner_source() -> str:
    return dedent(
        r'''
        import argparse
        import json
        import os
        import subprocess
        import sys
        import time
        from pathlib import Path
        from threading import Event, Lock, Thread

        parser = argparse.ArgumentParser()
        parser.add_argument("--executor-id", required=True)
        args = parser.parse_args()
        output_lock = Lock()
        state_lock = Lock()
        cancel_event = Event()
        task = None
        policy = None
        runtime_options_version = 0
        runtime_update_count = 0
        marker = "plugin"
        mode = "ignore_cancel"

        def write_json(path, value):
            Path(path).write_text(str(value), encoding="utf-8")

        def emit(message_type, payload, *, active_task=None, record=True):
            envelope = {"message_type": message_type, "payload": payload}
            if active_task is not None:
                envelope["workflow_run_id"] = active_task["workflow_run_id"]
                envelope["node_run_id"] = active_task["node_run_id"]
            if record and active_task is not None:
                with Path(f"{marker}.sent-events.jsonl").open(
                    "a",
                    encoding="utf-8",
                ) as stream:
                    stream.write(json.dumps(envelope) + "\n")
            with output_lock:
                try:
                    print(json.dumps(envelope), flush=True)
                except BrokenPipeError:
                    return False
            return True

        def policy_snapshot():
            with state_lock:
                return policy, runtime_options_version

        def level_enabled(configured, message_level):
            levels = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
            return levels.get(message_level, 0) >= levels.get(configured, 100)

        def sanitize_context(context, current_policy, level):
            diagnostics = (current_policy or {}).get("diagnostics", {})
            cleaned = {
                key: value
                for key, value in context.items()
                if key not in {"rows", "records", "binary"}
            }
            if not diagnostics.get("include_metrics", True):
                cleaned.pop("metrics", None)
            for column in diagnostics.get("redact_columns", []):
                if column in cleaned:
                    cleaned[column] = "***"
            if level == "ERROR" and not diagnostics.get(
                "capture_error_context",
                True,
            ):
                cleaned = {
                    key: value
                    for key, value in cleaned.items()
                    if key in {"message", "error_code", "reason"}
                }
            return cleaned

        def emit_log(active_task, level, message, context):
            current_policy, _version = policy_snapshot()
            telemetry = (current_policy or {}).get("telemetry", {})
            if not level_enabled(telemetry.get("log_level", "DEBUG"), level):
                return False
            return emit(
                "NODE_TASK_LOG",
                {
                    "level": level,
                    "message": message[:1024],
                    "logger_name": "example.runtime_feedback",
                    "node_instance_id": active_task["node_instance_id"],
                    "task_id": active_task["task_id"],
                    "context": sanitize_context(context, current_policy, level),
                },
                active_task=active_task,
            )

        def emit_progress(active_task, stage):
            current_policy, _version = policy_snapshot()
            telemetry = (current_policy or {}).get("telemetry", {})
            if not telemetry.get("progress_enabled", True):
                return False
            if telemetry.get("event_level", "verbose") not in {
                "progress",
                "verbose",
            }:
                return False
            metrics = {"ticks": 1}
            diagnostics = (current_policy or {}).get("diagnostics", {})
            if not diagnostics.get("include_metrics", True):
                metrics = {}
            return emit(
                "NODE_TASK_PROGRESS",
                {
                    "progress": 0.5,
                    "current_stage": stage,
                    "metrics": metrics,
                },
                active_task=active_task,
            )

        def emit_heartbeat(active_task):
            emit(
                "NODE_TASK_HEARTBEAT",
                {
                    "executor_id": args.executor_id,
                    "task_id": active_task["task_id"],
                    "attempt": active_task["attempt"],
                },
                active_task=active_task,
                record=False,
            )

        def terminal(active_task, status, error=None):
            result = {
                "task_id": active_task["task_id"],
                "node_run_id": active_task["node_run_id"],
                "attempt": active_task["attempt"],
                "executor_id": args.executor_id,
                "process_generation": active_task["process_generation"],
                "status": status,
                "summary": {"mode": mode},
                "error": error,
            }
            emit(
                "NODE_TASK_COMPLETED",
                {"result": result},
                active_task=active_task,
                record=False,
            )

        def run_feedback(active_task):
            emit(
                "NODE_TASK_LOG",
                {
                    "level": "ERROR",
                    "message": "spoofed-log",
                    "logger_name": "example.runtime_feedback",
                    "node_instance_id": active_task["node_instance_id"],
                    "task_id": active_task["task_id"],
                    "context": {},
                },
                active_task={**active_task, "workflow_run_id": "wrong-run"},
            )
            emit_log(active_task, "DEBUG", "pre-debug", {"metrics": {"x": 1}})
            emit_progress(active_task, "pre-update")
            initial_version = active_task.get("runtime_options_version", 0)
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                emit_heartbeat(active_task)
                if cancel_event.is_set():
                    terminal(
                        active_task,
                        "CANCELLED",
                        {
                            "message": "Node task cancelled cooperatively",
                            "reason": "WORKFLOW_CANCEL_REQUESTED",
                        },
                    )
                    return
                _current_policy, version = policy_snapshot()
                if version > initial_version:
                    break
                time.sleep(0.02)
            emit_heartbeat(active_task)
            emit_log(active_task, "DEBUG", "post-debug", {})
            emit_log(active_task, "INFO", "post-info", {})
            emit_log(
                active_task,
                "WARN",
                "post-warn",
                {
                    "password": "secret",
                    "metrics": {"value": 1},
                    "rows": [{"value": 1}],
                    "message": "kept",
                },
            )
            emit_progress(active_task, "post-update")
            time.sleep(0.05)
            emit_heartbeat(active_task)
            terminal(active_task, "SUCCEEDED")

        def run_cooperative_cancel(active_task):
            while not cancel_event.wait(0.02):
                emit_heartbeat(active_task)
            write_json(f"{marker}.cancel-received", "yes")
            terminal(
                active_task,
                "CANCELLED",
                {
                    "message": "Node task cancelled cooperatively",
                    "reason": "WORKFLOW_CANCEL_REQUESTED",
                },
            )

        def run_forever(active_task, *, spawn_child=False):
            child = None
            if spawn_child:
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        "import time; time.sleep(300)",
                    ]
                )
                write_json(f"{marker}.child.pid", child.pid)
            while True:
                emit_heartbeat(active_task)
                time.sleep(0.05)

        def start_task(active_task):
            write_json(f"{marker}.plugin.pid", os.getpid())
            write_json(f"{marker}.started", "yes")
            if mode == "feedback":
                target = run_feedback
            elif mode == "cooperative_cancel":
                target = run_cooperative_cancel
            elif mode == "process_tree":
                target = lambda value: run_forever(value, spawn_child=True)
            else:
                target = run_forever
            worker = Thread(target=target, args=(active_task,), daemon=False)
            worker.start()
            return worker

        emit("EXECUTOR_READY", {"executor_id": args.executor_id}, record=False)
        worker = None
        for line in sys.stdin:
            message = json.loads(line)
            message_type = message.get("message_type")
            if message_type == "NODE_TASK_SUBMIT":
                task = message["payload"]
                mode = task["config"]["mode"]
                marker = task["config"]["marker"]
                with state_lock:
                    policy = task.get("runtime_feedback_policy")
                    runtime_options_version = task.get(
                        "runtime_options_version",
                        0,
                    )
                worker = start_task(task)
                continue
            if message_type == "NODE_TASK_RUNTIME_OPTIONS_UPDATE" and task:
                payload = message["payload"]
                if payload.get("task_id") != task["task_id"]:
                    continue
                with state_lock:
                    if payload["runtime_options_version"] <= runtime_options_version:
                        continue
                    policy = payload["runtime_feedback_policy"]
                    runtime_options_version = payload["runtime_options_version"]
                    runtime_update_count += 1
                    applied_version = runtime_options_version
                write_json(
                    f"{marker}.runtime-update-count",
                    runtime_update_count,
                )
                emit(
                    "NODE_TASK_RUNTIME_OPTIONS_APPLIED",
                    {
                        "task_id": task["task_id"],
                        "runtime_options_version": applied_version,
                    },
                    active_task=task,
                    record=False,
                )
                continue
            if message_type == "NODE_TASK_CANCEL_REQUEST" and task:
                payload = message["payload"]
                if payload.get("task_id") == task["task_id"]:
                    cancel_event.set()
        if worker is not None:
            worker.join()
        '''
    )


def _event_message_exists(store: RuntimeStore, message: str) -> bool:
    return any(
        event.event_type == "NODE_LOG" and event.payload.get("message") == message
        for event in store.list_runtime_events()
    )


def _event_stage_exists(store: RuntimeStore, stage: str) -> bool:
    return _event_stage_exists_in(store.list_runtime_events(), stage)


def _event_stage_exists_in(events, stage: str) -> bool:
    return any(
        event.event_type == "NODE_PROGRESS"
        and event.payload.get("current_stage") == stage
        for event in events
    )


def _read_json_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _read_pid(path: Path) -> int:
    return int(path.read_text(encoding="utf-8"))


def _feedback_policy(
    *,
    log_level: str,
    progress_enabled: bool,
) -> ResolvedRuntimeFeedbackPolicyModel:
    return ResolvedRuntimeFeedbackPolicyModel.model_validate(
        {
            "telemetry": {
                "log_level": log_level,
                "event_level": "verbose",
                "event_rate_limit_per_second": 0,
                "progress_enabled": progress_enabled,
                "progress_interval_seconds": 0,
            },
            "diagnostics": {
                "capture_error_context": True,
                "include_metrics": True,
                "payload_byte_limit": 65536,
                "redact_columns": [],
                "mask_policy": "partial",
            },
        }
    )


def _wait_until(predicate, *, timeout_seconds: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    import ctypes

    process_query_limited_information = 0x1000
    still_active = 259
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(
        process_query_limited_information,
        False,
        pid,
    )
    if not handle:
        return False
    try:
        exit_code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == still_active
    finally:
        kernel32.CloseHandle(handle)
