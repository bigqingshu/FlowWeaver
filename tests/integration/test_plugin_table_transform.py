from __future__ import annotations

import json
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from alembic import command
from alembic.config import Config

from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.engine.table_provider_registry import (
    TableProviderRegistry,
)
from flowweaver.nodes.builtin_table_node_types import (
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
)
from flowweaver.plugin_runtime.discovery import discover_plugins
from flowweaver.plugin_runtime.executor import PluginExternalProcessExecutor
from flowweaver.protocols.enums import (
    NodeResultStatus,
    TableRole,
    TableStorageKind,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel
from flowweaver.workflow_process.main import run_workflow_process


def test_plugin_table_output_is_available_to_downstream_node(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_table_plugin(plugin_root, mode="success")
    runtime_dir = tmp_path / "runtime" / "workflow_runs"
    store = _make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Plugin table workflow",
        workflow_id="workflow-plugin-table",
        definition=_workflow_definition(multiplier=10),
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-plugin-table",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-plugin-table",
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
    finally:
        store.dispose()

    assert exit_code == 0
    assert plugin_result.output_slot_bindings == {
        "out": plugin_result.output_refs[0]
    }
    assert plugin_result.plugin_runtime is None
    assert plugin_result.summary["config"] == {"multiplier": 10}
    assert [row["amount"] for row in plugin_rows] == [10.0, 20.0, 30.0, 40.0]
    assert [row["amount"] for row in filter_rows] == [30.0, 40.0]
    submit_payload = (package / "last-submit.json").read_text(encoding="utf-8")
    assert all(
        forbidden not in submit_payload
        for forbidden in ('"rows"', '"records"', '"base64"', '"bytes"')
    )
    submitted_task = json.loads(submit_payload)
    assert submitted_task["config"] == {"multiplier": 10}
    assert submitted_task["plugin_runtime"]["inputs"][0]["materialized"] is False
    assert not (runtime_dir / "_plugin_staging").exists()


def test_memory_input_is_materialized_in_fixed_batches(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_table_plugin(plugin_root, mode="success")
    runtime_dir = tmp_path / "runtime" / "workflow_runs"
    store = _make_store(tmp_path)
    runtime_provider = SQLiteRuntimeTableProvider(runtime_dir)
    memory_provider = _TrackingMemoryTableProvider()
    provider_registry = TableProviderRegistry()
    provider_registry.register(
        runtime_provider,
        storage_kinds=(TableStorageKind.RUNTIME_SQL,),
    )
    provider_registry.register(
        memory_provider,
        storage_kinds=(TableStorageKind.MEMORY,),
    )
    schema = _schema()
    input_ref = memory_provider.create_memory_table(
        workflow_run_id="run-memory-plugin",
        node_run_id="source-node",
        logical_table_id="source",
        schema=schema,
        rows=[
            {"row_id": index, "amount": float(index)}
            for index in range(1, 2502)
        ],
        role=TableRole.CURRENT,
    )
    store.register_table_ref(input_ref)
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
        store=store,
        runtime_dir=runtime_dir,
        table_provider_registry=provider_registry,
    )

    try:
        result = executor.execute(
            _task(
                workflow_run_id="run-memory-plugin",
                input_ref_id=input_ref.table_ref_id,
                config={"enable_execute": True, "multiplier": 2},
            )
        )
        output_ref = store.get_table_ref(result.output_refs[0])
        assert output_ref is not None
        output_count = runtime_provider.count_rows(output_ref)
    finally:
        executor.close()
        memory_provider.drop_table(input_ref)
        store.dispose()

    assert result.status == NodeResultStatus.SUCCEEDED
    assert output_count == 2501
    batch_reads = [
        call for call in memory_provider.read_calls if call[1] == 1000
    ]
    assert [offset for offset, _limit in batch_reads] == [0, 1000, 2000]
    submit_payload = (package / "last-submit.json").read_text(encoding="utf-8")
    assert len(submit_payload) < 20_000
    assert '"rows"' not in submit_payload
    submitted_task = json.loads(submit_payload)
    assert submitted_task["plugin_runtime"]["inputs"][0]["materialized"] is True


def test_missing_required_input_does_not_start_plugin(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_table_plugin(plugin_root, mode="success")
    store = _make_store(tmp_path)
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
        store=store,
        runtime_dir=tmp_path / "runtime" / "workflow_runs",
    )

    try:
        result = executor.execute(
            _task(
                workflow_run_id="run-missing-input",
                input_ref_id=None,
                config={"enable_execute": True, "multiplier": 2},
            )
        )
    finally:
        executor.close()
        store.dispose()

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["error_code"] == "PLUGIN_INPUT_SLOT_MISSING"
    assert not (package / "runner.started").exists()


def test_unknown_input_ref_does_not_start_plugin(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    package = _write_table_plugin(plugin_root, mode="success")
    store = _make_store(tmp_path)
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
        store=store,
        runtime_dir=tmp_path / "runtime" / "workflow_runs",
    )

    try:
        result = executor.execute(
            _task(
                workflow_run_id="run-unknown-input",
                input_ref_id="missing-table-ref",
                config={"enable_execute": True, "multiplier": 2},
            )
        )
    finally:
        executor.close()
        store.dispose()

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["error_code"] == "PLUGIN_INPUT_REF_NOT_FOUND"
    assert not (package / "runner.started").exists()


@pytest.mark.parametrize(
    ("mode", "error_code"),
    [
        ("missing_output", "PLUGIN_OUTPUT_SLOT_MISSING"),
        ("duplicate_output", "PLUGIN_OUTPUT_SLOT_DUPLICATE"),
        ("undeclared_output", "PLUGIN_OUTPUT_SLOT_UNDECLARED"),
        ("path_escape", "PLUGIN_OUTPUT_PATH_OUTSIDE_STAGING"),
        ("plugin_failure", "PLUGIN_FORCED_FAILURE"),
    ],
)
def test_invalid_plugin_outputs_are_not_published(
    tmp_path: Path,
    mode: str,
    error_code: str,
) -> None:
    plugin_root = tmp_path / "plugins"
    _write_table_plugin(plugin_root, mode=mode)
    runtime_dir = tmp_path / "runtime" / "workflow_runs"
    store = _make_store(tmp_path)
    runtime_provider = SQLiteRuntimeTableProvider(runtime_dir)
    input_ref = _create_runtime_input(
        store=store,
        provider=runtime_provider,
        workflow_run_id=f"run-{mode}",
    )
    executor = PluginExternalProcessExecutor(
        plugin_catalog=discover_plugins(plugin_root),
        python_executable=sys.executable,
        store=store,
        runtime_dir=runtime_dir,
    )

    try:
        result = executor.execute(
            _task(
                workflow_run_id=f"run-{mode}",
                input_ref_id=input_ref.table_ref_id,
                config={"enable_execute": True, "multiplier": 2},
            )
        )
        plugin_refs = store.list_table_refs_by_node_run(
            workflow_run_id=f"run-{mode}",
            node_run_id="node-run-plugin",
        )
    finally:
        executor.close()
        store.dispose()

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert result.error["error_code"] == error_code
    assert plugin_refs == []
    assert not (runtime_dir / "_plugin_staging").exists()


class _TrackingMemoryTableProvider(MemoryTableProvider):
    def __init__(self) -> None:
        super().__init__()
        self.read_calls: list[tuple[int, int]] = []

    def read_rows(self, table_ref, offset, limit, **kwargs):
        self.read_calls.append((offset, limit))
        return super().read_rows(table_ref, offset, limit, **kwargs)


def _task(
    *,
    workflow_run_id: str,
    input_ref_id: str | None,
    config: dict,
) -> NodeTaskModel:
    return NodeTaskModel(
        task_id="task-plugin-table",
        workflow_run_id=workflow_run_id,
        workflow_process_id="process-plugin-table",
        process_generation=1,
        node_run_id="node-run-plugin",
        node_instance_id="plugin",
        node_type="plugin.example.table_transform",
        node_version="1.0",
        attempt=1,
        input_refs=[] if input_ref_id is None else [input_ref_id],
        input_slot_bindings=(
            {} if input_ref_id is None else {"in": input_ref_id}
        ),
        config=config,
        timeout_seconds=60,
    )


def _workflow_definition(*, multiplier: int) -> dict:
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
                "node_type": "plugin.example.table_transform",
                "node_version": "1.0",
                "config": {
                    "enable_execute": True,
                    "multiplier": multiplier,
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
                    "value": 25.0,
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
):
    staging_ref = provider.create_staging_table(
        workflow_run_id=workflow_run_id,
        node_run_id="source-node",
        output_name="source",
        schema=_schema(),
    )
    provider.insert_rows(
        staging_ref,
        [
            {"row_id": 1, "amount": 2.0},
            {"row_id": 2, "amount": 3.0},
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


def _make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")
    return RuntimeStore.from_sqlite_path(database_path)


def _write_table_plugin(plugin_root: Path, *, mode: str) -> Path:
    package = plugin_root / "table_transform"
    package.mkdir(parents=True)
    (package / "runner.py").write_text(
        _runner_source(mode),
        encoding="utf-8",
    )
    manifest = {
        "manifest_version": "1",
        "plugin_id": "example.table_transform",
        "plugin_version": "1.0.0",
        "node_type": "plugin.example.table_transform",
        "node_version": "1.0",
        "display_name": "Table Transform",
        "category": "test",
        "config_schema": {
            "type": "object",
            "properties": {
                "multiplier": {
                    "type": "integer",
                    "required": True,
                    "minimum": 1,
                }
            },
        },
        "input_ports": [{"name": "in", "required": True}],
        "output_ports": [{"name": "out", "required": True}],
        "input_table_slots": [{"name": "in", "required": True}],
        "output_table_slots": [
            {"name": "out", "allow_new_runtime_sql": True}
        ],
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


def _runner_source(mode: str) -> str:
    return dedent(
        f'''
        import argparse
        import json
        import os
        import sqlite3
        import sys
        from pathlib import Path

        MODE = {mode!r}
        parser = argparse.ArgumentParser()
        parser.add_argument("--executor-id", required=True)
        args = parser.parse_args()
        Path("runner.started").write_text(str(os.getpid()), encoding="utf-8")

        def emit(message_type, payload):
            message = {{"message_type": message_type, "payload": payload}}
            print(json.dumps(message), flush=True)

        def quote(value):
            return '"' + value.replace('"', '""') + '"'

        def create_output(target, schema, rows):
            database_path = target["database_path"]
            if MODE == "path_escape":
                database_path = str(Path("escape.db").resolve())
            connection = sqlite3.connect(database_path)
            try:
                columns = ", ".join(
                    f"{{quote(field['name'])}} {{field['data_type']}}"
                    for field in schema
                )
                connection.execute(
                    f"DROP TABLE IF EXISTS {{quote(target['table_name'])}}"
                )
                connection.execute(
                    f"CREATE TABLE {{quote(target['table_name'])}} ({{columns}})"
                )
                names = [field["name"] for field in schema]
                placeholders = ", ".join("?" for _ in names)
                insert_sql = (
                    f"INSERT INTO {{quote(target['table_name'])}} "
                    f"VALUES ({{placeholders}})"
                )
                connection.executemany(
                    insert_sql,
                    [[row.get(name) for name in names] for row in rows],
                )
                connection.commit()
            finally:
                connection.close()
            return database_path

        emit("EXECUTOR_READY", {{"executor_id": args.executor_id}})
        for line in sys.stdin:
            message = json.loads(line)
            if message.get("message_type") != "NODE_TASK_SUBMIT":
                continue
            task = message["payload"]
            Path("last-submit.json").write_text(
                json.dumps(task),
                encoding="utf-8",
            )
            runtime = task["plugin_runtime"]
            input_ref = runtime["inputs"][0]
            output_target = runtime["output_targets"][0]
            connection = sqlite3.connect(input_ref["database_uri"], uri=True)
            connection.row_factory = sqlite3.Row
            try:
                rows = [
                    dict(row)
                    for row in connection.execute(
                        f"SELECT * FROM {{quote(input_ref['table_name'])}}"
                    )
                ]
            finally:
                connection.close()
            multiplier = task["config"]["multiplier"]
            for row in rows:
                row["amount"] = row["amount"] * multiplier
            schema = input_ref["schema"]
            database_path = create_output(output_target, schema, rows)
            output = {{
                "slot_name": "out",
                "database_path": database_path,
                "table_name": output_target["table_name"],
                "schema": schema,
            }}
            if MODE == "missing_output":
                outputs = []
            elif MODE == "duplicate_output":
                outputs = [output, output]
            elif MODE == "undeclared_output":
                output["slot_name"] = "other"
                outputs = [output]
            else:
                outputs = [output]
            result = {{
                "task_id": task["task_id"],
                "node_run_id": task["node_run_id"],
                "attempt": task["attempt"],
                "executor_id": args.executor_id,
                "process_generation": task["process_generation"],
                "status": (
                    "FAILED" if MODE == "plugin_failure" else "SUCCEEDED"
                ),
                "summary": {{"config": task["config"]}},
                "plugin_runtime": {{
                    "protocol_version": "1",
                    "outputs": outputs,
                }},
            }}
            if MODE == "plugin_failure":
                result["error"] = {{
                    "error_code": "PLUGIN_FORCED_FAILURE",
                    "message": "forced plugin failure",
                }}
                emit(
                    "NODE_TASK_FAILED",
                    {{"result": result, "error_type": "PluginFailure"}},
                )
            else:
                emit("NODE_TASK_COMPLETED", {{"result": result}})
        '''
    )
