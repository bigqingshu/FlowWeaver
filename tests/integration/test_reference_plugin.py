from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path
from threading import Thread

from alembic import command
from alembic.config import Config

from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.builtin_table_node_types import (
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
)
from flowweaver.nodes.default_registry import create_default_node_registry
from flowweaver.plugin_runtime.discovery import discover_plugins
from flowweaver.plugin_runtime.executor import PluginExternalProcessExecutor
from flowweaver.protocols.enums import (
    IPCMessageType,
    NodeResultStatus,
    TableRole,
)
from flowweaver.protocols.ipc_messages import IPCEnvelope
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
)
from flowweaver.protocols.table_ref import FieldSchemaModel
from flowweaver.workflow_process.main import run_workflow_process

REFERENCE_NODE_TYPE = "plugin.flowweaver.table_projection"
REFERENCE_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "plugins"
    / "table_projection"
)


def test_reference_plugin_runs_table_workflow_and_keeps_core_baseline(
    tmp_path: Path,
) -> None:
    plugin_root = _copy_reference_plugin(tmp_path)
    catalog = discover_plugins(plugin_root)
    entries = catalog.list_entries()

    assert len(entries) == 1
    assert entries[0].enabled is True
    assert len(create_default_node_registry().list_definitions()) == 41
    combined_registry = create_default_node_registry(catalog)
    assert len(combined_registry.list_definitions()) == 42
    plugin_definition = combined_registry.get(REFERENCE_NODE_TYPE, "1.0")
    assert plugin_definition is not None
    assert plugin_definition.provider_type == "user_plugin"

    runtime_dir = tmp_path / "runtime" / "workflow_runs"
    store = _make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Reference plugin workflow",
        workflow_id="workflow-reference-plugin",
        definition=_workflow_definition(),
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-reference-plugin",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-reference-plugin",
    )
    assert process is not None

    try:
        exit_code = run_workflow_process(
            store=store,
            workflow_run_id=run.workflow_run_id,
            process_id=process.process_id,
            process_generation=process.process_generation,
            heartbeat_interval_seconds=0,
            runtime_dir=runtime_dir,
            plugin_dir=plugin_root,
        )
        node_runs = {
            node_run.node_instance_id: node_run
            for node_run in store.list_node_runs(run.workflow_run_id)
        }
        plugin_result = store.get_latest_succeeded_node_task_result_for_node_run(
            node_runs["plugin"].node_run_id
        )
        filter_result = store.get_latest_succeeded_node_task_result_for_node_run(
            node_runs["filter"].node_run_id
        )
        assert plugin_result is not None
        assert filter_result is not None
        plugin_ref = store.get_table_ref(plugin_result.output_refs[0])
        filter_ref = store.get_table_ref(filter_result.output_refs[0])
        assert plugin_ref is not None
        assert filter_ref is not None
        provider = SQLiteRuntimeTableProvider(runtime_dir)
        plugin_rows = provider.read_rows(plugin_ref, 0, 10)
        filter_rows = provider.read_rows(filter_ref, 0, 10)
        events = store.list_runtime_events()
    finally:
        store.dispose()

    assert exit_code == 0
    assert node_runs["plugin"].status == "SUCCEEDED"
    assert node_runs["plugin"].last_heartbeat is not None
    assert plugin_result.executor_id == "plugin-external-process-executor"
    assert plugin_result.output_slot_bindings == {
        "out": plugin_result.output_refs[0]
    }
    assert plugin_result.summary == {
        "selected_columns": ["row_id", "amount"],
        "rename_first_to": "projected_id",
        "copied_rows": 4,
    }
    assert [row["projected_id"] for row in plugin_rows] == [1, 2, 3, 4]
    assert [row["amount"] for row in filter_rows] == [3.0, 4.0]
    assert any(
        event.event_type == "NODE_LOG"
        and event.payload.get("message") == "Projection completed"
        for event in events
    )
    assert any(
        event.event_type == "NODE_PROGRESS"
        and event.payload.get("current_stage") == "completed"
        for event in events
    )
    assert not (runtime_dir / "_plugin_staging").exists()


def test_reference_plugin_applies_runtime_options_and_cancels(
    tmp_path: Path,
) -> None:
    plugin_root = _copy_reference_plugin(tmp_path)
    runtime_dir = tmp_path / "runtime" / "workflow_runs"
    store = _make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(runtime_dir)
    input_ref = _create_runtime_input(
        store=store,
        provider=provider,
        workflow_run_id="run-reference-control",
        row_count=20_000,
    )
    task = NodeTaskModel(
        task_id="task-reference-control",
        workflow_run_id="run-reference-control",
        workflow_process_id="process-reference-control",
        process_generation=1,
        node_run_id="node-run-reference-control",
        node_instance_id="plugin",
        node_type=REFERENCE_NODE_TYPE,
        node_version="1.0",
        attempt=1,
        input_refs=[input_ref.table_ref_id],
        input_slot_bindings={"in": input_ref.table_ref_id},
        config={
            "enable_execute": True,
            "selected_columns": ["row_id"],
            "rename_first_to": "projected_id",
            "batch_size": 1,
        },
        runtime_feedback_policy=_feedback_policy(
            log_level="DEBUG",
            progress_enabled=True,
        ),
        runtime_options_version=0,
        timeout_seconds=30,
    )
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
        store=store,
        runtime_dir=runtime_dir,
    )
    events: list[IPCEnvelope] = []
    results = []
    executor.set_event_handler(lambda _task, envelope: events.append(envelope))
    worker = Thread(target=lambda: results.append(executor.execute(task)))
    worker.start()
    try:
        assert _wait_until(
            lambda: _has_event(events, IPCMessageType.NODE_TASK_HEARTBEAT)
        )
        assert executor.request_runtime_options_update(
            task,
            runtime_options_version=1,
            runtime_feedback_policy=_feedback_policy(
                log_level="WARN",
                progress_enabled=False,
            ),
        )
        assert _wait_until(
            lambda: _has_event(
                events,
                IPCMessageType.NODE_TASK_RUNTIME_OPTIONS_APPLIED,
            )
        )
        assert _wait_until(
            lambda: any(
                event.message_type == IPCMessageType.NODE_TASK_LOG
                and event.payload.get("message") == "Runtime options applied"
                for event in events
            )
        )
        assert executor.request_cancel(task)
        worker.join(timeout=10)
    finally:
        if worker.is_alive():
            executor.close()
            worker.join(timeout=5)
        executor.close()
        plugin_refs = store.list_table_refs_by_node_run(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
        )
        store.dispose()

    assert not worker.is_alive()
    assert len(results) == 1
    assert results[0].status == NodeResultStatus.CANCELLED
    assert results[0].output_refs == []
    assert plugin_refs == []
    assert not (runtime_dir / "_plugin_staging").exists()


def _copy_reference_plugin(tmp_path: Path) -> Path:
    plugin_root = tmp_path / "plugins"
    shutil.copytree(REFERENCE_FIXTURE, plugin_root / "table_projection")
    return plugin_root


def _workflow_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "generate",
                "node_type": GENERATE_TEST_TABLE_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "rows": 4,
                    "columns": ["row_id", "amount"],
                    "seed": 0,
                },
            },
            {
                "node_instance_id": "plugin",
                "node_type": REFERENCE_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "enable_execute": True,
                    "selected_columns": ["row_id", "amount"],
                    "rename_first_to": "projected_id",
                    "batch_size": 2,
                    "input_sources": {
                        "in": {
                            "type": "upstream_table",
                            "source_node_instance_id": "generate",
                            "output_slot": "out",
                        }
                    },
                },
            },
            {
                "node_instance_id": "filter",
                "node_type": FILTER_ROWS_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "field": "amount",
                    "operator": "GT",
                    "value": 2.5,
                    "input_sources": {
                        "in": {
                            "type": "upstream_table",
                            "source_node_instance_id": "plugin",
                            "output_slot": "out",
                        }
                    },
                },
            },
        ],
        "connections": [
            {
                "connection_id": "generate-plugin",
                "source_node_id": "generate",
                "source_port": "out",
                "target_node_id": "plugin",
                "target_port": "in",
            },
            {
                "connection_id": "plugin-filter",
                "source_node_id": "plugin",
                "source_port": "out",
                "target_node_id": "filter",
                "target_port": "in",
            },
        ],
    }


def _create_runtime_input(
    *,
    store: RuntimeStore,
    provider: SQLiteRuntimeTableProvider,
    workflow_run_id: str,
    row_count: int,
):
    staging_ref = provider.create_staging_table(
        workflow_run_id=workflow_run_id,
        node_run_id="source-node",
        output_name="source",
        schema=_schema(),
        role=TableRole.CURRENT,
    )
    provider.insert_rows(
        staging_ref,
        [
            {"row_id": index, "amount": float(index)}
            for index in range(1, row_count + 1)
        ],
    )
    published_ref = provider.published_ref_from_staging(staging_ref)
    provider.publish_staging(staging_ref, published_ref)
    store.register_table_ref(published_ref)
    provider.drop_table(staging_ref)
    return published_ref


def _schema() -> list[FieldSchemaModel]:
    return [
        FieldSchemaModel(
            field_id="row_id",
            name="row_id",
            data_type="INTEGER",
            nullable=False,
            ordinal=0,
        ),
        FieldSchemaModel(
            field_id="amount",
            name="amount",
            data_type="FLOAT",
            nullable=False,
            ordinal=1,
        ),
    ]


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


def _has_event(events: list[IPCEnvelope], message_type: IPCMessageType) -> bool:
    return any(event.message_type == message_type for event in events)


def _wait_until(predicate, *, timeout_seconds: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def _make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")
    return RuntimeStore.from_sqlite_path(database_path)
