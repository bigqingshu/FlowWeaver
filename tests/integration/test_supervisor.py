from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.common.config import EngineConfig
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.supervisor import Supervisor
from flowweaver.protocols.enums import WorkflowRunStatus


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    return RuntimeStore.from_sqlite_path(database_path)


def create_run(store: RuntimeStore):
    workflow = store.create_workflow_definition(
        name="Supervisor workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
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
