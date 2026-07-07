from __future__ import annotations

import json
from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.engine.memory_table_provider import (
    MEMORY_PROVIDER_ID,
    MemoryTableProvider,
)
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.node_executor import BuiltinTableNodeExecutor
from flowweaver.nodes.builtin_table import (
    ADD_COLUMNS_NODE_TYPE,
    ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
    ADVANCED_FILTER_ROWS_NODE_TYPE,
    BATCH_RENAME_FILES_NODE_TYPE,
    CONDITION_FLAG_NODE_TYPE,
    COPY_COLUMN_NODE_TYPE,
    COPY_ROWS_NODE_TYPE,
    DEDUPLICATE_ROWS_NODE_TYPE,
    DELETE_COLUMNS_NODE_TYPE,
    DELETE_ROWS_NODE_TYPE,
    EXTRACT_TEXT_NODE_TYPE,
    FILL_CELLS_NODE_TYPE,
    FILL_RANGE_NODE_TYPE,
    FILL_SEQUENCE_NODE_TYPE,
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
    LIST_FILES_NODE_TYPE,
    LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
    MERGE_COLUMNS_NODE_TYPE,
    NUMERIC_COLUMN_OPERATION_NODE_TYPE,
    PARSE_DATETIME_NODE_TYPE,
    PLUGIN_NODE_TYPE,
    RENAME_COLUMNS_NODE_TYPE,
    REORDER_COLUMNS_NODE_TYPE,
    REPLACE_TEXT_NODE_TYPE,
    SAVE_MEMORY_TABLE_NODE_TYPE,
    SAVE_RUN_TABLE_NODE_TYPE,
    UNPIVOT_ROWS_NODE_TYPE,
    WRITE_BACK_TABLE_NODE_TYPE,
    WRITE_SELECTED_COLUMNS_NODE_TYPE,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    NodeResultStatus,
    TableRole,
    TableStorageKind,
)
from flowweaver.protocols.node_task import NodeTaskModel


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    return RuntimeStore.from_sqlite_path(database_path)


def make_executor(tmp_path: Path) -> tuple[
    BuiltinTableNodeExecutor,
    RuntimeStore,
    RuntimeDataRegistry,
    SQLiteRuntimeTableProvider,
]:
    executor, store, registry, provider, _memory_provider = (
        make_executor_with_memory_provider(tmp_path)
    )
    return executor, store, registry, provider


def make_executor_with_memory_provider(tmp_path: Path) -> tuple[
    BuiltinTableNodeExecutor,
    RuntimeStore,
    RuntimeDataRegistry,
    SQLiteRuntimeTableProvider,
    MemoryTableProvider,
]:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    memory_provider = MemoryTableProvider(tables={})
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    executor = BuiltinTableNodeExecutor(
        executor_id="builtin-executor-1",
        store=store,
        registry=registry,
        table_provider=provider,
        memory_provider=memory_provider,
    )
    return executor, store, registry, provider, memory_provider


def make_task(
    *,
    node_type: str,
    node_run_id: str,
    node_instance_id: str,
    config: dict,
    input_refs: list[str] | None = None,
) -> NodeTaskModel:
    return NodeTaskModel(
        workflow_run_id="run-1",
        workflow_process_id="process-1",
        process_generation=1,
        node_run_id=node_run_id,
        node_instance_id=node_instance_id,
        node_type=node_type,
        node_version="1.0",
        attempt=1,
        input_refs=input_refs or [],
        config=config,
        timeout_seconds=60,
    )


def publish_runtime_rows(
    *,
    registry,
    provider,
    schema,
    rows: list[dict],
    output_name: str,
):
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id=f"node-run-{output_name}",
        output_name=output_name,
        schema=schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    return registry.publish(staged_ref.table_ref_id)


def read_single_output_row(*, registry, provider, result):
    output_ref = registry.get(result.output_refs[0])
    rows = provider.read_rows(output_ref, offset=0, limit=10)
    assert len(rows) == 1
    return output_ref, rows[0]


def test_generate_test_table_node_publishes_runtime_sql_table_ref(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    task = make_task(
        node_type=GENERATE_TEST_TABLE_NODE_TYPE,
        node_run_id="node-run-generate",
        node_instance_id="generate",
        config={
            "rows": 4,
            "columns": [
                {"name": "row_id", "data_type": "INTEGER"},
                {"name": "amount", "data_type": "FLOAT"},
                {"name": "label", "data_type": "TEXT"},
            ],
            "seed": 7,
        },
    )

    result = executor.execute(task)

    assert result.status == NodeResultStatus.SUCCEEDED
    assert result.executor_id == "builtin-executor-1"
    assert len(result.output_refs) == 1
    published = registry.get(result.output_refs[0])
    assert result.summary == {
        "output_ref_count": 1,
        "outputs": [
            {
                "table_ref_id": published.table_ref_id,
                "logical_table_id": "generate_output",
                "role": TableRole.CURRENT.value,
                "storage_kind": TableStorageKind.RUNTIME_SQL.value,
            }
        ],
    }
    assert published.lifecycle_status == LifecycleStatus.PUBLISHED
    assert published.logical_table_id == "generate_output"
    assert provider.count_rows(published) == 4
    assert provider.read_rows(published, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 1.0, "label": "label_7_1"},
        {"row_id": 2, "amount": 2.0, "label": "label_7_2"},
        {"row_id": 3, "amount": 3.0, "label": "label_7_3"},
        {"row_id": 4, "amount": 4.0, "label": "label_7_4"},
    ]


def test_list_files_node_publishes_filtered_file_metadata_table(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    source_dir = tmp_path / "files"
    source_dir.mkdir()
    (source_dir / "a.txt").write_text("alpha", encoding="utf-8")
    (source_dir / "b.csv").write_text("beta", encoding="utf-8")
    (source_dir / ".hidden.txt").write_text("hidden", encoding="utf-8")
    nested_dir = source_dir / "nested"
    nested_dir.mkdir()
    (nested_dir / "c.txt").write_text("charlie", encoding="utf-8")
    task = make_task(
        node_type=LIST_FILES_NODE_TYPE,
        node_run_id="node-run-list-files",
        node_instance_id="list_files",
        config={
            "directory": str(source_dir),
            "recursive": True,
            "include_files": True,
            "include_dirs": False,
            "include_hidden": False,
            "extensions": ["txt"],
            "max_files": 10,
        },
    )

    result = executor.execute(task)

    assert result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(result.output_refs[0])
    assert output_ref.logical_table_id == "list_files_output"
    rows = provider.read_rows(
        output_ref,
        offset=0,
        limit=10,
        order_by=["relative_path"],
    )
    assert [
        {
            "name": row["name"],
            "relative_path": row["relative_path"],
            "extension": row["extension"],
            "is_file": row["is_file"],
            "is_dir": row["is_dir"],
            "size_bytes": row["size_bytes"],
        }
        for row in rows
    ] == [
        {
            "name": "a.txt",
            "relative_path": "a.txt",
            "extension": ".txt",
            "is_file": "true",
            "is_dir": "false",
            "size_bytes": 5,
        },
        {
            "name": "c.txt",
            "relative_path": "nested/c.txt",
            "extension": ".txt",
            "is_file": "true",
            "is_dir": "false",
            "size_bytes": 7,
        },
    ]


def test_list_files_node_can_include_directories_and_limit_rows(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    source_dir = tmp_path / "files"
    source_dir.mkdir()
    (source_dir / "a.txt").write_text("alpha", encoding="utf-8")
    (source_dir / "nested").mkdir()
    task = make_task(
        node_type=LIST_FILES_NODE_TYPE,
        node_run_id="node-run-list-files",
        node_instance_id="list_files",
        config={
            "directory": str(source_dir),
            "include_files": True,
            "include_dirs": True,
            "max_files": 1,
        },
    )

    result = executor.execute(task)

    assert result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(result.output_refs[0])
    assert provider.count_rows(output_ref) == 1


def test_batch_rename_files_node_outputs_preview_plan_without_renaming(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    source_dir = tmp_path / "rename"
    source_dir.mkdir()
    source_file = source_dir / "old.txt"
    source_file.write_text("alpha", encoding="utf-8")
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["path", "new_name"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10)
    rows[0] = {"path": str(source_file), "new_name": "renamed"}
    rows[1] = {"path": str(source_dir / "missing.txt"), "new_name": "missing_new"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-rename-input",
        output_name="rename_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    rename_task = make_task(
        node_type=BATCH_RENAME_FILES_NODE_TYPE,
        node_run_id="node-run-batch-rename",
        node_instance_id="batch_rename",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "path_field": "path",
            "new_name_field": "new_name",
            "auto_append_ext": True,
            "actual_rename": False,
        },
    )

    rename_result = executor.execute(rename_task)

    assert rename_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(rename_result.output_refs[0])
    output_rows = provider.read_rows(
        output_ref,
        offset=0,
        limit=10,
        order_by=["source_row_number"],
    )
    assert output_rows == [
        {
            "source_row_number": 1,
            "original_path": str(source_file),
            "new_path": str(source_dir / "renamed.txt"),
            "rename_status": "planned",
            "error_message": "",
            "rename_requested": "false",
            "actual_rename": "false",
            "write_log": "false",
            "log_path": "",
            "skipped_reason": "",
        },
        {
            "source_row_number": 2,
            "original_path": str(source_dir / "missing.txt"),
            "new_path": str(source_dir / "missing_new.txt"),
            "rename_status": "failed",
            "error_message": "source path does not exist",
            "rename_requested": "false",
            "actual_rename": "false",
            "write_log": "false",
            "log_path": "",
            "skipped_reason": "",
        },
    ]
    assert source_file.exists()
    assert not (source_dir / "renamed.txt").exists()


def test_batch_rename_files_node_renames_file_when_enabled(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    source_dir = tmp_path / "rename"
    source_dir.mkdir()
    source_file = source_dir / "old.txt"
    source_file.write_text("alpha", encoding="utf-8")
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["path", "new_name"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10)
    rows[0] = {"path": str(source_file), "new_name": "renamed.txt"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-rename-input",
        output_name="rename_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)

    rename_result = executor.execute(
        make_task(
            node_type=BATCH_RENAME_FILES_NODE_TYPE,
            node_run_id="node-run-batch-rename",
            node_instance_id="batch_rename",
            input_refs=[custom_input_ref.table_ref_id],
            config={
                "path_field": "path",
                "new_name_field": "new_name",
                "actual_rename": True,
            },
        )
    )

    assert rename_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(rename_result.output_refs[0])
    output_rows = provider.read_rows(output_ref, offset=0, limit=10)
    assert output_rows[0]["rename_status"] == "renamed"
    assert output_rows[0]["rename_requested"] == "true"
    assert output_rows[0]["actual_rename"] == "true"
    assert output_rows[0]["skipped_reason"] == ""
    assert not source_file.exists()
    assert (source_dir / "renamed.txt").read_text(encoding="utf-8") == "alpha"


def test_batch_rename_files_node_can_append_number_and_write_log(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    source_dir = tmp_path / "rename"
    source_dir.mkdir()
    source_file = source_dir / "old.txt"
    source_file.write_text("alpha", encoding="utf-8")
    existing_file = source_dir / "renamed.txt"
    existing_file.write_text("existing", encoding="utf-8")
    log_path = tmp_path / "logs" / "rename.jsonl"
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["path", "new_name"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10)
    rows[0] = {"path": str(source_file), "new_name": "renamed.txt"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-rename-input",
        output_name="rename_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)

    rename_result = executor.execute(
        make_task(
            node_type=BATCH_RENAME_FILES_NODE_TYPE,
            node_run_id="node-run-batch-rename",
            node_instance_id="batch_rename",
            input_refs=[custom_input_ref.table_ref_id],
            config={
                "path_field": "path",
                "new_name_field": "new_name",
                "actual_rename": True,
                "conflict_mode": "append_number",
                "write_log": True,
                "log_path": str(log_path),
            },
        )
    )

    assert rename_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(rename_result.output_refs[0])
    output_rows = provider.read_rows(output_ref, offset=0, limit=10)
    renamed_path = source_dir / "renamed_2.txt"
    assert output_rows[0]["rename_status"] == "renamed"
    assert output_rows[0]["new_path"] == str(renamed_path)
    assert output_rows[0]["actual_rename"] == "true"
    assert existing_file.read_text(encoding="utf-8") == "existing"
    assert renamed_path.read_text(encoding="utf-8") == "alpha"
    log_rows = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    assert log_rows == [output_rows[0]]


def test_batch_rename_files_node_skips_existing_target_without_mutating_files(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    source_dir = tmp_path / "rename"
    source_dir.mkdir()
    source_file = source_dir / "old.txt"
    source_file.write_text("alpha", encoding="utf-8")
    target_file = source_dir / "renamed.txt"
    target_file.write_text("existing", encoding="utf-8")
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["path", "new_name"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10)
    rows[0] = {"path": str(source_file), "new_name": "renamed.txt"}
    custom_input_ref = publish_runtime_rows(
        registry=registry,
        provider=provider,
        schema=input_ref.schema,
        rows=rows,
        output_name="rename_skip_input",
    )

    rename_result = executor.execute(
        make_task(
            node_type=BATCH_RENAME_FILES_NODE_TYPE,
            node_run_id="node-run-batch-rename-skip",
            node_instance_id="batch_rename_skip",
            input_refs=[custom_input_ref.table_ref_id],
            config={
                "path_field": "path",
                "new_name_field": "new_name",
                "actual_rename": True,
                "conflict_mode": "skip",
            },
        )
    )

    assert rename_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(rename_result.output_refs[0])
    output_rows = provider.read_rows(output_ref, offset=0, limit=10)
    assert output_rows[0]["rename_status"] == "skipped"
    assert output_rows[0]["rename_requested"] == "true"
    assert output_rows[0]["actual_rename"] == "false"
    assert output_rows[0]["skipped_reason"] == "target path already exists"
    assert source_file.read_text(encoding="utf-8") == "alpha"
    assert target_file.read_text(encoding="utf-8") == "existing"


def test_plugin_node_outputs_status_table_without_executing_plugin(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    plugin_task = make_task(
        node_type=PLUGIN_NODE_TYPE,
        node_run_id="node-run-plugin",
        node_instance_id="plugin",
        config={
            "plugin_id": "example.plugin",
            "plugin_version": "1.2.3",
            "params": {"threshold": 3},
            "input_bindings": {"input": "in"},
            "output_bindings": {"status": "status"},
            "plugin_manifest": {
                "plugin_id": "example.plugin",
                "plugin_version": "1.2.3",
                "execution_modes": ["external_process"],
                "inputs": {"input": {"required": True}},
                "outputs": {"status": {"required": True}},
                "required_params": ["threshold"],
                "has_external_actions": True,
            },
            "execution_mode": "external_process",
            "allow_external_actions": True,
            "enable_execute": True,
        },
    )

    plugin_result = executor.execute(plugin_task)

    assert plugin_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(plugin_result.output_refs[0])
    assert output_ref.logical_table_id == "plugin_output"
    assert provider.read_rows(output_ref, offset=0, limit=10) == [
        {
            "status": "skipped",
            "plugin_id": "example.plugin",
            "plugin_version": "1.2.3",
            "manifest_status": "valid",
            "manifest_plugin_id": "example.plugin",
            "manifest_plugin_version": "1.2.3",
            "execution_mode": "external_process",
            "input_ref_count": 0,
            "param_count": 1,
            "input_binding_count": 1,
            "output_binding_count": 1,
            "plugin_found": "true",
            "validation_status": "valid",
            "validation_errors": "",
            "allow_external_actions": "true",
            "enable_execute": "true",
            "external_actions_declared": "true",
            "execution_ready": "true",
            "actual_execute": "false",
            "skipped_reason": "plugin execution runner is not configured",
        }
    ]


def test_plugin_node_blocks_external_actions_when_not_allowed(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    plugin_task = make_task(
        node_type=PLUGIN_NODE_TYPE,
        node_run_id="node-run-plugin",
        node_instance_id="plugin",
        config={
            "plugin_id": "example.plugin",
            "plugin_version": "1.2.3",
            "params": {"threshold": 3},
            "input_bindings": {"input": "in"},
            "output_bindings": {"status": "status"},
            "plugin_manifest": {
                "plugin_id": "example.plugin",
                "plugin_version": "1.2.3",
                "execution_modes": ["external_process"],
                "inputs": {"input": {"required": True}},
                "outputs": {"status": {"required": True}},
                "required_params": ["threshold"],
                "has_external_actions": True,
            },
            "execution_mode": "external_process",
            "allow_external_actions": False,
            "enable_execute": True,
        },
    )

    plugin_result = executor.execute(plugin_task)

    assert plugin_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(plugin_result.output_refs[0])
    rows = provider.read_rows(output_ref, offset=0, limit=10)
    assert rows[0]["status"] == "blocked"
    assert rows[0]["manifest_status"] == "valid"
    assert rows[0]["validation_status"] == "blocked"
    assert json.loads(rows[0]["validation_errors"]) == [
        "plugin declares external actions but allow_external_actions is false"
    ]
    assert rows[0]["external_actions_declared"] == "true"
    assert rows[0]["execution_ready"] == "false"
    assert rows[0]["actual_execute"] == "false"


def test_plugin_node_allows_missing_manifest_when_execution_disabled(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    plugin_task = make_task(
        node_type=PLUGIN_NODE_TYPE,
        node_run_id="node-run-plugin",
        node_instance_id="plugin",
        config={
            "plugin_id": "example.plugin",
            "params": {"threshold": 3},
            "enable_execute": False,
        },
    )

    plugin_result = executor.execute(plugin_task)

    assert plugin_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(plugin_result.output_refs[0])
    rows = provider.read_rows(output_ref, offset=0, limit=10)
    assert rows[0]["status"] == "skipped"
    assert rows[0]["manifest_status"] == "missing"
    assert rows[0]["validation_status"] == "skipped"
    assert rows[0]["validation_errors"] == ""
    assert rows[0]["execution_ready"] == "false"
    assert rows[0]["skipped_reason"] == "enable_execute is false"


def test_filter_rows_node_publishes_filtered_table_ref_without_mutating_input(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 5,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    filter_task = make_task(
        node_type=FILTER_ROWS_NODE_TYPE,
        node_run_id="node-run-filter",
        node_instance_id="filter",
        input_refs=[input_ref.table_ref_id],
        config={"field": "amount", "operator": "GT", "value": 2.0},
    )

    filter_result = executor.execute(filter_task)

    assert filter_result.status == NodeResultStatus.SUCCEEDED
    assert filter_result.output_refs != generate_result.output_refs
    assert provider.count_rows(input_ref) == 5
    filtered_ref = registry.get(filter_result.output_refs[0])
    assert filtered_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert filtered_ref.logical_table_id == "filter_output"
    assert provider.count_rows(filtered_ref) == 3
    filtered_rows = provider.read_rows(
        filtered_ref,
        offset=0,
        limit=10,
        order_by=["row_id"],
    )
    assert filtered_rows == [
        {"row_id": 3, "amount": 3.0, "label": "label_0_3"},
        {"row_id": 4, "amount": 4.0, "label": "label_0_4"},
        {"row_id": 5, "amount": 5.0, "label": "label_0_5"},
    ]


def test_add_columns_node_publishes_table_with_new_default_column(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    add_task = make_task(
        node_type=ADD_COLUMNS_NODE_TYPE,
        node_run_id="node-run-add-column",
        node_instance_id="add_column",
        input_refs=[input_ref.table_ref_id],
        config={
            "column_name": "status",
            "default_value": "new",
            "data_type": "TEXT",
        },
    )

    add_result = executor.execute(add_task)

    assert add_result.status == NodeResultStatus.SUCCEEDED
    assert add_result.output_refs != generate_result.output_refs
    assert provider.count_rows(input_ref) == 2
    assert [field.name for field in input_ref.schema] == ["row_id", "amount"]
    output_ref = registry.get(add_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "add_column_output"
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "amount",
        "status",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 1.0, "status": "new"},
        {"row_id": 2, "amount": 2.0, "status": "new"},
    ]


def test_delete_columns_node_publishes_table_without_selected_columns(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    delete_task = make_task(
        node_type=DELETE_COLUMNS_NODE_TYPE,
        node_run_id="node-run-delete-columns",
        node_instance_id="delete_columns",
        input_refs=[input_ref.table_ref_id],
        config={"columns": ["amount"]},
    )

    delete_result = executor.execute(delete_task)

    assert delete_result.status == NodeResultStatus.SUCCEEDED
    assert delete_result.output_refs != generate_result.output_refs
    assert [field.name for field in input_ref.schema] == ["row_id", "amount", "label"]
    output_ref = registry.get(delete_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "delete_columns_output"
    assert [field.name for field in output_ref.schema] == ["row_id", "label"]
    assert [field.ordinal for field in output_ref.schema] == [0, 1]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "label": "label_0_1"},
        {"row_id": 2, "label": "label_0_2"},
    ]


def test_copy_column_node_publishes_table_with_new_column(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    copy_task = make_task(
        node_type=COPY_COLUMN_NODE_TYPE,
        node_run_id="node-run-copy-column",
        node_instance_id="copy_column",
        input_refs=[input_ref.table_ref_id],
        config={
            "source_field": "label",
            "output_mode": "new_field",
            "new_field": "label_copy",
        },
    )

    copy_result = executor.execute(copy_task)

    assert copy_result.status == NodeResultStatus.SUCCEEDED
    assert copy_result.output_refs != generate_result.output_refs
    assert [field.name for field in input_ref.schema] == [
        "row_id",
        "amount",
        "label",
    ]
    output_ref = registry.get(copy_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "copy_column_output"
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "amount",
        "label",
        "label_copy",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {
            "row_id": 1,
            "amount": 1.0,
            "label": "label_0_1",
            "label_copy": "label_0_1",
        },
        {
            "row_id": 2,
            "amount": 2.0,
            "label": "label_0_2",
            "label_copy": "label_0_2",
        },
    ]


def test_copy_column_node_overwrites_target_column(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    copy_task = make_task(
        node_type=COPY_COLUMN_NODE_TYPE,
        node_run_id="node-run-copy-column",
        node_instance_id="copy_column",
        input_refs=[input_ref.table_ref_id],
        config={
            "source_field": "row_id",
            "output_mode": "overwrite",
            "target_field": "label",
        },
    )

    copy_result = executor.execute(copy_task)

    assert copy_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(copy_result.output_refs[0])
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "amount",
        "label",
    ]
    assert output_ref.schema[2].data_type == "INTEGER"
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 1.0, "label": 1},
        {"row_id": 2, "amount": 2.0, "label": 2},
    ]


def test_copy_column_node_trims_and_replaces_empty_source_values(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "label", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0]["label"] = "  ready  "
    rows[1]["label"] = "  "
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    copy_task = make_task(
        node_type=COPY_COLUMN_NODE_TYPE,
        node_run_id="node-run-copy-column",
        node_instance_id="copy_column",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "source_field": "label",
            "output_mode": "new_field",
            "new_field": "clean_label",
            "trim_value": True,
            "empty_default": "fallback",
        },
    )

    copy_result = executor.execute(copy_task)

    assert copy_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(copy_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "label": "  ready  ", "clean_label": "ready"},
        {"row_id": 2, "label": "  ", "clean_label": "fallback"},
    ]


def test_reorder_columns_node_appends_unlisted_columns_by_default(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    reorder_task = make_task(
        node_type=REORDER_COLUMNS_NODE_TYPE,
        node_run_id="node-run-reorder-columns",
        node_instance_id="reorder_columns",
        input_refs=[input_ref.table_ref_id],
        config={"order": ["label", "row_id"]},
    )

    reorder_result = executor.execute(reorder_task)

    assert reorder_result.status == NodeResultStatus.SUCCEEDED
    assert reorder_result.output_refs != generate_result.output_refs
    assert [field.name for field in input_ref.schema] == ["row_id", "amount", "label"]
    output_ref = registry.get(reorder_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "reorder_columns_output"
    assert [field.name for field in output_ref.schema] == [
        "label",
        "row_id",
        "amount",
    ]
    assert [field.ordinal for field in output_ref.schema] == [0, 1, 2]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"label": "label_0_1", "row_id": 1, "amount": 1.0},
        {"label": "label_0_2", "row_id": 2, "amount": 2.0},
    ]


def test_reorder_columns_node_can_drop_unlisted_columns(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    reorder_task = make_task(
        node_type=REORDER_COLUMNS_NODE_TYPE,
        node_run_id="node-run-reorder-columns",
        node_instance_id="reorder_columns",
        input_refs=[input_ref.table_ref_id],
        config={
            "order": ["label", "row_id"],
            "unlisted_policy": "drop",
        },
    )

    reorder_result = executor.execute(reorder_task)

    assert reorder_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(reorder_result.output_refs[0])
    assert [field.name for field in output_ref.schema] == ["label", "row_id"]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"label": "label_0_1", "row_id": 1},
        {"label": "label_0_2", "row_id": 2},
    ]


def test_rename_columns_node_applies_mapping_without_mutating_values(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rename_task = make_task(
        node_type=RENAME_COLUMNS_NODE_TYPE,
        node_run_id="node-run-rename-columns",
        node_instance_id="rename_columns",
        input_refs=[input_ref.table_ref_id],
        config={
            "mappings": [
                {"source_field": "amount", "target_field": "total"},
                {"old_name": "label", "new_name": "name"},
            ],
        },
    )

    rename_result = executor.execute(rename_task)

    assert rename_result.status == NodeResultStatus.SUCCEEDED
    assert rename_result.output_refs != generate_result.output_refs
    assert [field.name for field in input_ref.schema] == ["row_id", "amount", "label"]
    output_ref = registry.get(rename_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "rename_columns_output"
    assert [field.name for field in output_ref.schema] == ["row_id", "total", "name"]
    assert [field.ordinal for field in output_ref.schema] == [0, 1, 2]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "total": 1.0, "name": "label_0_1"},
        {"row_id": 2, "total": 2.0, "name": "label_0_2"},
    ]


def test_rename_columns_node_can_prefix_scoped_fields_and_append_duplicate_number(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 1,
                "columns": ["row_id", "amount", "x_amount"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rename_result = executor.execute(
        make_task(
            node_type=RENAME_COLUMNS_NODE_TYPE,
            node_run_id="node-run-rename-columns",
            node_instance_id="rename_columns",
            input_refs=[input_ref.table_ref_id],
            config={
                "mode": "prefix",
                "scope": "fields",
                "scope_fields": ["amount"],
                "prefix": "x_",
                "duplicate_policy": "append_number",
            },
        )
    )

    assert rename_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(rename_result.output_refs[0])
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "x_amount",
        "x_amount_2",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "x_amount": 1.0, "x_amount_2": "x_amount_0_1"},
    ]


def test_fill_cells_node_fills_literal_value_down_from_start_row(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 4,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    fill_task = make_task(
        node_type=FILL_CELLS_NODE_TYPE,
        node_run_id="node-run-fill-cells",
        node_instance_id="fill_cells",
        input_refs=[input_ref.table_ref_id],
        config={
            "target_field": "label",
            "value_source": {"mode": "literal", "value": "filled"},
            "start_row": 2,
            "direction": "down",
            "count": 2,
        },
    )

    fill_result = executor.execute(fill_task)

    assert fill_result.status == NodeResultStatus.SUCCEEDED
    assert fill_result.output_refs != generate_result.output_refs
    output_ref = registry.get(fill_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "fill_cells_output"
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 1.0, "label": "label_0_1"},
        {"row_id": 2, "amount": 2.0, "label": "filled"},
        {"row_id": 3, "amount": 3.0, "label": "filled"},
        {"row_id": 4, "amount": 4.0, "label": "label_0_4"},
    ]


def test_fill_cells_node_uses_same_row_field_value_source(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    fill_task = make_task(
        node_type=FILL_CELLS_NODE_TYPE,
        node_run_id="node-run-fill-cells",
        node_instance_id="fill_cells",
        input_refs=[input_ref.table_ref_id],
        config={
            "target_field": "label",
            "value_source": {"mode": "row_field", "field": "amount"},
        },
    )

    fill_result = executor.execute(fill_task)

    assert fill_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(fill_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 1.0, "label": "1.0"},
        {"row_id": 2, "amount": 2.0, "label": "2.0"},
    ]


def test_fill_cells_node_empty_only_keeps_existing_values(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "label", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0]["label"] = "keep"
    rows[1]["label"] = ""
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    fill_task = make_task(
        node_type=FILL_CELLS_NODE_TYPE,
        node_run_id="node-run-fill-cells",
        node_instance_id="fill_cells",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "target_field": "label",
            "manual_value": "filled",
            "overwrite_rule": "empty_only",
        },
    )

    fill_result = executor.execute(fill_task)

    assert fill_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(fill_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "label": "keep"},
        {"row_id": 2, "label": "filled"},
    ]


def test_fill_range_node_fills_literal_value_in_field_and_row_range(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": ["row_id", "amount", "label", "status"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    fill_task = make_task(
        node_type=FILL_RANGE_NODE_TYPE,
        node_run_id="node-run-fill-range",
        node_instance_id="fill_range",
        input_refs=[input_ref.table_ref_id],
        config={
            "start_field": "label",
            "end_field": "status",
            "start_row": 2,
            "end_row": 3,
            "manual_value": "filled",
        },
    )

    fill_result = executor.execute(fill_task)

    assert fill_result.status == NodeResultStatus.SUCCEEDED
    assert fill_result.output_refs != generate_result.output_refs
    output_ref = registry.get(fill_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "fill_range_output"
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "amount",
        "label",
        "status",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {
            "row_id": 1,
            "amount": 1.0,
            "label": "label_0_1",
            "status": "status_0_1",
        },
        {"row_id": 2, "amount": 2.0, "label": "filled", "status": "filled"},
        {"row_id": 3, "amount": 3.0, "label": "filled", "status": "filled"},
    ]


def test_fill_range_node_empty_only_keeps_existing_area_values(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "label", "data_type": "TEXT"},
                    {"name": "status", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"label": "keep", "status": ""}
    rows[1] |= {"label": "", "status": "keep"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    fill_task = make_task(
        node_type=FILL_RANGE_NODE_TYPE,
        node_run_id="node-run-fill-range",
        node_instance_id="fill_range",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "start_field": "label",
            "end_field": "status",
            "manual_value": "filled",
            "overwrite_rule": "empty_only",
        },
    )

    fill_result = executor.execute(fill_task)

    assert fill_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(fill_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "label": "keep", "status": "filled"},
        {"row_id": 2, "label": "filled", "status": "keep"},
    ]


def test_fill_sequence_node_formats_counted_sequence_range(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 4,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "code", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    fill_result = executor.execute(
        make_task(
            node_type=FILL_SEQUENCE_NODE_TYPE,
            node_run_id="node-run-fill-sequence",
            node_instance_id="fill_sequence",
            input_refs=[input_ref.table_ref_id],
            config={
                "target_field": "code",
                "start_row": 2,
                "end_mode": "count",
                "count": 2,
                "start_value": 7,
                "step": 3,
                "zero_pad": 3,
                "prefix": "A-",
                "suffix": "-Z",
            },
        )
    )

    assert fill_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(fill_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "fill_sequence_output"
    assert [field.name for field in output_ref.schema] == ["row_id", "code"]
    assert output_ref.schema[1].data_type == "TEXT"
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "code": "code_0_1"},
        {"row_id": 2, "code": "A-007-Z"},
        {"row_id": 3, "code": "A-010-Z"},
        {"row_id": 4, "code": "code_0_4"},
    ]


def test_fill_sequence_node_can_fill_up_and_keep_existing_values(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "seq", "data_type": "INTEGER"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0]["seq"] = None
    rows[1]["seq"] = 99
    rows[2]["seq"] = None
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-sequence-input",
        output_name="sequence_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    fill_result = executor.execute(
        make_task(
            node_type=FILL_SEQUENCE_NODE_TYPE,
            node_run_id="node-run-fill-sequence",
            node_instance_id="fill_sequence",
            input_refs=[custom_input_ref.table_ref_id],
            config={
                "target_field": "seq",
                "start_row": 3,
                "direction": "up",
                "end_mode": "end_row",
                "end_row": 1,
                "start_value": 10,
                "step": 5,
                "overwrite_rule": "empty_only",
            },
        )
    )

    assert fill_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(fill_result.output_refs[0])
    assert output_ref.schema[1].data_type == "INTEGER"
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "seq": 20},
        {"row_id": 2, "seq": 99},
        {"row_id": 3, "seq": 10},
    ]


def test_replace_text_node_replaces_literal_partial_text(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "label", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    replace_task = make_task(
        node_type=REPLACE_TEXT_NODE_TYPE,
        node_run_id="node-run-replace-text",
        node_instance_id="replace_text",
        input_refs=[input_ref.table_ref_id],
        config={
            "target_field": "label",
            "match_mode": "contains",
            "match_value": "label",
            "replace_value": "item",
        },
    )

    replace_result = executor.execute(replace_task)

    assert replace_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(replace_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "replace_text_output"
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "label": "item_0_1"},
        {"row_id": 2, "label": "item_0_2"},
    ]


def test_replace_text_node_uses_same_row_value_sources(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "target", "data_type": "TEXT"},
                    {"name": "match", "data_type": "TEXT"},
                    {"name": "replacement", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"target": "abc-123", "match": "123", "replacement": "456"}
    rows[1] |= {"target": "xyz-789", "match": "789", "replacement": "000"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    replace_task = make_task(
        node_type=REPLACE_TEXT_NODE_TYPE,
        node_run_id="node-run-replace-text",
        node_instance_id="replace_text",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "target_field": "target",
            "match_value_source": {"mode": "row_field", "field": "match"},
            "replace_value_source": {"mode": "row_field", "field": "replacement"},
        },
    )

    replace_result = executor.execute(replace_task)

    assert replace_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(replace_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {
            "row_id": 1,
            "target": "abc-456",
            "match": "123",
            "replacement": "456",
        },
        {
            "row_id": 2,
            "target": "xyz-000",
            "match": "789",
            "replacement": "000",
        },
    ]


def test_replace_text_node_supports_regex_and_replace_count(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 1,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "label", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0]["label"] = "A1 B2 C3"
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    replace_task = make_task(
        node_type=REPLACE_TEXT_NODE_TYPE,
        node_run_id="node-run-replace-text",
        node_instance_id="replace_text",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "target_field": "label",
            "match_mode": "regex",
            "match_value": r"\d",
            "replace_value": "x",
            "replace_count": 2,
        },
    )

    replace_result = executor.execute(replace_task)

    assert replace_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(replace_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "label": "Ax Bx C3"},
    ]


def test_replace_text_node_skips_empty_match_value_by_default(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id", "label"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    replace_task = make_task(
        node_type=REPLACE_TEXT_NODE_TYPE,
        node_run_id="node-run-replace-text",
        node_instance_id="replace_text",
        input_refs=[input_ref.table_ref_id],
        config={
            "target_field": "label",
            "match_value": "",
            "replace_value": "x",
        },
    )

    replace_result = executor.execute(replace_task)

    assert replace_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(replace_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "label": "label_0_1"},
    ]


def test_delete_rows_node_deletes_row_number_list(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 5, "columns": ["row_id", "label"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    delete_task = make_task(
        node_type=DELETE_ROWS_NODE_TYPE,
        node_run_id="node-run-delete-rows",
        node_instance_id="delete_rows",
        input_refs=[input_ref.table_ref_id],
        config={"delete_mode": "row_numbers", "row_spec": [2, 4]},
    )

    delete_result = executor.execute(delete_task)

    assert delete_result.status == NodeResultStatus.SUCCEEDED
    assert delete_result.output_refs != generate_result.output_refs
    assert provider.count_rows(input_ref) == 5
    output_ref = registry.get(delete_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "delete_rows_output"
    assert [field.name for field in output_ref.schema] == ["row_id", "label"]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "label": "label_0_1"},
        {"row_id": 3, "label": "label_0_3"},
        {"row_id": 5, "label": "label_0_5"},
    ]


def test_delete_rows_node_deletes_row_range(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 5, "columns": ["row_id", "label"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    delete_task = make_task(
        node_type=DELETE_ROWS_NODE_TYPE,
        node_run_id="node-run-delete-rows",
        node_instance_id="delete_rows",
        input_refs=[input_ref.table_ref_id],
        config={
            "delete_mode": "row_range",
            "start_row": 2,
            "end_row": 4,
        },
    )

    delete_result = executor.execute(delete_task)

    assert delete_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(delete_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "label": "label_0_1"},
        {"row_id": 5, "label": "label_0_5"},
    ]


def test_delete_rows_node_uses_same_row_condition_value_source(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "value", "data_type": "TEXT"},
                    {"name": "match", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"value": "A-123", "match": "123"}
    rows[1] |= {"value": "B-999", "match": "123"}
    rows[2] |= {"value": "C-456", "match": "456"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    delete_task = make_task(
        node_type=DELETE_ROWS_NODE_TYPE,
        node_run_id="node-run-delete-rows",
        node_instance_id="delete_rows",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "delete_mode": "condition",
            "condition_field": "value",
            "condition_op": "CONTAINS",
            "condition_value_source": {"mode": "row_field", "field": "match"},
        },
    )

    delete_result = executor.execute(delete_task)

    assert delete_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(delete_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 2, "value": "B-999", "match": "123"},
    ]


def test_delete_rows_node_deletes_all_empty_rows(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": [
                    {"name": "left", "data_type": "TEXT"},
                    {"name": "right", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10)
    rows[0] |= {"left": "keep", "right": ""}
    rows[1] |= {"left": "", "right": ""}
    rows[2] |= {"left": None, "right": ""}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    delete_task = make_task(
        node_type=DELETE_ROWS_NODE_TYPE,
        node_run_id="node-run-delete-rows",
        node_instance_id="delete_rows",
        input_refs=[custom_input_ref.table_ref_id],
        config={"delete_mode": "empty", "empty_mode": "all_fields"},
    )

    delete_result = executor.execute(delete_task)

    assert delete_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(delete_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10) == [
        {"left": "keep", "right": ""},
    ]


def test_copy_rows_node_appends_copies_to_table_tail(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 3, "columns": ["row_id", "label"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    copy_task = make_task(
        node_type=COPY_ROWS_NODE_TYPE,
        node_run_id="node-run-copy-rows",
        node_instance_id="copy_rows",
        input_refs=[input_ref.table_ref_id],
        config={"source_row": 2, "copy_count": 2, "insert_mode": "append"},
    )

    copy_result = executor.execute(copy_task)

    assert copy_result.status == NodeResultStatus.SUCCEEDED
    assert copy_result.output_refs != generate_result.output_refs
    assert provider.count_rows(input_ref) == 3
    output_ref = registry.get(copy_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "copy_rows_output"
    assert [field.name for field in output_ref.schema] == ["row_id", "label"]
    assert provider.read_rows(output_ref, offset=0, limit=10) == [
        {"row_id": 1, "label": "label_0_1"},
        {"row_id": 2, "label": "label_0_2"},
        {"row_id": 3, "label": "label_0_3"},
        {"row_id": 2, "label": "label_0_2"},
        {"row_id": 2, "label": "label_0_2"},
    ]


def test_copy_rows_node_can_insert_at_head_and_relative_rows(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 3, "columns": ["row_id", "label"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])

    prepend_result = executor.execute(
        make_task(
            node_type=COPY_ROWS_NODE_TYPE,
            node_run_id="node-run-copy-rows-prepend",
            node_instance_id="copy_rows_prepend",
            input_refs=[input_ref.table_ref_id],
            config={"source_row": 3, "copy_count": 1, "insert_mode": "prepend"},
        )
    )
    before_result = executor.execute(
        make_task(
            node_type=COPY_ROWS_NODE_TYPE,
            node_run_id="node-run-copy-rows-before",
            node_instance_id="copy_rows_before",
            input_refs=[input_ref.table_ref_id],
            config={
                "source_row": 1,
                "copy_count": 1,
                "insert_mode": "before_row",
                "insert_row": 2,
            },
        )
    )
    after_result = executor.execute(
        make_task(
            node_type=COPY_ROWS_NODE_TYPE,
            node_run_id="node-run-copy-rows-after",
            node_instance_id="copy_rows_after",
            input_refs=[input_ref.table_ref_id],
            config={
                "source_row": 1,
                "copy_count": 1,
                "insert_mode": "after_row",
                "insert_row": 2,
            },
        )
    )

    assert prepend_result.status == NodeResultStatus.SUCCEEDED
    prepend_ref = registry.get(prepend_result.output_refs[0])
    assert provider.read_rows(prepend_ref, offset=0, limit=10) == [
        {"row_id": 3, "label": "label_0_3"},
        {"row_id": 1, "label": "label_0_1"},
        {"row_id": 2, "label": "label_0_2"},
        {"row_id": 3, "label": "label_0_3"},
    ]

    assert before_result.status == NodeResultStatus.SUCCEEDED
    before_ref = registry.get(before_result.output_refs[0])
    assert provider.read_rows(before_ref, offset=0, limit=10) == [
        {"row_id": 1, "label": "label_0_1"},
        {"row_id": 1, "label": "label_0_1"},
        {"row_id": 2, "label": "label_0_2"},
        {"row_id": 3, "label": "label_0_3"},
    ]

    assert after_result.status == NodeResultStatus.SUCCEEDED
    after_ref = registry.get(after_result.output_refs[0])
    assert provider.read_rows(after_ref, offset=0, limit=10) == [
        {"row_id": 1, "label": "label_0_1"},
        {"row_id": 2, "label": "label_0_2"},
        {"row_id": 1, "label": "label_0_1"},
        {"row_id": 3, "label": "label_0_3"},
    ]


def test_unpivot_rows_node_expands_value_fields_with_metadata(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "category", "data_type": "TEXT"},
                    {"name": "jan", "data_type": "FLOAT"},
                    {"name": "feb", "data_type": "FLOAT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    unpivot_result = executor.execute(
        make_task(
            node_type=UNPIVOT_ROWS_NODE_TYPE,
            node_run_id="node-run-unpivot-rows",
            node_instance_id="unpivot_rows",
            input_refs=[input_ref.table_ref_id],
            config={
                "value_fields": ["jan", "feb"],
                "keep_fields": ["row_id", "category"],
                "output_value_field": "amount",
                "source_field_name": "month",
                "output_original_row": True,
                "original_row_field": "source_row",
                "output_status": True,
                "status_field": "status",
            },
        )
    )

    assert unpivot_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(unpivot_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "unpivot_rows_output"
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "category",
        "amount",
        "month",
        "source_row",
        "status",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10) == [
        {
            "row_id": 1,
            "category": "category_0_1",
            "amount": "1.0",
            "month": "jan",
            "source_row": 1,
            "status": "mapped",
        },
        {
            "row_id": 1,
            "category": "category_0_1",
            "amount": "1.0",
            "month": "feb",
            "source_row": 1,
            "status": "mapped",
        },
        {
            "row_id": 2,
            "category": "category_0_2",
            "amount": "2.0",
            "month": "jan",
            "source_row": 2,
            "status": "mapped",
        },
        {
            "row_id": 2,
            "category": "category_0_2",
            "amount": "2.0",
            "month": "feb",
            "source_row": 2,
            "status": "mapped",
        },
    ]


def test_unpivot_rows_node_can_fill_empty_values_and_limit_rows(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "category", "data_type": "TEXT"},
                    {"name": "left", "data_type": "TEXT"},
                    {"name": "right", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"left": "keep-out", "right": "keep-out"}
    rows[1] |= {"left": "  A  ", "right": ""}
    rows[2] |= {"left": None, "right": "B"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-unpivot-input",
        output_name="unpivot_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    unpivot_result = executor.execute(
        make_task(
            node_type=UNPIVOT_ROWS_NODE_TYPE,
            node_run_id="node-run-unpivot-rows",
            node_instance_id="unpivot_rows",
            input_refs=[custom_input_ref.table_ref_id],
            config={
                "value_fields": ["left", "right"],
                "keep_fields": ["row_id"],
                "output_value_field": "mapped_value",
                "output_source_field": False,
                "output_status": True,
                "status_field": "status",
                "empty_mode": "fixed",
                "empty_fixed": "N/A",
                "trim_value": True,
                "start_row": 2,
                "end_mode": "count",
                "count": 2,
            },
        )
    )

    assert unpivot_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(unpivot_result.output_refs[0])
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "mapped_value",
        "status",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10) == [
        {"row_id": 2, "mapped_value": "A", "status": "mapped"},
        {"row_id": 2, "mapped_value": "N/A", "status": "empty_fixed"},
        {"row_id": 3, "mapped_value": "N/A", "status": "empty_fixed"},
        {"row_id": 3, "mapped_value": "B", "status": "mapped"},
    ]


def test_deduplicate_rows_node_keeps_first_matching_key(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "category", "data_type": "TEXT"},
                    {"name": "label", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"category": " Alpha ", "label": "first"}
    rows[1] |= {"category": "alpha", "label": "second"}
    rows[2] |= {"category": "Beta", "label": "third"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    dedupe_task = make_task(
        node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        node_run_id="node-run-deduplicate-rows",
        node_instance_id="deduplicate_rows",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "dedupe_mode": "key_fields",
            "key_fields": ["category"],
            "trim": True,
            "ignore_case": True,
            "keep_policy": "first",
        },
    )

    dedupe_result = executor.execute(dedupe_task)

    assert dedupe_result.status == NodeResultStatus.SUCCEEDED
    assert dedupe_result.output_refs != generate_result.output_refs
    assert provider.count_rows(custom_input_ref) == 3
    output_ref = registry.get(dedupe_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "deduplicate_rows_output"
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "category",
        "label",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10) == [
        {"row_id": 1, "category": " Alpha ", "label": "first"},
        {"row_id": 3, "category": "Beta", "label": "third"},
    ]


def test_deduplicate_rows_node_can_keep_last_matching_key(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "category", "data_type": "TEXT"},
                    {"name": "label", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"category": "alpha", "label": "first"}
    rows[1] |= {"category": "alpha", "label": "second"}
    rows[2] |= {"category": "beta", "label": "third"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    dedupe_task = make_task(
        node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        node_run_id="node-run-deduplicate-rows",
        node_instance_id="deduplicate_rows",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "key_fields": ["category"],
            "keep_policy": "last",
        },
    )

    dedupe_result = executor.execute(dedupe_task)

    assert dedupe_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(dedupe_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10) == [
        {"row_id": 2, "category": "alpha", "label": "second"},
        {"row_id": 3, "category": "beta", "label": "third"},
    ]


def test_deduplicate_rows_node_can_compare_entire_rows(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": [
                    {"name": "category", "data_type": "TEXT"},
                    {"name": "label", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10)
    rows[0] |= {"category": "alpha", "label": "same"}
    rows[1] |= {"category": "alpha", "label": "same"}
    rows[2] |= {"category": "alpha", "label": "different"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    dedupe_task = make_task(
        node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        node_run_id="node-run-deduplicate-rows",
        node_instance_id="deduplicate_rows",
        input_refs=[custom_input_ref.table_ref_id],
        config={"dedupe_mode": "entire_row"},
    )

    dedupe_result = executor.execute(dedupe_task)

    assert dedupe_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(dedupe_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10) == [
        {"category": "alpha", "label": "same"},
        {"category": "alpha", "label": "different"},
    ]


def test_deduplicate_rows_node_mark_mode_keeps_rows_and_adds_markers(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "category", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"category": "alpha"}
    rows[1] |= {"category": "alpha"}
    rows[2] |= {"category": "beta"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    dedupe_task = make_task(
        node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        node_run_id="node-run-deduplicate-rows",
        node_instance_id="deduplicate_rows",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "key_fields": ["category"],
            "output_mode": "mark",
            "keep_policy": "first",
        },
    )

    dedupe_result = executor.execute(dedupe_task)

    assert dedupe_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(dedupe_result.output_refs[0])
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "category",
        "_duplicate_group",
        "_duplicate_status",
        "_duplicate_index",
        "_duplicate_count",
        "_keep_row",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10) == [
        {
            "row_id": 1,
            "category": "alpha",
            "_duplicate_group": "group-1",
            "_duplicate_status": "kept",
            "_duplicate_index": 1,
            "_duplicate_count": 2,
            "_keep_row": 1,
        },
        {
            "row_id": 2,
            "category": "alpha",
            "_duplicate_group": "group-1",
            "_duplicate_status": "duplicate",
            "_duplicate_index": 2,
            "_duplicate_count": 2,
            "_keep_row": 0,
        },
        {
            "row_id": 3,
            "category": "beta",
            "_duplicate_group": "group-3",
            "_duplicate_status": "unique",
            "_duplicate_index": 1,
            "_duplicate_count": 1,
            "_keep_row": 1,
        },
    ]


def test_advanced_filter_rows_node_filters_with_and_field_value_source(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "amount", "data_type": "FLOAT"},
                    {"name": "threshold", "data_type": "FLOAT"},
                    {"name": "category", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"amount": 1.0, "threshold": 2.0, "category": "keep"}
    rows[1] |= {"amount": 3.0, "threshold": 2.0, "category": "drop"}
    rows[2] |= {"amount": 4.0, "threshold": 3.0, "category": "keep"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    filter_task = make_task(
        node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
        node_run_id="node-run-advanced-filter",
        node_instance_id="advanced_filter",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "logic": "and",
            "conditions": [
                {
                    "field": "amount",
                    "operator": "GT",
                    "value_source": {"mode": "row_field", "field": "threshold"},
                },
                {"field": "category", "operator": "EQ", "value": "keep"},
            ],
        },
    )

    filter_result = executor.execute(filter_task)

    assert filter_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(filter_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "advanced_filter_output"
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 3, "amount": 4.0, "threshold": 3.0, "category": "keep"},
    ]


def test_advanced_filter_rows_node_applies_or_output_fields_and_limit(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 4,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "amount", "data_type": "FLOAT"},
                    {"name": "category", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"amount": 1.0, "category": "keep"}
    rows[1] |= {"amount": 2.0, "category": "drop"}
    rows[2] |= {"amount": 3.0, "category": "drop"}
    rows[3] |= {"amount": 4.0, "category": "keep"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    filter_task = make_task(
        node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
        node_run_id="node-run-advanced-filter",
        node_instance_id="advanced_filter",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "logic": "or",
            "conditions": [
                {"field": "category", "operator": "EQ", "value": "keep"},
                {"field": "amount", "operator": "GE", "value": 3.0},
            ],
            "output_fields": ["row_id", "category"],
            "result_limit": 2,
        },
    )

    filter_result = executor.execute(filter_task)

    assert filter_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(filter_result.output_refs[0])
    assert [field.name for field in output_ref.schema] == ["row_id", "category"]
    assert provider.read_rows(output_ref, offset=0, limit=10) == [
        {"row_id": 1, "category": "keep"},
        {"row_id": 3, "category": "drop"},
    ]


def test_advanced_filter_rows_node_can_remove_duplicate_output_rows(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "category", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"category": "same"}
    rows[1] |= {"category": "same"}
    rows[2] |= {"category": "other"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    filter_task = make_task(
        node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
        node_run_id="node-run-advanced-filter",
        node_instance_id="advanced_filter",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "conditions": [],
            "output_fields": ["category"],
            "remove_duplicates": True,
        },
    )

    filter_result = executor.execute(filter_task)

    assert filter_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(filter_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10) == [
        {"category": "same"},
        {"category": "other"},
    ]


def test_extract_text_node_uses_dynamic_regex_and_unmatched_value_source(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "source", "data_type": "TEXT"},
                    {"name": "pattern", "data_type": "TEXT"},
                    {"name": "fallback", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {
        "source": "item-123",
        "pattern": r"item-(\d+)",
        "fallback": "missing",
    }
    rows[1] |= {
        "source": "other",
        "pattern": r"item-(\d+)",
        "fallback": "fallback-value",
    }
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    extract_task = make_task(
        node_type=EXTRACT_TEXT_NODE_TYPE,
        node_run_id="node-run-extract-text",
        node_instance_id="extract_text",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "source_field": "source",
            "method": "regex",
            "rule_value_source": {"mode": "row_field", "field": "pattern"},
            "regex_group": 1,
            "new_field": "result",
            "unmatched_mode": "fixed",
            "unmatched_value_source": {"mode": "row_field", "field": "fallback"},
        },
    )

    extract_result = executor.execute(extract_task)

    assert extract_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(extract_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "extract_text_output"
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "source",
        "pattern",
        "fallback",
        "result",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {
            "row_id": 1,
            "source": "item-123",
            "pattern": r"item-(\d+)",
            "fallback": "missing",
            "result": "123",
        },
        {
            "row_id": 2,
            "source": "other",
            "pattern": r"item-(\d+)",
            "fallback": "fallback-value",
            "result": "fallback-value",
        },
    ]


def test_extract_text_node_can_overwrite_source_with_delimiter_part(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id", "source"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0]["source"] = "left|middle|right"
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    extract_task = make_task(
        node_type=EXTRACT_TEXT_NODE_TYPE,
        node_run_id="node-run-extract-text",
        node_instance_id="extract_text",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "source_field": "source",
            "method": "delimiter",
            "delimiter": "|",
            "part_index": 2,
            "output_mode": "overwrite_source",
        },
    )

    extract_result = executor.execute(extract_task)

    assert extract_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(extract_result.output_refs[0])
    assert [field.name for field in output_ref.schema] == ["row_id", "source"]
    assert output_ref.schema[1].data_type == "TEXT"
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "source": "middle"},
    ]


def test_extract_text_node_can_extract_fixed_position_to_existing_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 1,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "source", "data_type": "TEXT"},
                    {"name": "target", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"source": "abcdef", "target": ""}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    extract_task = make_task(
        node_type=EXTRACT_TEXT_NODE_TYPE,
        node_run_id="node-run-extract-text",
        node_instance_id="extract_text",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "source_field": "source",
            "method": "position",
            "start_pos": 2,
            "extract_len": 3,
            "output_mode": "overwrite",
            "target_field": "target",
        },
    )

    extract_result = executor.execute(extract_task)

    assert extract_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(extract_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "source": "abcdef", "target": "bcd"},
    ]


def test_lookup_matched_field_name_node_outputs_match_metadata(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    main_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-main",
            node_instance_id="main",
            config={"rows": 3, "columns": ["row_id", "source"], "seed": 0},
        )
    )
    lookup_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-lookup",
            node_instance_id="lookup",
            config={
                "rows": 3,
                "columns": [
                    {"name": "lookup_id", "data_type": "INTEGER"},
                    {"name": "first", "data_type": "TEXT"},
                    {"name": "second", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    main_ref = registry.get(main_result.output_refs[0])
    main_rows = provider.read_rows(main_ref, offset=0, limit=10, order_by=["row_id"])
    main_rows[0]["source"] = "A"
    main_rows[1]["source"] = "B"
    main_rows[2]["source"] = "Z"
    main_staged = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-main-custom",
        output_name="main_custom",
        schema=main_ref.schema,
    )
    provider.insert_rows(main_staged, main_rows)
    registry.register_staging(main_staged)
    main_input_ref = registry.publish(main_staged.table_ref_id)

    lookup_ref = registry.get(lookup_result.output_refs[0])
    lookup_rows = provider.read_rows(
        lookup_ref,
        offset=0,
        limit=10,
        order_by=["lookup_id"],
    )
    lookup_rows[0] |= {"first": "A", "second": "X"}
    lookup_rows[1] |= {"first": "Y", "second": "B"}
    lookup_rows[2] |= {"first": "A", "second": "C"}
    lookup_staged = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-lookup-custom",
        output_name="lookup_custom",
        schema=lookup_ref.schema,
    )
    provider.insert_rows(lookup_staged, lookup_rows)
    registry.register_staging(lookup_staged)
    lookup_input_ref = registry.publish(lookup_staged.table_ref_id)

    lookup_task = make_task(
        node_type=LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
        node_run_id="node-run-lookup-matched-field",
        node_instance_id="lookup_matched_field",
        input_refs=[main_input_ref.table_ref_id, lookup_input_ref.table_ref_id],
        config={
            "source_field": "source",
            "lookup_fields": ["first", "second"],
            "output_match_value": True,
            "output_match_row": True,
            "no_match_value": "none",
        },
    )

    lookup_node_result = executor.execute(lookup_task)

    assert lookup_node_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(lookup_node_result.output_refs[0])
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "source",
        "matched_field",
        "matched_value",
        "matched_row",
        "match_status",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {
            "row_id": 1,
            "source": "A",
            "matched_field": "first",
            "matched_value": "A",
            "matched_row": 1,
            "match_status": "multiple_matched",
        },
        {
            "row_id": 2,
            "source": "B",
            "matched_field": "second",
            "matched_value": "B",
            "matched_row": 2,
            "match_status": "matched",
        },
        {
            "row_id": 3,
            "source": "Z",
            "matched_field": "none",
            "matched_value": "none",
            "matched_row": None,
            "match_status": "not_matched",
        },
    ]


def test_merge_columns_node_merges_fields_with_separator_and_trim(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "first", "data_type": "TEXT"},
                    {"name": "last", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"first": " Ada ", "last": " Lovelace "}
    rows[1] |= {"first": "Grace", "last": "Hopper"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    merge_task = make_task(
        node_type=MERGE_COLUMNS_NODE_TYPE,
        node_run_id="node-run-merge-columns",
        node_instance_id="merge_columns",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "fields": ["first", "last"],
            "separators": [" "],
            "output_field": "full_name",
            "trim_value": True,
        },
    )

    merge_result = executor.execute(merge_task)

    assert merge_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(merge_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "merge_columns_output"
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "first",
        "last",
        "full_name",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {
            "row_id": 1,
            "first": " Ada ",
            "last": " Lovelace ",
            "full_name": "Ada Lovelace",
        },
        {
            "row_id": 2,
            "first": "Grace",
            "last": "Hopper",
            "full_name": "Grace Hopper",
        },
    ]


def test_merge_columns_node_skip_empty_and_overwrite_conflict(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "left", "data_type": "TEXT"},
                    {"name": "middle", "data_type": "TEXT"},
                    {"name": "right", "data_type": "TEXT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"left": "A", "middle": "", "right": "C"}
    rows[1] |= {"left": "", "middle": "B", "right": ""}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    merge_task = make_task(
        node_type=MERGE_COLUMNS_NODE_TYPE,
        node_run_id="node-run-merge-columns",
        node_instance_id="merge_columns",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "fields": ["left", "middle", "right"],
            "separators": ["-"],
            "output_field": "right",
            "conflict_mode": "overwrite",
            "skip_empty": True,
        },
    )

    merge_result = executor.execute(merge_task)

    assert merge_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(merge_result.output_refs[0])
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "left",
        "middle",
        "right",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "left": "A", "middle": "", "right": "A-C"},
        {"row_id": 2, "left": "", "middle": "B", "right": "B"},
    ]


def test_numeric_column_operation_node_adds_same_row_operand_to_new_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "amount", "data_type": "FLOAT"},
                    {"name": "fee", "data_type": "FLOAT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"amount": 10.0, "fee": 1.5}
    rows[1] |= {"amount": 20.0, "fee": 2.25}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    numeric_task = make_task(
        node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        node_run_id="node-run-numeric-column",
        node_instance_id="numeric_column",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "target_field": "amount",
            "operation": "add",
            "operand_source": "row_field",
            "operand_field": "fee",
            "output_mode": "new_field",
            "output_field": "total",
            "decimal_places": 2,
        },
    )

    numeric_result = executor.execute(numeric_task)

    assert numeric_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(numeric_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "numeric_column_output"
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "amount",
        "fee",
        "total",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 10.0, "fee": 1.5, "total": 11.5},
        {"row_id": 2, "amount": 20.0, "fee": 2.25, "total": 22.25},
    ]


def test_numeric_column_operation_node_handles_divide_zero_with_fixed_value(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": [
                    {"name": "row_id", "data_type": "INTEGER"},
                    {"name": "amount", "data_type": "FLOAT"},
                    {"name": "divisor", "data_type": "FLOAT"},
                ],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"amount": 10.0, "divisor": 2.0}
    rows[1] |= {"amount": 10.0, "divisor": 0.0}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    numeric_task = make_task(
        node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        node_run_id="node-run-numeric-column",
        node_instance_id="numeric_column",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "target_field": "amount",
            "operation": "divide",
            "operand_source": "row_field",
            "operand_field": "divisor",
            "output_mode": "overwrite",
            "divide_zero_policy": "fixed",
            "divide_zero_fixed": -1,
        },
    )

    numeric_result = executor.execute(numeric_task)

    assert numeric_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(numeric_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 5.0, "divisor": 2.0},
        {"row_id": 2, "amount": -1.0, "divisor": 0.0},
    ]


def test_numeric_column_operation_node_limits_changes_to_row_range(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 3, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    numeric_task = make_task(
        node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        node_run_id="node-run-numeric-column",
        node_instance_id="numeric_column",
        input_refs=[input_ref.table_ref_id],
        config={
            "target_field": "amount",
            "operation": "multiply",
            "operand_value": 10,
            "range_mode": "row_range",
            "start_row": 2,
            "end_row": 2,
        },
    )

    numeric_result = executor.execute(numeric_task)

    assert numeric_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(numeric_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 1.0},
        {"row_id": 2, "amount": 20.0},
        {"row_id": 3, "amount": 3.0},
    ]


def test_add_current_datetime_column_node_uses_fixed_time_for_run(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 3, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    datetime_task = make_task(
        node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
        node_run_id="node-run-current-datetime",
        node_instance_id="current_datetime",
        input_refs=[input_ref.table_ref_id],
        config={
            "new_field": "run_time",
            "time_mode": "fixed",
            "format_mode": "strftime",
            "strftime_template": "%Y%m%d%H%M%S",
        },
    )

    datetime_result = executor.execute(datetime_task)

    assert datetime_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(datetime_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "current_datetime_output"
    rows = provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"])
    run_time_values = {row["run_time"] for row in rows}
    assert len(run_time_values) == 1
    run_time = run_time_values.pop()
    assert len(run_time) == 14
    assert run_time.isdigit()


def test_add_current_datetime_column_node_can_overwrite_target_with_template(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id", "label"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    datetime_task = make_task(
        node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
        node_run_id="node-run-current-datetime",
        node_instance_id="current_datetime",
        input_refs=[input_ref.table_ref_id],
        config={
            "output_mode": "overwrite",
            "target_field": "label",
            "format_mode": "template",
            "template": "{year}-{month}-{day}",
        },
    )

    datetime_result = executor.execute(datetime_task)

    assert datetime_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(datetime_result.output_refs[0])
    rows = provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"])
    assert len(rows[0]["label"]) == 10
    assert rows[0]["label"].count("-") == 2


def test_parse_datetime_node_auto_parses_dates_and_outputs_status(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "raw_date"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0]["raw_date"] = "2026-07-07"
    rows[1]["raw_date"] = "not-a-date"
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    parse_task = make_task(
        node_type=PARSE_DATETIME_NODE_TYPE,
        node_run_id="node-run-parse-datetime",
        node_instance_id="parse_datetime",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "source_field": "raw_date",
            "parse_type": "date",
            "new_field": "parsed_date",
            "output_status": True,
        },
    )

    parse_result = executor.execute(parse_task)

    assert parse_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(parse_result.output_refs[0])
    assert output_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert output_ref.logical_table_id == "parse_datetime_output"
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {
            "row_id": 1,
            "raw_date": "2026-07-07",
            "parsed_date": "2026-07-07",
            "parse_status": "parsed",
        },
        {
            "row_id": 2,
            "raw_date": "not-a-date",
            "parsed_date": "",
            "parse_status": "failed",
        },
    ]


def test_parse_datetime_node_combines_separate_time_field_with_strptime(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 1,
                "columns": ["row_id", "raw_date", "raw_time"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"raw_date": "07/07/2026", "raw_time": "14:05"}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-input",
        output_name="custom_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)
    parse_task = make_task(
        node_type=PARSE_DATETIME_NODE_TYPE,
        node_run_id="node-run-parse-datetime",
        node_instance_id="parse_datetime",
        input_refs=[custom_input_ref.table_ref_id],
        config={
            "source_field": "raw_date",
            "use_separate_time_field": True,
            "time_source_field": "raw_time",
            "input_structure": "strptime",
            "input_format": "%m/%d/%Y %H:%M",
            "datetime_output_template": "%Y-%m-%dT%H:%M",
            "new_field": "parsed_datetime",
            "output_status": False,
        },
    )

    parse_result = executor.execute(parse_task)

    assert parse_result.status == NodeResultStatus.SUCCEEDED
    output_ref = registry.get(parse_result.output_refs[0])
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {
            "row_id": 1,
            "raw_date": "07/07/2026",
            "raw_time": "14:05",
            "parsed_datetime": "2026-07-07T14:05",
        },
    ]


def test_condition_flag_node_evaluates_row_count_true_and_false(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 3, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])

    true_result = executor.execute(
        make_task(
            node_type=CONDITION_FLAG_NODE_TYPE,
            node_run_id="node-run-condition-row-count-true",
            node_instance_id="condition_row_count_true",
            input_refs=[input_ref.table_ref_id],
            config={
                "flag_name": "enough_rows",
                "condition_type": "row_count",
                "operator": "GE",
                "value": 3,
                "true_value": "yes",
                "false_value": "no",
            },
        )
    )
    false_result = executor.execute(
        make_task(
            node_type=CONDITION_FLAG_NODE_TYPE,
            node_run_id="node-run-condition-row-count-false",
            node_instance_id="condition_row_count_false",
            input_refs=[input_ref.table_ref_id],
            config={
                "flag_name": "too_few_rows",
                "condition_type": "row_count",
                "operator": "LT",
                "value": 3,
                "true_value": "yes",
                "false_value": "no",
            },
        )
    )

    assert true_result.status == NodeResultStatus.SUCCEEDED
    _true_ref, true_row = read_single_output_row(
        registry=registry,
        provider=provider,
        result=true_result,
    )
    assert true_row["flag_name"] == "enough_rows"
    assert true_row["condition_type"] == "row_count"
    assert true_row["result"] == "true"
    assert true_row["output_value"] == "yes"
    assert true_row["matched_count"] == 3
    assert true_row["total_rows"] == 3
    assert json.loads(true_row["details"])["row_count"] == 3

    assert false_result.status == NodeResultStatus.SUCCEEDED
    _false_ref, false_row = read_single_output_row(
        registry=registry,
        provider=provider,
        result=false_result,
    )
    assert false_row["result"] == "false"
    assert false_row["output_value"] == "no"
    assert false_row["matched_count"] == 0
    assert false_row["total_rows"] == 3


def test_condition_flag_node_evaluates_field_exists_true_and_false(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])

    exists_result = executor.execute(
        make_task(
            node_type=CONDITION_FLAG_NODE_TYPE,
            node_run_id="node-run-condition-field-exists",
            node_instance_id="condition_field_exists",
            input_refs=[input_ref.table_ref_id],
            config={
                "condition_type": "field_exists",
                "field": "amount",
            },
        )
    )
    missing_result = executor.execute(
        make_task(
            node_type=CONDITION_FLAG_NODE_TYPE,
            node_run_id="node-run-condition-field-missing",
            node_instance_id="condition_field_missing",
            input_refs=[input_ref.table_ref_id],
            config={
                "condition_type": "field_exists",
                "field": "missing",
            },
        )
    )

    assert exists_result.status == NodeResultStatus.SUCCEEDED
    _exists_ref, exists_row = read_single_output_row(
        registry=registry,
        provider=provider,
        result=exists_result,
    )
    assert exists_row["result"] == "true"
    assert exists_row["matched_count"] == 2
    assert json.loads(exists_row["details"]) == {
        "exists": True,
        "field": "amount",
    }

    assert missing_result.status == NodeResultStatus.SUCCEEDED
    _missing_ref, missing_row = read_single_output_row(
        registry=registry,
        provider=provider,
        result=missing_result,
    )
    assert missing_row["result"] == "false"
    assert missing_row["matched_count"] == 0
    assert json.loads(missing_row["details"]) == {
        "exists": False,
        "field": "missing",
    }


def test_condition_flag_node_evaluates_field_value_literal_and_same_row_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": ["row_id", "label", "needle", "left", "right"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0] |= {"label": "abc-123", "needle": "123", "left": "A", "right": "A"}
    rows[1] |= {"label": "xyz-789", "needle": "000", "left": "B", "right": "B"}
    rows[2] |= {"label": "plain", "needle": "plain", "left": "C", "right": "D"}
    custom_input_ref = publish_runtime_rows(
        registry=registry,
        provider=provider,
        schema=input_ref.schema,
        rows=rows,
        output_name="condition_input",
    )

    literal_result = executor.execute(
        make_task(
            node_type=CONDITION_FLAG_NODE_TYPE,
            node_run_id="node-run-condition-field-literal",
            node_instance_id="condition_field_literal",
            input_refs=[custom_input_ref.table_ref_id],
            config={
                "condition_type": "field_value",
                "field": "label",
                "operator": "CONTAINS",
                "value": "123",
                "aggregation": "any",
            },
        )
    )
    field_result = executor.execute(
        make_task(
            node_type=CONDITION_FLAG_NODE_TYPE,
            node_run_id="node-run-condition-field-source",
            node_instance_id="condition_field_source",
            input_refs=[custom_input_ref.table_ref_id],
            config={
                "condition_type": "field_value",
                "field": "left",
                "operator": "EQ",
                "value_source": {"mode": "field", "field": "right"},
                "aggregation": "any",
            },
        )
    )

    assert literal_result.status == NodeResultStatus.SUCCEEDED
    _literal_ref, literal_row = read_single_output_row(
        registry=registry,
        provider=provider,
        result=literal_result,
    )
    assert literal_row["result"] == "true"
    assert literal_row["matched_count"] == 1
    literal_details = json.loads(literal_row["details"])
    assert literal_details["value_source"] == "literal"

    assert field_result.status == NodeResultStatus.SUCCEEDED
    _field_ref, field_row = read_single_output_row(
        registry=registry,
        provider=provider,
        result=field_result,
    )
    assert field_row["result"] == "true"
    assert field_row["matched_count"] == 2
    field_details = json.loads(field_row["details"])
    assert field_details["value_source"] == "field"
    assert field_details["value_field"] == "right"


def test_condition_flag_node_supports_field_value_aggregations(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 3, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    cases = [
        ("any", "GT", 2, "true", 1),
        ("all", "GE", 1, "true", 3),
        ("first", "EQ", 1, "true", 1),
        ("count", "GT", 1, "true", 2),
    ]

    for aggregation, operator, value, expected_result, expected_count in cases:
        result = executor.execute(
            make_task(
                node_type=CONDITION_FLAG_NODE_TYPE,
                node_run_id=f"node-run-condition-{aggregation}",
                node_instance_id=f"condition_{aggregation}",
                input_refs=[input_ref.table_ref_id],
                config={
                    "condition_type": "field_value",
                    "field": "amount",
                    "operator": operator,
                    "value": value,
                    "aggregation": aggregation,
                },
            )
        )

        assert result.status == NodeResultStatus.SUCCEEDED
        _output_ref, row = read_single_output_row(
            registry=registry,
            provider=provider,
            result=result,
        )
        assert row["aggregation"] == aggregation
        assert row["result"] == expected_result
        assert row["matched_count"] == expected_count
        assert row["total_rows"] == 3


def test_condition_flag_node_handles_empty_and_case_insensitive_values(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 3, "columns": ["row_id", "label"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10, order_by=["row_id"])
    rows[0]["label"] = ""
    rows[1]["label"] = "Alpha"
    rows[2]["label"] = "beta"
    custom_input_ref = publish_runtime_rows(
        registry=registry,
        provider=provider,
        schema=input_ref.schema,
        rows=rows,
        output_name="condition_empty_input",
    )

    empty_result = executor.execute(
        make_task(
            node_type=CONDITION_FLAG_NODE_TYPE,
            node_run_id="node-run-condition-empty",
            node_instance_id="condition_empty",
            input_refs=[custom_input_ref.table_ref_id],
            config={
                "condition_type": "field_value",
                "field": "label",
                "operator": "IS_EMPTY",
                "aggregation": "any",
            },
        )
    )
    case_result = executor.execute(
        make_task(
            node_type=CONDITION_FLAG_NODE_TYPE,
            node_run_id="node-run-condition-case",
            node_instance_id="condition_case",
            input_refs=[custom_input_ref.table_ref_id],
            config={
                "condition_type": "field_value",
                "field": "label",
                "operator": "EQ",
                "value": "alpha",
                "aggregation": "any",
                "case_sensitive": False,
            },
        )
    )

    assert empty_result.status == NodeResultStatus.SUCCEEDED
    _empty_ref, empty_row = read_single_output_row(
        registry=registry,
        provider=provider,
        result=empty_result,
    )
    assert empty_row["result"] == "true"
    assert empty_row["matched_count"] == 1

    assert case_result.status == NodeResultStatus.SUCCEEDED
    _case_ref, case_row = read_single_output_row(
        registry=registry,
        provider=provider,
        result=case_result,
    )
    assert case_row["result"] == "true"
    assert case_row["matched_count"] == 1
    assert json.loads(case_row["details"])["case_sensitive"] is False


def test_condition_flag_node_returns_validation_error_for_incompatible_compare(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id", "label"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10)
    rows[0]["label"] = "not-a-number"
    custom_input_ref = publish_runtime_rows(
        registry=registry,
        provider=provider,
        schema=input_ref.schema,
        rows=rows,
        output_name="condition_incompatible_input",
    )

    result = executor.execute(
        make_task(
            node_type=CONDITION_FLAG_NODE_TYPE,
            node_run_id="node-run-condition-incompatible",
            node_instance_id="condition_incompatible",
            input_refs=[custom_input_ref.table_ref_id],
            config={
                "condition_type": "field_value",
                "field": "label",
                "operator": "GT",
                "value": 1,
            },
        )
    )

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "cannot compare values" in result.error["message"]


def test_save_memory_table_node_outputs_current_ref_and_auxiliary_memory_ref(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider, memory_provider = (
        make_executor_with_memory_provider(tmp_path)
    )
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    save_task = make_task(
        node_type=SAVE_MEMORY_TABLE_NODE_TYPE,
        node_run_id="node-run-save-memory",
        node_instance_id="save_memory",
        input_refs=[input_ref.table_ref_id],
        config={"table_name": "scratch", "mode": "overwrite"},
    )

    save_result = executor.execute(save_task)

    assert save_result.status == NodeResultStatus.SUCCEEDED
    assert save_result.output_refs[0] == input_ref.table_ref_id
    assert len(save_result.output_refs) == 2
    memory_ref = registry.get(save_result.output_refs[1])
    assert memory_ref.provider_id == MEMORY_PROVIDER_ID
    assert memory_ref.storage_kind == TableStorageKind.MEMORY
    assert memory_ref.role == TableRole.AUXILIARY
    assert memory_ref.logical_table_id == "scratch"
    assert provider.count_rows(input_ref) == 2
    assert memory_provider.count_rows(memory_ref) == 2
    assert memory_provider.read_rows(
        memory_ref,
        offset=0,
        limit=10,
        order_by=["row_id"],
    ) == [
        {"row_id": 1, "amount": 1.0},
        {"row_id": 2, "amount": 2.0},
    ]


def test_save_run_table_node_outputs_current_ref_and_named_transit_ref(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider, memory_provider = (
        make_executor_with_memory_provider(tmp_path)
    )
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    save_task = make_task(
        node_type=SAVE_RUN_TABLE_NODE_TYPE,
        node_run_id="node-run-save-run",
        node_instance_id="save_run",
        input_refs=[input_ref.table_ref_id],
        config={
            "transit_name": "daily_scratch",
            "save_memory": True,
            "mode": "overwrite",
        },
    )

    save_result = executor.execute(save_task)

    assert save_result.status == NodeResultStatus.SUCCEEDED
    assert save_result.output_refs[0] == input_ref.table_ref_id
    assert len(save_result.output_refs) == 2
    transit_ref = registry.get(save_result.output_refs[1])
    assert transit_ref.provider_id == MEMORY_PROVIDER_ID
    assert transit_ref.storage_kind == TableStorageKind.MEMORY
    assert transit_ref.role == TableRole.AUXILIARY
    assert transit_ref.logical_table_id == "daily_scratch"
    assert provider.count_rows(input_ref) == 2
    assert memory_provider.read_rows(
        transit_ref,
        offset=0,
        limit=10,
        order_by=["row_id"],
    ) == [
        {"row_id": 1, "amount": 1.0},
        {"row_id": 2, "amount": 2.0},
    ]


def test_save_run_table_node_can_pass_through_without_memory_save(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider, _memory_provider = (
        make_executor_with_memory_provider(tmp_path)
    )
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])

    save_result = executor.execute(
        make_task(
            node_type=SAVE_RUN_TABLE_NODE_TYPE,
            node_run_id="node-run-save-run",
            node_instance_id="save_run",
            input_refs=[input_ref.table_ref_id],
            config={"save_memory": False},
        )
    )

    assert save_result.status == NodeResultStatus.SUCCEEDED
    assert save_result.output_refs == [input_ref.table_ref_id]


def test_write_selected_columns_node_outputs_write_plan_status_table(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    write_task = make_task(
        node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
        node_run_id="node-run-write-selected",
        node_instance_id="write_selected",
        input_refs=[input_ref.table_ref_id],
        config={
            "selected_fields": ["row_id", "amount"],
            "target_type": "sqlite",
            "target_table": "target_orders",
            "write_mode": "append",
            "field_name_mode": "mapping",
            "field_mappings": [
                {"source_field": "row_id", "target_field": "target_id"},
                {"source_field": "amount", "target_field": "target_amount"},
            ],
            "overwrite_rule": "empty_only",
            "enable_write": False,
            "backup_before_write": True,
        },
    )

    write_result = executor.execute(write_task)

    assert write_result.status == NodeResultStatus.SUCCEEDED
    assert len(write_result.output_refs) == 1
    status_ref = registry.get(write_result.output_refs[0])
    assert status_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert status_ref.logical_table_id == "write_selected_output"
    assert provider.read_rows(status_ref, offset=0, limit=10) == [
        {
            "status": "skipped",
            "source_type": "current_table",
            "target_type": "sqlite",
            "target_table": "target_orders",
            "write_mode": "append",
            "overwrite_rule": "empty_only",
            "selected_field_count": 2,
            "mapping_count": 2,
            "source_row_count": 3,
            "enable_write": "false",
            "backup_before_write": "true",
            "actual_write": "false",
            "affected_rows": 0,
            "skipped_rows": 3,
            "warning_count": 0,
            "warnings": "",
            "target_table_ref_id": "",
            "selected_fields": "row_id,amount",
            "target_fields": "target_id,target_amount",
            "skipped_reason": "enable_write is false",
        }
    ]
    assert provider.count_rows(input_ref) == 3


def test_write_selected_columns_node_does_not_create_runtime_target_when_disabled(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])

    write_result = executor.execute(
        make_task(
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            node_run_id="node-run-write-selected-disabled",
            node_instance_id="write_selected_disabled",
            input_refs=[input_ref.table_ref_id],
            config={
                "selected_fields": ["row_id"],
                "target_type": "run_table",
                "target_transit_table": "disabled_target",
                "enable_write": False,
            },
        )
    )

    assert write_result.status == NodeResultStatus.SUCCEEDED
    assert len(write_result.output_refs) == 1
    status_ref = registry.get(write_result.output_refs[0])
    status_rows = provider.read_rows(status_ref, offset=0, limit=10)
    assert status_rows[0]["target_type"] == "run_table"
    assert status_rows[0]["target_table"] == "disabled_target"
    assert status_rows[0]["actual_write"] == "false"
    assert status_rows[0]["target_table_ref_id"] == ""
    assert status_rows[0]["skipped_reason"] == "enable_write is false"
    assert [
        table_ref.logical_table_id
        for table_ref in registry.list_by_workflow_run("run-1")
    ].count("disabled_target") == 0


def test_write_selected_columns_node_writes_run_table_when_enabled(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])

    write_result = executor.execute(
        make_task(
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            node_run_id="node-run-write-selected",
            node_instance_id="write_selected",
            input_refs=[input_ref.table_ref_id],
            config={
                "selected_fields": ["row_id"],
                "target_transit_table": "target_scratch",
                "enable_write": True,
            },
        )
    )

    assert write_result.status == NodeResultStatus.SUCCEEDED
    status_ref = registry.get(write_result.output_refs[0])
    written_ref = registry.get(write_result.output_refs[1])
    assert len(write_result.output_refs) == 2
    assert written_ref.logical_table_id == "target_scratch"
    assert written_ref.role == TableRole.AUXILIARY
    assert written_ref.storage_kind == TableStorageKind.RUNTIME_SQL
    assert provider.read_rows(status_ref, offset=0, limit=10) == [
        {
            "status": "written",
            "source_type": "current_table",
            "target_type": "run_table",
            "target_table": "target_scratch",
            "write_mode": "overwrite",
            "overwrite_rule": "all",
            "selected_field_count": 1,
            "mapping_count": 0,
            "source_row_count": 1,
            "enable_write": "true",
            "backup_before_write": "false",
            "actual_write": "true",
            "affected_rows": 1,
            "skipped_rows": 0,
            "warning_count": 0,
            "warnings": "",
            "target_table_ref_id": written_ref.table_ref_id,
            "selected_fields": "row_id",
            "target_fields": "row_id",
            "skipped_reason": "",
        }
    ]
    assert provider.read_rows(written_ref, offset=0, limit=10) == [
        {"row_id": 1},
    ]


def test_write_selected_columns_node_can_append_to_memory_table_target(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider, memory_provider = (
        make_executor_with_memory_provider(tmp_path)
    )
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])

    first_result = executor.execute(
        make_task(
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            node_run_id="node-run-write-selected-first",
            node_instance_id="write_selected_first",
            input_refs=[input_ref.table_ref_id],
            config={
                "selected_fields": ["amount"],
                "target_type": "memory_table",
                "target_table": "target_memory",
                "field_name_mode": "mapping",
                "field_mappings": [
                    {"source_field": "amount", "target_field": "total"},
                ],
                "enable_write": True,
            },
        )
    )
    second_result = executor.execute(
        make_task(
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            node_run_id="node-run-write-selected-second",
            node_instance_id="write_selected_second",
            input_refs=[input_ref.table_ref_id],
            config={
                "selected_fields": ["amount"],
                "target_type": "memory_table",
                "target_table": "target_memory",
                "write_mode": "append",
                "field_name_mode": "mapping",
                "field_mappings": [
                    {"source_field": "amount", "target_field": "total"},
                ],
                "enable_write": True,
            },
        )
    )

    assert first_result.status == NodeResultStatus.SUCCEEDED
    assert second_result.status == NodeResultStatus.SUCCEEDED
    first_written_ref = registry.get(first_result.output_refs[1])
    second_status_ref = registry.get(second_result.output_refs[0])
    second_written_ref = registry.get(second_result.output_refs[1])
    assert first_written_ref.storage_kind == TableStorageKind.MEMORY
    assert second_written_ref.storage_kind == TableStorageKind.MEMORY
    assert second_written_ref.role == TableRole.AUXILIARY
    assert memory_provider.read_rows(
        second_written_ref,
        offset=0,
        limit=10,
    ) == [
        {"total": 1.0},
        {"total": 2.0},
        {"total": 1.0},
        {"total": 2.0},
    ]
    assert provider.read_rows(second_status_ref, offset=0, limit=10) == [
        {
            "status": "written",
            "source_type": "current_table",
            "target_type": "memory_table",
            "target_table": "target_memory",
            "write_mode": "append",
            "overwrite_rule": "all",
            "selected_field_count": 1,
            "mapping_count": 1,
            "source_row_count": 2,
            "enable_write": "true",
            "backup_before_write": "false",
            "actual_write": "true",
            "affected_rows": 2,
            "skipped_rows": 0,
            "warning_count": 0,
            "warnings": "",
            "target_table_ref_id": second_written_ref.table_ref_id,
            "selected_fields": "amount",
            "target_fields": "total",
            "skipped_reason": "",
        }
    ]


def test_write_selected_columns_node_rejects_create_when_target_exists(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    first_result = executor.execute(
        make_task(
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            node_run_id="node-run-write-selected-first",
            node_instance_id="write_selected_first",
            input_refs=[input_ref.table_ref_id],
            config={
                "selected_fields": ["row_id"],
                "target_transit_table": "target_scratch",
                "write_mode": "create",
                "enable_write": True,
            },
        )
    )

    second_result = executor.execute(
        make_task(
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            node_run_id="node-run-write-selected-second",
            node_instance_id="write_selected_second",
            input_refs=[input_ref.table_ref_id],
            config={
                "selected_fields": ["row_id"],
                "target_transit_table": "target_scratch",
                "write_mode": "create",
                "enable_write": True,
            },
        )
    )

    assert first_result.status == NodeResultStatus.SUCCEEDED
    assert second_result.status == NodeResultStatus.FAILED
    assert second_result.error is not None
    assert second_result.error["error_code"] == "VALIDATION_ERROR"
    assert "target table already exists" in second_result.error["message"]


def test_write_selected_columns_node_rejects_append_schema_mismatch(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    first_result = executor.execute(
        make_task(
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            node_run_id="node-run-write-selected-first",
            node_instance_id="write_selected_first",
            input_refs=[input_ref.table_ref_id],
            config={
                "selected_fields": ["amount"],
                "target_transit_table": "target_scratch",
                "field_name_mode": "mapping",
                "field_mappings": [
                    {"source_field": "amount", "target_field": "value"},
                ],
                "enable_write": True,
            },
        )
    )

    second_result = executor.execute(
        make_task(
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            node_run_id="node-run-write-selected-second",
            node_instance_id="write_selected_second",
            input_refs=[input_ref.table_ref_id],
            config={
                "selected_fields": ["row_id"],
                "target_transit_table": "target_scratch",
                "write_mode": "append",
                "field_name_mode": "mapping",
                "field_mappings": [
                    {"source_field": "row_id", "target_field": "value"},
                ],
                "enable_write": True,
            },
        )
    )

    assert first_result.status == NodeResultStatus.SUCCEEDED
    assert second_result.status == NodeResultStatus.FAILED
    assert second_result.error is not None
    assert second_result.error["error_code"] == "VALIDATION_ERROR"
    assert "append target schema does not match" in second_result.error["message"]


def test_write_selected_columns_node_returns_validation_error_for_missing_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id"], "seed": 0},
        )
    )

    result = executor.execute(
        make_task(
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            node_run_id="node-run-write-selected",
            node_instance_id="write_selected",
            input_refs=generate_result.output_refs,
            config={
                "selected_fields": ["missing"],
                "target_transit_table": "target_scratch",
            },
        )
    )

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Fields do not exist: missing" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_write_back_table_node_outputs_writeback_status_table(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 3,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    writeback_task = make_task(
        node_type=WRITE_BACK_TABLE_NODE_TYPE,
        node_run_id="node-run-writeback",
        node_instance_id="writeback",
        input_refs=[input_ref.table_ref_id],
        config={
            "target_table": "orders",
            "match_rules": [
                {
                    "source_field": "row_id",
                    "target_field": "id",
                    "operator": "equals",
                }
            ],
            "field_mappings": [
                {"source_field": "amount", "target_field": "total"},
                {"source_field": "label", "target_field": "caption"},
            ],
            "overwrite_policy": "empty_only",
            "source_empty_policy": "skip",
            "no_match_policy": "insert",
            "multi_match_policy": "skip",
            "duplicate_target_policy": "first",
            "enable_write": False,
            "backup_before_write": True,
            "output_preview_table": True,
        },
    )

    writeback_result = executor.execute(writeback_task)

    assert writeback_result.status == NodeResultStatus.SUCCEEDED
    assert len(writeback_result.output_refs) == 1
    status_ref = registry.get(writeback_result.output_refs[0])
    assert status_ref.lifecycle_status == LifecycleStatus.PUBLISHED
    assert status_ref.logical_table_id == "writeback_output"
    assert provider.read_rows(status_ref, offset=0, limit=10) == [
        {
            "status": "skipped",
            "writeback_direction": "source_to_target",
            "source_table": "generate_output",
            "target_type": "sqlite",
            "target_table": "orders",
            "write_mode": "overwrite",
            "use_match_rules": "true",
            "match_rule_count": 1,
            "field_mapping_count": 2,
            "source_row_count": 3,
            "enable_write": "false",
            "backup_before_write": "true",
            "output_preview_table": "true",
            "actual_write": "false",
            "affected_rows": 0,
            "skipped_rows": 3,
            "warning_count": 0,
            "warnings": "",
            "target_table_ref_id": "",
            "overwrite_policy": "empty_only",
            "source_empty_policy": "skip",
            "no_match_policy": "insert",
            "multi_match_policy": "skip",
            "duplicate_target_policy": "first",
            "match_fields": "row_id->id",
            "mapped_fields": "amount->total,label->caption",
            "skipped_reason": "enable_write is false",
        }
    ]
    assert provider.count_rows(input_ref) == 3


def test_write_back_table_node_outputs_preview_only_when_write_enabled(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])

    writeback_result = executor.execute(
        make_task(
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
            node_run_id="node-run-writeback",
            node_instance_id="writeback",
            input_refs=[input_ref.table_ref_id],
            config={
                "target_table": "orders",
                "use_match_rules": False,
                "field_mappings": [
                    {"source_field": "amount", "target_field": "total"},
                ],
                "enable_write": True,
                "output_preview_table": False,
            },
        )
    )

    assert writeback_result.status == NodeResultStatus.SUCCEEDED
    status_ref = registry.get(writeback_result.output_refs[0])
    rows = provider.read_rows(status_ref, offset=0, limit=10)
    assert rows[0]["use_match_rules"] == "false"
    assert rows[0]["match_rule_count"] == 0
    assert rows[0]["enable_write"] == "true"
    assert rows[0]["output_preview_table"] == "false"
    assert rows[0]["actual_write"] == "false"
    assert rows[0]["affected_rows"] == 0
    assert rows[0]["skipped_rows"] == 1
    assert rows[0]["warning_count"] == 0
    assert rows[0]["warnings"] == ""
    assert rows[0]["target_table_ref_id"] == ""
    assert rows[0]["skipped_reason"] == "sqlite target writes are not implemented"


def test_write_back_table_node_skips_target_to_source_runtime_write(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])

    writeback_result = executor.execute(
        make_task(
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
            node_run_id="node-run-writeback-direction",
            node_instance_id="writeback_direction",
            input_refs=[input_ref.table_ref_id],
            config={
                "writeback_direction": "target_to_source",
                "target_type": "run_table",
                "target_table": "direction_target",
                "use_match_rules": False,
                "field_mappings": [
                    {"source_field": "amount", "target_field": "total"},
                ],
                "enable_write": True,
            },
        )
    )

    assert writeback_result.status == NodeResultStatus.SUCCEEDED
    assert len(writeback_result.output_refs) == 1
    status_ref = registry.get(writeback_result.output_refs[0])
    rows = provider.read_rows(status_ref, offset=0, limit=10)
    assert rows[0]["writeback_direction"] == "target_to_source"
    assert rows[0]["target_type"] == "run_table"
    assert rows[0]["actual_write"] == "false"
    assert rows[0]["target_table_ref_id"] == ""
    assert rows[0]["skipped_reason"] == (
        "target_to_source runtime writes are not implemented"
    )
    assert [
        table_ref.logical_table_id
        for table_ref in registry.list_by_workflow_run("run-1")
    ].count("direction_target") == 0


def test_write_back_table_node_writes_run_table_when_enabled(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])

    writeback_result = executor.execute(
        make_task(
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
            node_run_id="node-run-writeback",
            node_instance_id="writeback",
            input_refs=[input_ref.table_ref_id],
            config={
                "target_type": "run_table",
                "target_table": "orders_projection",
                "use_match_rules": False,
                "field_mappings": [
                    {"source_field": "row_id", "target_field": "id"},
                    {"source_field": "amount", "target_field": "total"},
                ],
                "enable_write": True,
            },
        )
    )

    assert writeback_result.status == NodeResultStatus.SUCCEEDED
    assert len(writeback_result.output_refs) == 2
    status_ref = registry.get(writeback_result.output_refs[0])
    target_ref = registry.get(writeback_result.output_refs[1])
    assert target_ref.logical_table_id == "orders_projection"
    assert target_ref.role == TableRole.AUXILIARY
    assert target_ref.storage_kind == TableStorageKind.RUNTIME_SQL
    assert provider.read_rows(status_ref, offset=0, limit=10) == [
        {
            "status": "written",
            "writeback_direction": "source_to_target",
            "source_table": "generate_output",
            "target_type": "run_table",
            "target_table": "orders_projection",
            "write_mode": "overwrite",
            "use_match_rules": "false",
            "match_rule_count": 0,
            "field_mapping_count": 2,
            "source_row_count": 2,
            "enable_write": "true",
            "backup_before_write": "false",
            "output_preview_table": "true",
            "actual_write": "true",
            "affected_rows": 2,
            "skipped_rows": 0,
            "warning_count": 0,
            "warnings": "",
            "target_table_ref_id": target_ref.table_ref_id,
            "overwrite_policy": "overwrite",
            "source_empty_policy": "skip",
            "no_match_policy": "skip",
            "multi_match_policy": "error",
            "duplicate_target_policy": "error",
            "match_fields": "",
            "mapped_fields": "row_id->id,amount->total",
            "skipped_reason": "",
        }
    ]
    assert provider.read_rows(target_ref, offset=0, limit=10) == [
        {"id": 1, "total": 1.0},
        {"id": 2, "total": 2.0},
    ]


def test_write_back_table_node_can_append_to_memory_table_target(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider, memory_provider = (
        make_executor_with_memory_provider(tmp_path)
    )
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])

    first_result = executor.execute(
        make_task(
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
            node_run_id="node-run-writeback-first",
            node_instance_id="writeback_first",
            input_refs=[input_ref.table_ref_id],
            config={
                "target_type": "memory_table",
                "target_table": "orders_memory",
                "use_match_rules": False,
                "field_mappings": [
                    {"source_field": "amount", "target_field": "total"},
                ],
                "enable_write": True,
            },
        )
    )
    second_result = executor.execute(
        make_task(
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
            node_run_id="node-run-writeback-second",
            node_instance_id="writeback_second",
            input_refs=[input_ref.table_ref_id],
            config={
                "target_type": "memory_table",
                "target_table": "orders_memory",
                "write_mode": "append",
                "use_match_rules": False,
                "field_mappings": [
                    {"source_field": "amount", "target_field": "total"},
                ],
                "enable_write": True,
            },
        )
    )

    assert first_result.status == NodeResultStatus.SUCCEEDED
    assert second_result.status == NodeResultStatus.SUCCEEDED
    first_target_ref = registry.get(first_result.output_refs[1])
    second_status_ref = registry.get(second_result.output_refs[0])
    second_target_ref = registry.get(second_result.output_refs[1])
    assert first_target_ref.storage_kind == TableStorageKind.MEMORY
    assert second_target_ref.storage_kind == TableStorageKind.MEMORY
    assert memory_provider.read_rows(
        second_target_ref,
        offset=0,
        limit=10,
    ) == [
        {"total": 1.0},
        {"total": 2.0},
        {"total": 1.0},
        {"total": 2.0},
    ]
    rows = _provider.read_rows(second_status_ref, offset=0, limit=10)
    assert rows[0]["status"] == "written"
    assert rows[0]["target_type"] == "memory_table"
    assert rows[0]["write_mode"] == "append"
    assert rows[0]["actual_write"] == "true"
    assert rows[0]["affected_rows"] == 2
    assert rows[0]["skipped_rows"] == 0
    assert rows[0]["target_table_ref_id"] == second_target_ref.table_ref_id


def test_write_back_table_node_skips_empty_source_rows_for_runtime_target(
    tmp_path: Path,
) -> None:
    executor, _store, registry, provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 3, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    rows = provider.read_rows(input_ref, offset=0, limit=10)
    rows[1] = {"row_id": 2, "amount": ""}
    staged_ref = provider.create_staging_table(
        workflow_run_id="run-1",
        node_run_id="node-run-custom-writeback-input",
        output_name="writeback_input",
        schema=input_ref.schema,
    )
    provider.insert_rows(staged_ref, rows)
    registry.register_staging(staged_ref)
    custom_input_ref = registry.publish(staged_ref.table_ref_id)

    writeback_result = executor.execute(
        make_task(
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
            node_run_id="node-run-writeback",
            node_instance_id="writeback",
            input_refs=[custom_input_ref.table_ref_id],
            config={
                "target_type": "run_table",
                "target_table": "orders_projection",
                "use_match_rules": False,
                "field_mappings": [
                    {"source_field": "amount", "target_field": "total"},
                ],
                "source_empty_policy": "skip",
                "enable_write": True,
            },
        )
    )

    assert writeback_result.status == NodeResultStatus.SUCCEEDED
    status_ref = registry.get(writeback_result.output_refs[0])
    target_ref = registry.get(writeback_result.output_refs[1])
    status_rows = provider.read_rows(status_ref, offset=0, limit=10)
    assert status_rows[0]["affected_rows"] == 2
    assert status_rows[0]["skipped_rows"] == 1
    assert provider.read_rows(target_ref, offset=0, limit=10) == [
        {"total": 1.0},
        {"total": 3.0},
    ]


def test_write_back_table_node_rejects_create_when_target_exists(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    first_result = executor.execute(
        make_task(
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
            node_run_id="node-run-writeback-first",
            node_instance_id="writeback_first",
            input_refs=[input_ref.table_ref_id],
            config={
                "target_type": "run_table",
                "target_table": "orders_projection",
                "write_mode": "create",
                "use_match_rules": False,
                "field_mappings": [
                    {"source_field": "amount", "target_field": "total"},
                ],
                "enable_write": True,
            },
        )
    )

    second_result = executor.execute(
        make_task(
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
            node_run_id="node-run-writeback-second",
            node_instance_id="writeback_second",
            input_refs=[input_ref.table_ref_id],
            config={
                "target_type": "run_table",
                "target_table": "orders_projection",
                "write_mode": "create",
                "use_match_rules": False,
                "field_mappings": [
                    {"source_field": "amount", "target_field": "total"},
                ],
                "enable_write": True,
            },
        )
    )

    assert first_result.status == NodeResultStatus.SUCCEEDED
    assert second_result.status == NodeResultStatus.FAILED
    assert second_result.error is not None
    assert second_result.error["error_code"] == "VALIDATION_ERROR"
    assert "target table already exists" in second_result.error["message"]


def test_write_back_table_node_rejects_append_schema_mismatch(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    first_result = executor.execute(
        make_task(
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
            node_run_id="node-run-writeback-first",
            node_instance_id="writeback_first",
            input_refs=[input_ref.table_ref_id],
            config={
                "target_type": "run_table",
                "target_table": "orders_projection",
                "use_match_rules": False,
                "field_mappings": [
                    {"source_field": "amount", "target_field": "value"},
                ],
                "enable_write": True,
            },
        )
    )

    second_result = executor.execute(
        make_task(
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
            node_run_id="node-run-writeback-second",
            node_instance_id="writeback_second",
            input_refs=[input_ref.table_ref_id],
            config={
                "target_type": "run_table",
                "target_table": "orders_projection",
                "write_mode": "append",
                "use_match_rules": False,
                "field_mappings": [
                    {"source_field": "row_id", "target_field": "value"},
                ],
                "enable_write": True,
            },
        )
    )

    assert first_result.status == NodeResultStatus.SUCCEEDED
    assert second_result.status == NodeResultStatus.FAILED
    assert second_result.error is not None
    assert second_result.error["error_code"] == "VALIDATION_ERROR"
    assert "append target schema does not match" in second_result.error["message"]


def test_write_back_table_node_returns_validation_error_for_missing_mapping_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id"], "seed": 0},
        )
    )

    result = executor.execute(
        make_task(
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
            node_run_id="node-run-writeback",
            node_instance_id="writeback",
            input_refs=generate_result.output_refs,
            config={
                "target_table": "orders",
                "use_match_rules": False,
                "field_mappings": [
                    {"source_field": "missing", "target_field": "total"},
                ],
            },
        )
    )

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field does not exist: missing" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_add_columns_node_returns_validation_error_for_duplicate_column(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    add_task = make_task(
        node_type=ADD_COLUMNS_NODE_TYPE,
        node_run_id="node-run-add-column",
        node_instance_id="add_column",
        input_refs=generate_result.output_refs,
        config={
            "column_name": "amount",
            "default_value": "new",
            "data_type": "TEXT",
        },
    )

    result = executor.execute(add_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field already exists" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_filter_rows_node_returns_validation_error_for_missing_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    filter_task = make_task(
        node_type=FILTER_ROWS_NODE_TYPE,
        node_run_id="node-run-filter",
        node_instance_id="filter",
        input_refs=generate_result.output_refs,
        config={"field": "missing", "operator": "EQ", "value": 1},
    )

    result = executor.execute(filter_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field does not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_list_files_node_returns_validation_error_for_missing_directory(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    task = make_task(
        node_type=LIST_FILES_NODE_TYPE,
        node_run_id="node-run-list-files",
        node_instance_id="list_files",
        config={
            "directory": str(tmp_path / "missing"),
        },
    )

    result = executor.execute(task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Directory does not exist" in result.error["message"]
    assert registry.list_by_workflow_run("run-1") == []


def test_batch_rename_files_node_returns_validation_error_for_missing_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["path"], "seed": 0},
        )
    )

    result = executor.execute(
        make_task(
            node_type=BATCH_RENAME_FILES_NODE_TYPE,
            node_run_id="node-run-batch-rename",
            node_instance_id="batch_rename",
            input_refs=generate_result.output_refs,
            config={
                "path_field": "path",
                "new_name_field": "missing",
            },
        )
    )

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Fields do not exist: missing" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_plugin_node_returns_validation_error_for_missing_plugin_id(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    task = make_task(
        node_type=PLUGIN_NODE_TYPE,
        node_run_id="node-run-plugin",
        node_instance_id="plugin",
        config={},
    )

    result = executor.execute(task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "PluginNode config.plugin_id is required" in result.error["message"]
    assert registry.list_by_workflow_run("run-1") == []


def test_delete_columns_node_returns_validation_error_for_missing_column(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    delete_task = make_task(
        node_type=DELETE_COLUMNS_NODE_TYPE,
        node_run_id="node-run-delete-columns",
        node_instance_id="delete_columns",
        input_refs=generate_result.output_refs,
        config={"columns": ["missing"]},
    )

    result = executor.execute(delete_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Fields do not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_delete_rows_node_returns_validation_error_for_row_out_of_range(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    delete_task = make_task(
        node_type=DELETE_ROWS_NODE_TYPE,
        node_run_id="node-run-delete-rows",
        node_instance_id="delete_rows",
        input_refs=generate_result.output_refs,
        config={"delete_mode": "row_numbers", "row_spec": [3]},
    )

    result = executor.execute(delete_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "out of range" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_delete_rows_node_returns_validation_error_for_missing_condition_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    delete_task = make_task(
        node_type=DELETE_ROWS_NODE_TYPE,
        node_run_id="node-run-delete-rows",
        node_instance_id="delete_rows",
        input_refs=generate_result.output_refs,
        config={
            "delete_mode": "condition",
            "condition_field": "missing",
            "condition_op": "EQ",
            "condition_value": 1,
        },
    )

    result = executor.execute(delete_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field does not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_copy_rows_node_returns_validation_error_for_source_row_out_of_range(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    copy_task = make_task(
        node_type=COPY_ROWS_NODE_TYPE,
        node_run_id="node-run-copy-rows",
        node_instance_id="copy_rows",
        input_refs=generate_result.output_refs,
        config={"source_row": 3, "copy_count": 1},
    )

    result = executor.execute(copy_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "source_row is out of range" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_copy_rows_node_returns_validation_error_when_output_exceeds_limit(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    copy_task = make_task(
        node_type=COPY_ROWS_NODE_TYPE,
        node_run_id="node-run-copy-rows",
        node_instance_id="copy_rows",
        input_refs=generate_result.output_refs,
        config={
            "source_row": 1,
            "copy_count": 2,
            "max_output_rows": 3,
        },
    )

    result = executor.execute(copy_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "max_output_rows" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_deduplicate_rows_node_returns_validation_error_for_missing_key_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    dedupe_task = make_task(
        node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        node_run_id="node-run-deduplicate-rows",
        node_instance_id="deduplicate_rows",
        input_refs=generate_result.output_refs,
        config={"key_fields": ["missing"]},
    )

    result = executor.execute(dedupe_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Fields do not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_deduplicate_rows_node_returns_validation_error_for_marker_field_conflict(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "category", "_duplicate_status"],
                "seed": 0,
            },
        )
    )
    dedupe_task = make_task(
        node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        node_run_id="node-run-deduplicate-rows",
        node_instance_id="deduplicate_rows",
        input_refs=generate_result.output_refs,
        config={
            "key_fields": ["category"],
            "output_mode": "mark",
        },
    )

    result = executor.execute(dedupe_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Fields already exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_advanced_filter_rows_node_returns_validation_error_for_missing_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    filter_task = make_task(
        node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
        node_run_id="node-run-advanced-filter",
        node_instance_id="advanced_filter",
        input_refs=generate_result.output_refs,
        config={
            "conditions": [
                {"field": "missing", "operator": "EQ", "value": 1},
            ],
        },
    )

    result = executor.execute(filter_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field does not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_extract_text_node_returns_validation_error_for_missing_source_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "source"], "seed": 0},
        )
    )
    extract_task = make_task(
        node_type=EXTRACT_TEXT_NODE_TYPE,
        node_run_id="node-run-extract-text",
        node_instance_id="extract_text",
        input_refs=generate_result.output_refs,
        config={
            "source_field": "missing",
            "method": "regex",
            "regex_pattern": r"(\d+)",
            "new_field": "result",
        },
    )

    result = executor.execute(extract_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field does not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_lookup_matched_field_name_node_requires_lookup_input_ref(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "source"], "seed": 0},
        )
    )
    lookup_task = make_task(
        node_type=LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
        node_run_id="node-run-lookup-matched-field",
        node_instance_id="lookup_matched_field",
        input_refs=generate_result.output_refs,
        config={"source_field": "source", "lookup_fields": ["source"]},
    )

    result = executor.execute(lookup_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "requires main and lookup input_refs" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_merge_columns_node_returns_validation_error_for_missing_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "first"], "seed": 0},
        )
    )
    merge_task = make_task(
        node_type=MERGE_COLUMNS_NODE_TYPE,
        node_run_id="node-run-merge-columns",
        node_instance_id="merge_columns",
        input_refs=generate_result.output_refs,
        config={"fields": ["first", "missing"], "output_field": "merged"},
    )

    result = executor.execute(merge_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Fields do not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_numeric_column_operation_node_returns_validation_error_for_missing_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    numeric_task = make_task(
        node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        node_run_id="node-run-numeric-column",
        node_instance_id="numeric_column",
        input_refs=generate_result.output_refs,
        config={"target_field": "missing", "operation": "add", "operand_value": 1},
    )

    result = executor.execute(numeric_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field does not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_add_current_datetime_column_node_returns_validation_error_for_conflict(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    datetime_task = make_task(
        node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
        node_run_id="node-run-current-datetime",
        node_instance_id="current_datetime",
        input_refs=generate_result.output_refs,
        config={"new_field": "amount"},
    )

    result = executor.execute(datetime_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field already exists" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_parse_datetime_node_returns_validation_error_for_missing_source_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "raw_date"], "seed": 0},
        )
    )
    parse_task = make_task(
        node_type=PARSE_DATETIME_NODE_TYPE,
        node_run_id="node-run-parse-datetime",
        node_instance_id="parse_datetime",
        input_refs=generate_result.output_refs,
        config={"source_field": "missing"},
    )

    result = executor.execute(parse_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field does not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_condition_flag_node_returns_validation_errors_for_invalid_config(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    input_ref = registry.get(generate_result.output_refs[0])
    invalid_tasks = [
        (
            {
                "condition_type": "field_value",
                "field": "missing",
                "operator": "EQ",
                "value": 1,
            },
            "Field does not exist: missing",
        ),
        (
            {
                "condition_type": "field_value",
                "field": "amount",
                "operator": "EQ",
            },
            "ConditionFlagNode config.value is required",
        ),
        (
            {
                "condition_type": "field_value",
                "field": "amount",
                "operator": "BAD",
                "value": 1,
            },
            "Unsupported ConditionFlagNode operator",
        ),
    ]

    for index, (config, expected_message) in enumerate(invalid_tasks, start=1):
        result = executor.execute(
            make_task(
                node_type=CONDITION_FLAG_NODE_TYPE,
                node_run_id=f"node-run-condition-invalid-{index}",
                node_instance_id=f"condition_invalid_{index}",
                input_refs=[input_ref.table_ref_id],
                config=config,
            )
        )

        assert result.status == NodeResultStatus.FAILED
        assert result.output_refs == []
        assert result.error is not None
        assert result.error["error_code"] == "VALIDATION_ERROR"
        assert expected_message in result.error["message"]


def test_copy_column_node_returns_validation_error_for_missing_source_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    copy_task = make_task(
        node_type=COPY_COLUMN_NODE_TYPE,
        node_run_id="node-run-copy-column",
        node_instance_id="copy_column",
        input_refs=generate_result.output_refs,
        config={
            "source_field": "missing",
            "output_mode": "new_field",
            "new_field": "missing_copy",
        },
    )

    result = executor.execute(copy_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field does not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_reorder_columns_node_returns_validation_error_for_missing_column(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    reorder_task = make_task(
        node_type=REORDER_COLUMNS_NODE_TYPE,
        node_run_id="node-run-reorder-columns",
        node_instance_id="reorder_columns",
        input_refs=generate_result.output_refs,
        config={"order": ["missing"]},
    )

    result = executor.execute(reorder_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Fields do not exist" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_rename_columns_node_returns_validation_error_for_duplicate_output(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 1, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    rename_task = make_task(
        node_type=RENAME_COLUMNS_NODE_TYPE,
        node_run_id="node-run-rename-columns",
        node_instance_id="rename_columns",
        input_refs=generate_result.output_refs,
        config={
            "mappings": [
                {"source_field": "amount", "target_field": "row_id"},
            ],
        },
    )

    result = executor.execute(rename_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "output fields are duplicated" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_fill_cells_node_returns_validation_error_for_start_row_out_of_range(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "label"], "seed": 0},
        )
    )
    fill_task = make_task(
        node_type=FILL_CELLS_NODE_TYPE,
        node_run_id="node-run-fill-cells",
        node_instance_id="fill_cells",
        input_refs=generate_result.output_refs,
        config={
            "target_field": "label",
            "manual_value": "filled",
            "start_row": 3,
        },
    )

    result = executor.execute(fill_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "start_row is out of range" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_fill_range_node_returns_validation_error_when_range_exceeds_limit(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={
                "rows": 2,
                "columns": ["row_id", "amount", "label"],
                "seed": 0,
            },
        )
    )
    fill_task = make_task(
        node_type=FILL_RANGE_NODE_TYPE,
        node_run_id="node-run-fill-range",
        node_instance_id="fill_range",
        input_refs=generate_result.output_refs,
        config={
            "start_field": "amount",
            "end_field": "label",
            "manual_value": "filled",
            "max_cells": 3,
        },
    )

    result = executor.execute(fill_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "target range exceeds max_cells" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_fill_sequence_node_returns_validation_error_for_missing_target_field(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    fill_task = make_task(
        node_type=FILL_SEQUENCE_NODE_TYPE,
        node_run_id="node-run-fill-sequence",
        node_instance_id="fill_sequence",
        input_refs=generate_result.output_refs,
        config={"target_field": "missing"},
    )

    result = executor.execute(fill_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "Field does not exist: missing" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2


def test_unpivot_rows_node_returns_validation_error_for_output_field_conflict(
    tmp_path: Path,
) -> None:
    executor, _store, registry, _provider = make_executor(tmp_path)
    generate_result = executor.execute(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_run_id="node-run-generate",
            node_instance_id="generate",
            config={"rows": 2, "columns": ["row_id", "amount"], "seed": 0},
        )
    )
    unpivot_task = make_task(
        node_type=UNPIVOT_ROWS_NODE_TYPE,
        node_run_id="node-run-unpivot-rows",
        node_instance_id="unpivot_rows",
        input_refs=generate_result.output_refs,
        config={
            "value_fields": ["amount"],
            "keep_fields": ["row_id"],
            "output_value_field": "row_id",
        },
    )

    result = executor.execute(unpivot_task)

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert "output fields conflict with keep_fields" in result.error["message"]
    assert len(registry.list_by_workflow_run("run-1")) == 2
