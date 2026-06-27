from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.engine.runtime_event_sink import IPCEventSink
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.ipc_messages import IPCEnvelope
from flowweaver.workflow_process.main import run_workflow_process


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    return RuntimeStore.from_sqlite_path(database_path)


def definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "source",
                "node_type": "core.source",
                "node_version": "1.0",
            },
            {
                "node_instance_id": "transform",
                "node_type": "core.transform",
                "node_version": "1.0",
            },
        ],
        "connections": [
            {
                "connection_id": "c1",
                "source_node_id": "source",
                "source_port": "out",
                "target_node_id": "transform",
                "target_port": "in",
            }
        ],
    }


def empty_definition() -> dict:
    return {"schema_version": "1.0", "nodes": [], "connections": []}


def test_workflow_process_executes_ready_nodes_with_fake_executor(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Fake executor workflow",
        definition=definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
    )

    loaded_process = store.get_workflow_process(process.process_id)
    node_runs = store.list_node_runs(run.workflow_run_id)
    assert exit_code == 0
    assert loaded_process is not None
    assert loaded_process.status == "RUNNING"
    assert loaded_process.exit_code is None
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert {node.node_instance_id: node.status for node in node_runs} == {
        "source": "SUCCEEDED",
        "transform": "SUCCEEDED",
    }
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]


def test_workflow_process_ipc_event_sink_does_not_write_runtime_events(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="IPC event workflow",
        definition=empty_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    assert process is not None
    event_path = tmp_path / "runtime-events.jsonl"

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        event_sink=IPCEventSink(event_path),
    )

    envelopes = [
        IPCEnvelope.model_validate_json(line)
        for line in event_path.read_text(encoding="utf-8").splitlines()
    ]
    assert exit_code == 0
    assert store.list_runtime_events() == []
    assert [envelope.message_type for envelope in envelopes] == [
        IPCMessageType.RUNTIME_EVENT,
        IPCMessageType.RUNTIME_EVENT,
    ]
    assert [envelope.payload["event_type"] for envelope in envelopes] == [
        "WORKFLOW_STARTED",
        "WORKFLOW_FINISHED",
    ]
