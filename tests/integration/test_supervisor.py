from __future__ import annotations

import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from flowweaver.common.config import EngineConfig
from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.supervisor import Supervisor
from flowweaver.protocols.enums import NodeRunStatus, WorkflowRunStatus


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    return RuntimeStore.from_sqlite_path(database_path)


def non_empty_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "source",
                "node_type": "core.source",
                "node_version": "1.0",
            }
        ],
        "connections": [],
    }


def create_run(store: RuntimeStore, *, definition: dict | None = None):
    workflow = store.create_workflow_definition(
        name="Supervisor workflow",
        definition=definition
        or {"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-1",
    )
    return store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
        status=WorkflowRunStatus.PENDING,
    )


def test_supervisor_sweeps_crashed_workflow_process_without_breaking_host(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run = create_run(store)
    process = store.create_workflow_process(workflow_run_id=run.workflow_run_id)
    supervisor = Supervisor(
        config=EngineConfig(
            data_dir=tmp_path / "runtime",
            enforce_single_instance=False,
        ),
        runtime_store=store,
        python_executable=sys.executable,
    )
    child = subprocess.Popen(
        [sys.executable, "-c", "raise SystemExit(7)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    supervisor._children[process.process_id] = child

    try:
        deadline = time.monotonic() + 5
        swept = []
        while time.monotonic() < deadline:
            swept = supervisor.sweep_exited_children()
            if swept:
                break
            time.sleep(0.05)
    finally:
        if child.poll() is None:
            child.terminate()

    loaded_process = store.get_workflow_process(process.process_id)
    assert [item.process_id for item in swept] == [process.process_id]
    assert loaded_process is not None
    assert loaded_process.status == "FAILED"
    assert loaded_process.exit_code == 7
    assert store.get_workflow_run(run.workflow_run_id) is not None


def test_supervisor_marks_stale_workflow_process_lost(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run = create_run(store)
    process = store.create_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    store.record_workflow_process_heartbeat(process.process_id)
    supervisor = Supervisor(
        config=EngineConfig(
            data_dir=tmp_path / "runtime",
            enforce_single_instance=False,
            workflow_process_lost_threshold_seconds=0,
        ),
        runtime_store=store,
    )

    lost = supervisor.mark_lost_workflow_processes()

    loaded_process = store.get_workflow_process(process.process_id)
    assert [item.process_id for item in lost] == [process.process_id]
    assert loaded_process is not None
    assert loaded_process.status == "LOST"
    assert loaded_process.exited_at is not None
    assert loaded_process.exit_code is None


def test_supervisor_does_not_mark_fresh_workflow_process_lost(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run = create_run(store)
    process = store.create_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    store.record_workflow_process_heartbeat(process.process_id)
    supervisor = Supervisor(
        config=EngineConfig(
            data_dir=tmp_path / "runtime",
            enforce_single_instance=False,
            workflow_process_lost_threshold_seconds=60,
        ),
        runtime_store=store,
    )

    lost = supervisor.mark_lost_workflow_processes()

    loaded_process = store.get_workflow_process(process.process_id)
    assert lost == []
    assert loaded_process is not None
    assert loaded_process.status == "RUNNING"


def test_supervisor_rejects_duplicate_active_workflow_process_and_writes_logs(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run = create_run(store, definition=non_empty_definition())
    supervisor = Supervisor(
        config=EngineConfig(
            data_dir=tmp_path / "runtime",
            enforce_single_instance=False,
            workflow_process_heartbeat_interval_seconds=0,
            workflow_process_lost_threshold_seconds=60,
        ),
        runtime_store=store,
        python_executable=sys.executable,
    )

    first_process_id = supervisor.start_workflow_process(run.workflow_run_id)
    try:
        with pytest.raises(RuntimeError, match="RUN_ALREADY_OWNED"):
            supervisor.start_workflow_process(run.workflow_run_id)

        process = store.get_workflow_process(first_process_id)
        stdout_log = (
            tmp_path
            / "runtime"
            / "logs"
            / "workflow_runs"
            / f"{run.workflow_run_id}.stdout.log"
        )
        stderr_log = stdout_log.with_name(f"{run.workflow_run_id}.stderr.log")

        assert process is not None
        assert process.process_generation == 1
        assert process.fencing_token is not None
        assert stdout_log.exists()
        assert stderr_log.exists()
    finally:
        supervisor.close()


def test_supervisor_completes_workflow_with_default_subprocess_executor(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run = create_run(store, definition=non_empty_definition())
    supervisor = Supervisor(
        config=EngineConfig(
            data_dir=tmp_path / "runtime",
            enforce_single_instance=False,
            workflow_process_heartbeat_interval_seconds=0,
            workflow_process_lost_threshold_seconds=60,
            supervisor_maintenance_interval_seconds=60,
        ),
        runtime_store=store,
        python_executable=sys.executable,
    )

    process_id = supervisor.start_workflow_process(run.workflow_run_id)
    loaded_run = store.get_workflow_run(run.workflow_run_id)
    loaded_process = store.get_workflow_process(process_id)
    node_runs = []
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            supervisor.sweep_exited_children()
            loaded_run = store.get_workflow_run(run.workflow_run_id)
            loaded_process = store.get_workflow_process(process_id)
            node_runs = store.list_node_runs(run.workflow_run_id)
            if (
                loaded_run is not None
                and loaded_run.status == "SUCCEEDED"
                and loaded_process is not None
                and loaded_process.status == "EXITED"
            ):
                break
            time.sleep(0.05)
    finally:
        supervisor.close()

    assert loaded_run is not None
    assert loaded_run.status == "SUCCEEDED"
    assert loaded_process is not None
    assert loaded_process.status == "EXITED"
    assert loaded_process.exit_code == 0
    assert {node.node_instance_id: node.status for node in node_runs} == {
        "source": "SUCCEEDED",
    }
    assert {node.executor_id for node in node_runs} == {"subprocess-node-executor"}


def test_supervisor_close_terminates_running_child_and_aborts_run(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run = create_run(store, definition=non_empty_definition())
    supervisor = Supervisor(
        config=EngineConfig(
            data_dir=tmp_path / "runtime",
            enforce_single_instance=False,
            workflow_process_heartbeat_interval_seconds=0,
            workflow_process_lost_threshold_seconds=60,
            workflow_process_cancel_grace_seconds=1,
        ),
        runtime_store=store,
        python_executable=sys.executable,
    )
    process_id = supervisor.start_workflow_process(run.workflow_run_id)

    supervisor.close()

    loaded_process = store.get_workflow_process(process_id)
    loaded_run = store.get_workflow_run(run.workflow_run_id)
    assert supervisor._children == {}
    assert loaded_process is not None
    assert loaded_process.status == "FAILED"
    assert loaded_process.exited_at is not None
    assert loaded_run is not None
    assert loaded_run.status == "ABORTED"


def test_stale_workflow_process_generation_cannot_write_run_or_node(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run = create_run(store)
    process_a = store.claim_workflow_process(workflow_run_id=run.workflow_run_id)
    assert process_a is not None
    store.record_workflow_process_heartbeat(
        process_a.process_id,
        process_generation=process_a.process_generation,
    )
    running = store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        owner_process_id=process_a.process_id,
        process_generation=process_a.process_generation,
    )
    assert running is not None
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
        node_type="core.source",
        status=NodeRunStatus.READY,
        owner_process_id=process_a.process_id,
        process_generation=process_a.process_generation,
    )
    store.mark_lost_workflow_processes(
        stale_before=utc_now() + timedelta(seconds=1),
    )
    process_b = store.claim_workflow_process(workflow_run_id=run.workflow_run_id)
    assert process_b is not None

    stale_run_update = store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.SUCCEEDED,
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
        owner_process_id=process_a.process_id,
        process_generation=process_a.process_generation,
    )
    stale_node_update = store.update_node_run_status(
        node.node_run_id,
        NodeRunStatus.QUEUED,
        allowed_source_statuses=[NodeRunStatus.READY],
        owner_process_id=process_a.process_id,
        process_generation=process_a.process_generation,
    )

    assert stale_run_update is None
    assert stale_node_update is None
    assert store.workflow_run_is_owned_by(
        workflow_run_id=run.workflow_run_id,
        process_id=process_b.process_id,
        process_generation=process_b.process_generation,
    )


def test_supervisor_marks_starting_process_without_heartbeat_lost_and_aborts_run(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run = create_run(store)
    process = store.claim_workflow_process(workflow_run_id=run.workflow_run_id)
    assert process is not None
    supervisor = Supervisor(
        config=EngineConfig(
            data_dir=tmp_path / "runtime",
            enforce_single_instance=False,
            workflow_process_start_timeout_seconds=0,
            workflow_process_lost_threshold_seconds=60,
        ),
        runtime_store=store,
    )

    lost = supervisor.mark_lost_workflow_processes()

    loaded_process = store.get_workflow_process(process.process_id)
    loaded_run = store.get_workflow_run(run.workflow_run_id)
    assert [item.process_id for item in lost] == [process.process_id]
    assert loaded_process is not None
    assert loaded_process.status == "LOST"
    assert loaded_run is not None
    assert loaded_run.status == "ABORTED"
    assert loaded_run.error["reason"] == "WORKFLOW_PROCESS_LOST"


def test_supervisor_abnormal_exit_aborts_run_and_running_nodes(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    run = create_run(store)
    process = store.claim_workflow_process(workflow_run_id=run.workflow_run_id)
    assert process is not None
    store.record_workflow_process_heartbeat(
        process.process_id,
        process_generation=process.process_generation,
    )
    assert store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        owner_process_id=process.process_id,
        process_generation=process.process_generation,
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source",
        node_type="core.source",
        status=NodeRunStatus.RUNNING,
        owner_process_id=process.process_id,
        process_generation=process.process_generation,
    )
    supervisor = Supervisor(
        config=EngineConfig(
            data_dir=tmp_path / "runtime",
            enforce_single_instance=False,
        ),
        runtime_store=store,
    )
    child = subprocess.Popen(
        [sys.executable, "-c", "raise SystemExit(7)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    supervisor._children[process.process_id] = child

    try:
        deadline = time.monotonic() + 5
        swept = []
        while time.monotonic() < deadline:
            swept = supervisor.sweep_exited_children()
            if swept:
                break
            time.sleep(0.05)
    finally:
        if child.poll() is None:
            child.terminate()

    loaded_process = store.get_workflow_process(process.process_id)
    loaded_run = store.get_workflow_run(run.workflow_run_id)
    loaded_node = store.get_node_run(node.node_run_id)
    assert [item.process_id for item in swept] == [process.process_id]
    assert loaded_process is not None
    assert loaded_process.status == "FAILED"
    assert loaded_process.exit_code == 7
    assert loaded_run is not None
    assert loaded_run.status == "ABORTED"
    assert loaded_node is not None
    assert loaded_node.status == "CANCELLED"
    assert loaded_node.error["reason"] == "WORKFLOW_PROCESS_EXITED_ABNORMALLY"


def test_supervisor_sweeps_exited_executor_and_records_event(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    supervisor = Supervisor(
        config=EngineConfig(
            data_dir=tmp_path / "runtime",
            enforce_single_instance=False,
            supervisor_maintenance_interval_seconds=60,
        ),
        runtime_store=store,
        python_executable=sys.executable,
    )

    executor_id = supervisor.start_executor_process(executor_id="executor-1")
    child = supervisor._executor_children[executor_id]
    assert child.stdin is not None
    child.stdin.close()

    try:
        deadline = time.monotonic() + 5
        while (
            time.monotonic() < deadline
            and executor_id in supervisor._executor_children
        ):
            supervisor.sweep_exited_executors()
            time.sleep(0.05)
    finally:
        supervisor.close()

    events = [
        event
        for event in store.list_runtime_events()
        if event.event_type == "EXECUTOR_EXITED"
    ]
    stdout_log = (
        tmp_path
        / "runtime"
        / "logs"
        / "executors"
        / f"{executor_id}.stdout.log"
    )
    stderr_log = stdout_log.with_name(f"{executor_id}.stderr.log")

    assert executor_id not in supervisor._executor_children
    assert len(events) == 1
    assert events[0].payload["executor_id"] == executor_id
    assert events[0].payload["exit_code"] == 0
    assert events[0].payload["abnormal"] is False
    assert stdout_log.exists()
    assert stderr_log.exists()


def test_supervisor_passes_workflow_process_execution_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = make_store(tmp_path)
    run = create_run(store, definition=non_empty_definition())
    captured_command: list[str] = []

    class FakeProcess:
        pid = 12345
        returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.returncode = -15

        def wait(self, timeout: float | None = None) -> int:
            if self.returncode is None:
                self.returncode = 0
            return self.returncode

    def fake_popen(command: list[str], **_kwargs: object) -> FakeProcess:
        captured_command.extend(command)
        return FakeProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    supervisor = Supervisor(
        config=EngineConfig(
            data_dir=tmp_path / "runtime",
            enforce_single_instance=False,
            workflow_process_execution_mode="threaded",
            workflow_process_max_concurrent_node_tasks=2,
        ),
        runtime_store=store,
        python_executable=sys.executable,
    )

    process_id = supervisor.start_workflow_process(run.workflow_run_id)

    try:
        assert supervisor._children[process_id].pid == 12345
        assert captured_command[
            captured_command.index("--execution-mode") + 1
        ] == "threaded"
        assert captured_command[
            captured_command.index("--max-concurrent-node-tasks") + 1
        ] == "2"
    finally:
        supervisor.close()
