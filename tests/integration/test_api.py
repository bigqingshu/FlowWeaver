from __future__ import annotations

import queue
import threading
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from flowweaver.api.app import create_app
from flowweaver.common.config import EngineConfig
from flowweaver.common.time import utc_now
from flowweaver.engine.bootstrap import EngineHostBootstrap
from flowweaver.engine.event_router import EventRouter
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.engine.service_container import ServiceContainer
from flowweaver.engine.supervisor import Supervisor
from flowweaver.engine.table_lease_manager import TableLeaseManager
from flowweaver.nodes.registry import NodeDefinitionSpec, NodePortSpec, NodeRegistry
from flowweaver.protocols.enums import (
    EventType,
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
    WorkflowRunCompletionReason,
    WorkflowRunStatus,
)
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

TOKEN = "test-token"


def valid_definition() -> dict:
    return {"schema_version": "1.0", "nodes": [], "connections": []}


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def make_client(tmp_path: Path) -> tuple[TestClient, RuntimeStore, ServiceContainer]:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    store = RuntimeStore.from_sqlite_path(database_path)
    config = EngineConfig(
        data_dir=tmp_path / "runtime",
        local_api_token=TOKEN,
        enforce_single_instance=False,
        workflow_process_heartbeat_interval_seconds=0,
        supervisor_maintenance_interval_seconds=0.05,
    )
    node_registry = NodeRegistry()
    node_registry.register(
        NodeDefinitionSpec(
            node_type="core.source",
            node_version="1.0",
            display_name="Source",
            output_ports=(NodePortSpec("out"),),
        )
    )
    node_registry.register(
        NodeDefinitionSpec(
            node_type="core.transform",
            node_version="1.0",
            display_name="Transform",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
        )
    )
    event_router = EventRouter(store)
    container = ServiceContainer(
        config=config,
        runtime_store=store,
        event_router=event_router,
        table_lease_manager=TableLeaseManager(store.engine),
        supervisor=Supervisor(
            config=config,
            runtime_store=store,
            event_router=event_router,
        ),
        node_registry=node_registry,
    )
    return TestClient(create_app(container)), store, container


def make_default_registry_client(tmp_path: Path) -> tuple[TestClient, ServiceContainer]:
    data_dir = tmp_path / "runtime"
    container = EngineHostBootstrap(
        EngineConfig(
            data_dir=data_dir,
            local_api_token=TOKEN,
            enforce_single_instance=False,
            workflow_process_heartbeat_interval_seconds=0,
            supervisor_maintenance_interval_seconds=0.05,
        )
    ).initialize()
    return TestClient(create_app(container)), container


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def response_data(response):
    payload = response.json()
    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["request_id"]
    return payload["data"]


def response_error(response):
    payload = response.json()
    assert payload["ok"] is False
    assert payload["data"] is None
    assert payload["request_id"]
    return payload["error"]


def make_api_table_ref(
    *,
    table_ref_id: str,
    workflow_run_id: str,
    node_run_id: str,
    logical_table_id: str = "orders",
    version: int = 1,
) -> TableRefModel:
    return TableRefModel(
        table_ref_id=table_ref_id,
        role=TableRole.CURRENT,
        storage_kind=TableStorageKind.RUNTIME_SQL,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.PUBLISHED_IMMUTABLE,
        provider_id="sqlite_runtime",
        resource_profile_id=None,
        mount_id=None,
        logical_table_id=logical_table_id,
        opaque_handle={
            "database_path": "runtime/run.db",
            "table_name": f"{logical_table_id}_v{version}",
        },
        schema=[
            FieldSchemaModel(
                field_id=f"{logical_table_id}-amount",
                name="amount",
                data_type="FLOAT",
                nullable=False,
                ordinal=0,
            )
        ],
        schema_fingerprint=f"{logical_table_id}-fingerprint-{version}",
        version=version,
        capabilities={"READ"},
        lifecycle_status=LifecycleStatus.PUBLISHED,
        created_by_workflow_run_id=workflow_run_id,
        created_by_node_run_id=node_run_id,
        created_at=utc_now(),
    )


def test_health_returns_uniform_response(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    response = client.get("/api/v1/health", headers={"x-request-id": "request-1"})

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {"status": "ok"},
        "error": None,
        "request_id": "request-1",
    }


def test_workflow_crud_api(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    created = response_data(
        client.post(
            "/api/v1/workflows",
            json={"name": "API workflow", "definition": valid_definition()},
            headers=auth_headers(),
        )
    )
    workflow_id = created["workflow_id"]

    assert created["name"] == "API workflow"
    assert created["version"] == 1
    assert created["revision_id"]

    loaded = response_data(
        client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers())
    )
    listed = response_data(client.get("/api/v1/workflows", headers=auth_headers()))
    updated = response_data(
        client.put(
            f"/api/v1/workflows/{workflow_id}",
            json={
                "base_revision_id": created["revision_id"],
                "definition": {
                    "schema_version": "1.0",
                    "nodes": [],
                    "connections": [],
                    "outputs": [],
                }
            },
            headers=auth_headers(),
        )
    )
    revisions = response_data(
        client.get(
            f"/api/v1/workflows/{workflow_id}/revisions",
            headers=auth_headers(),
        )
    )
    first_revision = response_data(
        client.get(
            f"/api/v1/workflows/{workflow_id}/revisions/{created['revision_id']}",
            headers=auth_headers(),
        )
    )
    deleted = response_data(
        client.delete(f"/api/v1/workflows/{workflow_id}", headers=auth_headers())
    )

    assert loaded["workflow_id"] == workflow_id
    assert [item["workflow_id"] for item in listed] == [workflow_id]
    assert updated["version"] == 2
    assert updated["revision_id"] != created["revision_id"]
    assert [revision["version"] for revision in revisions] == [1, 2]
    assert first_revision["definition"] == valid_definition()
    assert deleted == {"workflow_id": workflow_id, "deleted": True}


def test_workflow_api_preserves_runtime_options(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)
    definition = valid_definition() | {
        "runtime_options": {
            "version": "1.0",
            "workflow": {
                "profile": "normal",
                "telemetry": {
                    "log_level": "INFO",
                    "event_level": "progress",
                    "progress_enabled": True,
                },
            },
            "node_overrides": {
                "source": {
                    "telemetry": {
                        "log_level": "DEBUG",
                    },
                },
            },
        },
    }

    created = response_data(
        client.post(
            "/api/v1/workflows",
            json={"name": "Runtime options workflow", "definition": definition},
            headers=auth_headers(),
        )
    )

    assert created["definition"]["runtime_options"]["workflow"]["profile"] == "normal"
    assert (
        created["definition"]["runtime_options"]["node_overrides"]["source"][
            "telemetry"
        ]["log_level"]
        == "DEBUG"
    )


def test_update_workflow_requires_base_revision_id(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)
    created = response_data(
        client.post(
            "/api/v1/workflows",
            json={"name": "API workflow", "definition": valid_definition()},
            headers=auth_headers(),
        )
    )

    response = client.put(
        f"/api/v1/workflows/{created['workflow_id']}",
        json={"definition": valid_definition()},
        headers=auth_headers(),
    )

    assert response.status_code == 400
    assert response_error(response)["error_code"] == "BASE_REVISION_REQUIRED"


def test_update_workflow_rejects_stale_base_revision_id(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)
    created = response_data(
        client.post(
            "/api/v1/workflows",
            json={"name": "API workflow", "definition": valid_definition()},
            headers=auth_headers(),
        )
    )
    workflow_id = created["workflow_id"]
    first_revision_id = created["revision_id"]
    updated = response_data(
        client.put(
            f"/api/v1/workflows/{workflow_id}",
            json={
                "base_revision_id": first_revision_id,
                "definition": valid_definition() | {"outputs": []},
            },
            headers=auth_headers(),
        )
    )

    response = client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={
            "base_revision_id": first_revision_id,
            "definition": valid_definition() | {"inputs": []},
        },
        headers=auth_headers(),
    )

    assert response.status_code == 409
    error = response_error(response)
    assert error["error_code"] == "WORKFLOW_REVISION_CONFLICT"
    assert error["details"] == {
        "workflow_id": workflow_id,
        "expected_revision_id": first_revision_id,
        "current_revision_id": updated["revision_id"],
    }


def test_node_definitions_api_returns_visible_builtin_nodes(tmp_path: Path) -> None:
    client, container = make_default_registry_client(tmp_path)
    try:
        response = client.get("/api/v1/node-definitions", headers=auth_headers())
        definitions = response_data(response)
    finally:
        container.close()

    by_type = {definition["node_type"]: definition for definition in definitions}

    assert set(by_type) == {
        "GenerateTestTableNode",
        "ListFilesNode",
        "BatchRenameFilesNode",
        "PluginNode",
        "FilterRowsNode",
        "AddColumnsNode",
        "DeleteColumnsNode",
        "CopyColumnNode",
        "ReorderColumnsNode",
        "RenameColumnsNode",
        "FillCellsNode",
        "FillRangeNode",
        "FillSequenceNode",
        "ReplaceTextNode",
        "DeleteRowsNode",
        "CopyRowsNode",
        "UnpivotRowsNode",
        "DeduplicateRowsNode",
        "AdvancedFilterRowsNode",
        "ExtractTextNode",
        "LookupMatchedFieldNameNode",
        "MergeColumnsNode",
        "NumericColumnOperationNode",
        "AddCurrentDateTimeColumnNode",
        "ParseDateTimeNode",
        "ConditionFlagNode",
        "JumpAnchorNode",
        "UnconditionalJumpNode",
        "SaveMemoryTableNode",
        "SaveRunTableNode",
        "WriteSelectedColumnsNode",
        "WriteBackTableNode",
        "PublishSharedTablesNode",
        "ReadSharedTablesNode",
        "SqlMappingNode",
    }
    assert "DelayTestNode" not in by_type
    assert "FaultTestNode" not in by_type
    assert by_type["GenerateTestTableNode"]["output_ports"] == [
        {"name": "out", "required": False}
    ]
    assert by_type["ListFilesNode"]["output_ports"] == [
        {"name": "out", "required": False}
    ]
    assert by_type["BatchRenameFilesNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["BatchRenameFilesNode"]["output_ports"] == [
        {"name": "status", "required": False}
    ]
    assert by_type["PluginNode"]["input_ports"] == [
        {"name": "in", "required": False}
    ]
    assert by_type["PluginNode"]["output_ports"] == [
        {"name": "status", "required": False}
    ]
    assert by_type["FilterRowsNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["DeleteColumnsNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["CopyColumnNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["ReorderColumnsNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["RenameColumnsNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["FillCellsNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["FillRangeNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["FillSequenceNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["ReplaceTextNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["DeleteRowsNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["CopyRowsNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["UnpivotRowsNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["DeduplicateRowsNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["AdvancedFilterRowsNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["ExtractTextNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["LookupMatchedFieldNameNode"]["input_ports"] == [
        {"name": "in", "required": True},
        {"name": "lookup", "required": True},
    ]
    assert by_type["MergeColumnsNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["NumericColumnOperationNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["AddCurrentDateTimeColumnNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["ParseDateTimeNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["ConditionFlagNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["ConditionFlagNode"]["output_ports"] == [
        {"name": "status", "required": False}
    ]
    assert by_type["JumpAnchorNode"]["input_ports"] == []
    assert by_type["JumpAnchorNode"]["output_ports"] == [
        {"name": "status", "required": False}
    ]
    assert by_type["UnconditionalJumpNode"]["input_ports"] == [
        {"name": "in", "required": False}
    ]
    assert by_type["UnconditionalJumpNode"]["output_ports"] == [
        {"name": "status", "required": False}
    ]
    assert by_type["SaveMemoryTableNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["SaveMemoryTableNode"]["output_ports"] == [
        {"name": "out", "required": False},
        {"name": "memory", "required": False},
    ]
    assert by_type["SaveRunTableNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["SaveRunTableNode"]["output_ports"] == [
        {"name": "out", "required": False},
        {"name": "transit", "required": False},
    ]
    assert by_type["WriteSelectedColumnsNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["WriteSelectedColumnsNode"]["output_ports"] == [
        {"name": "status", "required": False}
    ]
    assert by_type["WriteBackTableNode"]["input_ports"] == [
        {"name": "in", "required": True}
    ]
    assert by_type["WriteBackTableNode"]["output_ports"] == [
        {"name": "status", "required": False}
    ]
    assert by_type["GenerateTestTableNode"]["ui_visibility"] == "visible"
    assert all("implementation_ref" not in definition for definition in definitions)
    assert all(
        definition["config_schema_version"] == "1.0"
        for definition in definitions
    )
    assert all(
        definition["config_schema"]["type"] == "object"
        for definition in definitions
    )

    generate_properties = by_type["GenerateTestTableNode"]["config_schema"][
        "properties"
    ]
    assert generate_properties["rows"] == {
        "type": "integer",
        "title": "Rows",
        "required": True,
        "default": 3,
        "minimum": 0,
    }
    assert generate_properties["seed"]["default"] == 0
    assert generate_properties["columns"]["items"] == {"type": "string"}

    list_files_properties = by_type["ListFilesNode"]["config_schema"][
        "properties"
    ]
    assert list_files_properties["directory"]["required"] is True
    assert list_files_properties["recursive"]["default"] is False
    assert list_files_properties["include_files"]["default"] is True
    assert list_files_properties["include_dirs"]["default"] is False
    assert list_files_properties["include_hidden"]["default"] is False
    assert list_files_properties["extensions"]["items"] == {"type": "string"}
    assert list_files_properties["glob_pattern"]["default"] == "*"
    assert list_files_properties["max_files"]["minimum"] == 1

    batch_rename_properties = by_type["BatchRenameFilesNode"]["config_schema"][
        "properties"
    ]
    assert batch_rename_properties["path_field"]["required"] is True
    assert batch_rename_properties["new_name_field"]["required"] is True
    assert batch_rename_properties["name_value_type"]["enum"] == [
        "file_name",
        "full_path",
    ]
    assert batch_rename_properties["auto_append_ext"]["default"] is True
    assert batch_rename_properties["allow_dirs"]["default"] is False
    assert batch_rename_properties["conflict_mode"]["enum"] == [
        "error",
        "skip",
        "overwrite",
        "append_number",
    ]
    assert batch_rename_properties["actual_rename"]["default"] is False

    plugin_properties = by_type["PluginNode"]["config_schema"]["properties"]
    assert plugin_properties["plugin_id"]["required"] is True
    assert plugin_properties["params"]["type"] == "object"
    assert plugin_properties["input_bindings"]["type"] == "object"
    assert plugin_properties["output_bindings"]["type"] == "object"
    assert plugin_properties["plugin_manifest"]["type"] == "object"
    assert plugin_properties["execution_mode"]["enum"] == [
        "in_process",
        "external_process",
    ]
    assert plugin_properties["allow_external_actions"]["default"] is False
    assert plugin_properties["enable_execute"]["default"] is False

    filter_properties = by_type["FilterRowsNode"]["config_schema"]["properties"]
    assert filter_properties["operator"] == {
        "type": "enum",
        "title": "Operator",
        "required": True,
        "enum": ["EQ", "NE", "GT", "GE", "LT", "LE", "CONTAINS", "IS_NULL"],
    }

    add_columns_properties = by_type["AddColumnsNode"]["config_schema"][
        "properties"
    ]
    assert add_columns_properties["column_name"] == {
        "type": "string",
        "title": "Column Name",
        "required": True,
        "default": "new_column",
    }
    assert add_columns_properties["data_type"]["enum"] == [
        "TEXT",
        "INTEGER",
        "FLOAT",
        "BOOLEAN",
    ]

    delete_columns_properties = by_type["DeleteColumnsNode"]["config_schema"][
        "properties"
    ]
    assert delete_columns_properties["columns"] == {
        "type": "array",
        "title": "Columns",
        "required": True,
        "items": {"type": "string"},
        "description": "Column names to remove from the output table.",
    }

    copy_column_properties = by_type["CopyColumnNode"]["config_schema"][
        "properties"
    ]
    assert copy_column_properties["source_field"] == {
        "type": "string",
        "title": "Source Field",
        "required": True,
    }
    assert copy_column_properties["output_mode"] == {
        "type": "enum",
        "title": "Output Mode",
        "required": True,
        "default": "new_field",
        "enum": ["new_field", "overwrite"],
    }
    assert copy_column_properties["trim_value"]["default"] is False

    reorder_columns_properties = by_type["ReorderColumnsNode"]["config_schema"][
        "properties"
    ]
    assert reorder_columns_properties["order"] == {
        "type": "array",
        "title": "Order",
        "required": True,
        "items": {"type": "string"},
        "description": "Target column order.",
    }
    assert reorder_columns_properties["missing_policy"]["enum"] == [
        "error",
        "skip",
        "warn",
    ]
    assert reorder_columns_properties["unlisted_policy"]["default"] == "append"

    rename_columns_properties = by_type["RenameColumnsNode"]["config_schema"][
        "properties"
    ]
    assert rename_columns_properties["mode"]["enum"] == [
        "mappings",
        "prefix",
        "suffix",
        "replace",
    ]
    assert rename_columns_properties["mappings"]["items"] == {"type": "object"}
    assert rename_columns_properties["scope"]["enum"] == ["all", "fields"]
    assert rename_columns_properties["scope_fields"]["items"] == {"type": "string"}
    assert rename_columns_properties["duplicate_policy"]["enum"] == [
        "error",
        "skip",
        "append_number",
    ]
    assert rename_columns_properties["missing_policy"]["enum"] == [
        "error",
        "skip",
        "warn",
    ]
    assert rename_columns_properties["trim_names"]["default"] is True

    fill_cells_properties = by_type["FillCellsNode"]["config_schema"]["properties"]
    assert fill_cells_properties["target_field"] == {
        "type": "string",
        "title": "Target Field",
        "required": True,
    }
    assert fill_cells_properties["direction"]["enum"] == ["down", "up"]
    assert fill_cells_properties["overwrite_rule"]["default"] == "all"

    fill_range_properties = by_type["FillRangeNode"]["config_schema"]["properties"]
    assert fill_range_properties["start_field"] == {
        "type": "string",
        "title": "Start Field",
        "required": True,
    }
    assert fill_range_properties["overwrite_rule"]["default"] == "all"
    assert fill_range_properties["max_cells"]["default"] == 100000

    fill_sequence_properties = by_type["FillSequenceNode"]["config_schema"][
        "properties"
    ]
    assert fill_sequence_properties["target_field"] == {
        "type": "string",
        "title": "Target Field",
        "required": True,
    }
    assert fill_sequence_properties["direction"]["enum"] == ["down", "up"]
    assert fill_sequence_properties["end_mode"]["enum"] == [
        "to_end",
        "count",
        "end_row",
        "reference_non_empty",
    ]
    assert fill_sequence_properties["overwrite_rule"]["default"] == "all"
    assert fill_sequence_properties["zero_pad"]["minimum"] == 0

    replace_text_properties = by_type["ReplaceTextNode"]["config_schema"][
        "properties"
    ]
    assert replace_text_properties["target_field"] == {
        "type": "string",
        "title": "Target Field",
        "required": True,
    }
    assert replace_text_properties["match_mode"]["enum"] == [
        "contains",
        "equals",
        "starts_with",
        "ends_with",
        "regex",
        "is_empty",
        "is_not_empty",
    ]
    assert replace_text_properties["replace_mode"]["default"] == "partial"
    assert replace_text_properties["skip_empty_match_value"]["default"] is True

    delete_rows_properties = by_type["DeleteRowsNode"]["config_schema"][
        "properties"
    ]
    assert delete_rows_properties["delete_mode"] == {
        "type": "enum",
        "title": "Delete Mode",
        "required": True,
        "default": "row_numbers",
        "enum": ["row_numbers", "row_range", "condition", "empty"],
    }
    assert delete_rows_properties["row_spec"]["items"] == {"type": "integer"}
    assert delete_rows_properties["condition_op"]["enum"] == [
        "EQ",
        "NE",
        "GT",
        "GE",
        "LT",
        "LE",
        "CONTAINS",
        "IS_NULL",
    ]
    assert delete_rows_properties["empty_mode"]["default"] == "all_fields"

    copy_rows_properties = by_type["CopyRowsNode"]["config_schema"]["properties"]
    assert copy_rows_properties["source_row"] == {
        "type": "integer",
        "title": "Source Row",
        "required": True,
        "default": 1,
        "minimum": 1,
    }
    assert copy_rows_properties["copy_count"]["default"] == 1
    assert copy_rows_properties["copy_count"]["minimum"] == 0
    assert copy_rows_properties["insert_mode"]["enum"] == [
        "append",
        "prepend",
        "before_row",
        "after_row",
    ]
    assert copy_rows_properties["max_output_rows"]["default"] == 100000

    unpivot_rows_properties = by_type["UnpivotRowsNode"]["config_schema"][
        "properties"
    ]
    assert unpivot_rows_properties["value_fields"] == {
        "type": "array",
        "title": "Value Fields",
        "required": True,
        "items": {"type": "string"},
    }
    assert unpivot_rows_properties["keep_fields"]["items"] == {"type": "string"}
    assert unpivot_rows_properties["output_source_field"]["default"] is True
    assert unpivot_rows_properties["output_status"]["default"] is False
    assert unpivot_rows_properties["empty_mode"]["enum"] == [
        "skip",
        "empty",
        "fixed",
    ]
    assert unpivot_rows_properties["end_mode"]["enum"] == [
        "to_end",
        "count",
        "end_row",
    ]

    deduplicate_rows_properties = by_type["DeduplicateRowsNode"]["config_schema"][
        "properties"
    ]
    assert deduplicate_rows_properties["dedupe_mode"] == {
        "type": "enum",
        "title": "Dedupe Mode",
        "required": True,
        "default": "key_fields",
        "enum": ["key_fields", "entire_row"],
    }
    assert deduplicate_rows_properties["key_fields"]["items"] == {"type": "string"}
    assert deduplicate_rows_properties["empty_key_policy"]["enum"] == [
        "include",
        "skip",
    ]
    assert deduplicate_rows_properties["keep_policy"]["enum"] == [
        "first",
        "last",
        "all",
    ]
    assert deduplicate_rows_properties["output_mode"]["enum"] == ["dedupe", "mark"]
    assert (
        deduplicate_rows_properties["duplicate_status_field"]["default"]
        == "_duplicate_status"
    )

    advanced_filter_properties = by_type["AdvancedFilterRowsNode"]["config_schema"][
        "properties"
    ]
    assert advanced_filter_properties["logic"]["enum"] == ["and", "or"]
    assert advanced_filter_properties["conditions"]["items"] == {"type": "object"}
    assert advanced_filter_properties["output_fields"]["items"] == {"type": "string"}
    assert advanced_filter_properties["result_limit"]["minimum"] == 0
    assert advanced_filter_properties["remove_duplicates"]["default"] is False

    extract_text_properties = by_type["ExtractTextNode"]["config_schema"][
        "properties"
    ]
    assert extract_text_properties["source_field"] == {
        "type": "string",
        "title": "Source Field",
        "required": True,
    }
    assert extract_text_properties["method"]["enum"] == [
        "regex",
        "position",
        "left",
        "right",
        "delimiter",
        "between",
    ]
    assert extract_text_properties["output_mode"]["enum"] == [
        "new_field",
        "overwrite_source",
        "overwrite",
    ]
    assert extract_text_properties["unmatched_mode"]["enum"] == [
        "empty",
        "keep_original",
        "fixed",
        "skip_row",
    ]
    assert extract_text_properties["rule_value_source"]["type"] == "object"

    lookup_matched_properties = by_type["LookupMatchedFieldNameNode"][
        "config_schema"
    ]["properties"]
    assert lookup_matched_properties["source_field"] == {
        "type": "string",
        "title": "Source Field",
        "required": True,
    }
    assert lookup_matched_properties["lookup_fields"]["items"] == {
        "type": "string"
    }
    assert lookup_matched_properties["match_mode"]["enum"] == ["equals"]
    assert lookup_matched_properties["output_field"]["default"] == "matched_field"
    assert lookup_matched_properties["output_status"]["default"] is True
    assert lookup_matched_properties["multi_match_policy"]["enum"] == [
        "first",
        "last",
        "error",
    ]

    merge_columns_properties = by_type["MergeColumnsNode"]["config_schema"][
        "properties"
    ]
    assert merge_columns_properties["fields"] == {
        "type": "array",
        "title": "Fields",
        "required": True,
        "items": {"type": "string"},
    }
    assert merge_columns_properties["separators"]["items"] == {"type": "string"}
    assert merge_columns_properties["output_field"]["default"] == "merged"
    assert merge_columns_properties["skip_empty"]["default"] is False
    assert merge_columns_properties["conflict_mode"]["enum"] == [
        "error",
        "overwrite",
    ]

    numeric_properties = by_type["NumericColumnOperationNode"]["config_schema"][
        "properties"
    ]
    assert numeric_properties["target_field"] == {
        "type": "string",
        "title": "Target Field",
        "required": True,
    }
    assert numeric_properties["operation"]["enum"] == [
        "add",
        "subtract",
        "multiply",
        "divide",
        "sequence",
        "round",
        "floor",
        "ceil",
    ]
    assert numeric_properties["operand_source"]["enum"] == [
        "literal",
        "row_field",
        "row_number",
        "sequence",
    ]
    assert numeric_properties["divide_zero_policy"]["enum"] == [
        "error",
        "empty",
        "fixed",
        "keep_original",
    ]
    assert numeric_properties["range_mode"]["enum"] == [
        "all",
        "row_range",
        "reference_non_empty",
    ]

    current_datetime_properties = by_type["AddCurrentDateTimeColumnNode"][
        "config_schema"
    ]["properties"]
    assert current_datetime_properties["output_mode"]["enum"] == [
        "new_field",
        "overwrite",
    ]
    assert current_datetime_properties["new_field"]["default"] == "current_datetime"
    assert current_datetime_properties["time_mode"]["enum"] == ["fixed", "per_row"]
    assert current_datetime_properties["format_mode"]["enum"] == [
        "iso",
        "strftime",
        "template",
    ]
    assert current_datetime_properties["template"]["default"] == "{datetime}"

    parse_datetime_properties = by_type["ParseDateTimeNode"]["config_schema"][
        "properties"
    ]
    assert parse_datetime_properties["source_field"] == {
        "type": "string",
        "title": "Source Field",
        "required": True,
    }
    assert parse_datetime_properties["parse_type"]["enum"] == [
        "date",
        "time",
        "datetime",
    ]
    assert parse_datetime_properties["input_structure"]["enum"] == [
        "auto",
        "strptime",
    ]
    assert parse_datetime_properties["date_order"]["enum"] == ["ymd", "mdy", "dmy"]
    assert parse_datetime_properties["output_status"]["default"] is True
    assert parse_datetime_properties["unmatched_mode"]["enum"] == [
        "empty",
        "keep_original",
        "fixed",
    ]

    condition_properties = by_type["ConditionFlagNode"]["config_schema"][
        "properties"
    ]
    assert condition_properties["flag_name"] == {
        "type": "string",
        "title": "Flag Name",
        "required": True,
        "default": "condition",
    }
    assert condition_properties["condition_type"]["enum"] == [
        "row_count",
        "field_exists",
        "field_value",
    ]
    assert condition_properties["operator"]["enum"] == [
        "EQ",
        "NE",
        "GT",
        "GE",
        "LT",
        "LE",
        "CONTAINS",
        "IS_NULL",
        "IS_EMPTY",
    ]
    assert condition_properties["value"]["default"] == 1
    assert condition_properties["value_source"]["type"] == "object"
    assert condition_properties["value_field"]["type"] == "string"
    assert condition_properties["aggregation"]["enum"] == [
        "any",
        "all",
        "first",
        "count",
    ]
    assert condition_properties["case_sensitive"]["default"] is True
    assert condition_properties["true_value"]["default"] is True
    assert condition_properties["false_value"]["default"] is False

    jump_anchor_properties = by_type["JumpAnchorNode"]["config_schema"][
        "properties"
    ]
    assert jump_anchor_properties["anchor_name"] == {
        "type": "string",
        "title": "Anchor Name",
        "required": True,
        "default": "anchor",
    }
    assert jump_anchor_properties["description"]["default"] == ""
    assert jump_anchor_properties["allow_multiple_hits"]["default"] is False

    unconditional_jump_properties = by_type["UnconditionalJumpNode"][
        "config_schema"
    ]["properties"]
    assert unconditional_jump_properties["target_mode"] == {
        "type": "enum",
        "title": "Target Mode",
        "required": True,
        "default": "anchor",
        "enum": ["anchor", "node"],
    }
    assert unconditional_jump_properties["target_anchor"]["type"] == "string"
    assert unconditional_jump_properties["target_node_id"]["type"] == "string"
    assert unconditional_jump_properties["reason"]["default"] == ""

    save_memory_properties = by_type["SaveMemoryTableNode"]["config_schema"][
        "properties"
    ]
    assert save_memory_properties["table_name"] == {
        "type": "string",
        "title": "Table Name",
        "required": True,
        "default": "memory_table",
    }
    assert save_memory_properties["mode"]["enum"] == ["overwrite"]

    save_run_properties = by_type["SaveRunTableNode"]["config_schema"][
        "properties"
    ]
    assert save_run_properties["transit_name"]["default"] == "run_table"
    assert save_run_properties["save_memory"]["default"] is True
    assert save_run_properties["mode"]["enum"] == ["overwrite"]

    write_selected_properties = by_type["WriteSelectedColumnsNode"][
        "config_schema"
    ]["properties"]
    assert write_selected_properties["selected_fields"]["items"] == {
        "type": "string"
    }
    assert write_selected_properties["target_type"]["enum"] == [
        "run_table",
        "memory_table",
        "sqlite",
    ]
    assert write_selected_properties["field_name_mode"]["enum"] == [
        "keep",
        "prefix",
        "suffix",
        "mapping",
    ]
    assert write_selected_properties["field_mappings"]["items"] == {
        "type": "object"
    }
    assert write_selected_properties["enable_write"]["default"] is False
    assert write_selected_properties["backup_before_write"]["default"] is False

    write_back_properties = by_type["WriteBackTableNode"]["config_schema"][
        "properties"
    ]
    assert write_back_properties["writeback_direction"]["enum"] == [
        "source_to_target",
        "target_to_source",
    ]
    assert write_back_properties["target_type"]["enum"] == [
        "run_table",
        "memory_table",
        "sqlite",
    ]
    assert write_back_properties["target_type"]["default"] == "sqlite"
    assert write_back_properties["write_mode"]["enum"] == [
        "create",
        "overwrite",
        "append",
    ]
    assert write_back_properties["target_table"]["required"] is True
    assert write_back_properties["match_rules"]["items"] == {"type": "object"}
    assert write_back_properties["field_mappings"]["items"] == {"type": "object"}
    assert write_back_properties["field_mappings"]["required"] is True
    assert write_back_properties["overwrite_policy"]["enum"] == [
        "overwrite",
        "empty_only",
        "skip_existing",
    ]
    assert write_back_properties["enable_write"]["default"] is False
    assert write_back_properties["output_preview_table"]["default"] is True

    publish_properties = by_type["PublishSharedTablesNode"]["config_schema"][
        "properties"
    ]
    assert publish_properties["export_names"]["items"] == {"type": "string"}
    assert publish_properties["retention_seconds"]["minimum"] == 1

    read_properties = by_type["ReadSharedTablesNode"]["config_schema"]["properties"]
    assert read_properties["version_policy"]["enum"] == ["LATEST", "EXACT_VERSION"]
    assert read_properties["exact_version"]["minimum"] == 1


def test_node_definitions_api_rejects_missing_token(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    response = client.get("/api/v1/node-definitions")

    assert response.status_code == 401
    assert response_error(response)["error_code"] == "UNAUTHORIZED"


def test_create_workflow_rejects_reserved_skip_dependents_policy(
    tmp_path: Path,
) -> None:
    client, _store, _container = make_client(tmp_path)

    response = client.post(
        "/api/v1/workflows",
        json={
            "name": "Reserved failure policy",
            "definition": valid_definition()
            | {"failure_policy": {"mode": "SKIP_DEPENDENTS"}},
        },
        headers=auth_headers(),
    )

    assert response.status_code == 422
    error = response_error(response)
    assert error["error_code"] == "WORKFLOW_VALIDATION_FAILED"
    assert error["details"]["errors"][0]["code"] == "UNAVAILABLE_FAILURE_POLICY"
    assert error["details"]["errors"][0]["path"] == "failure_policy.mode"


def test_workflow_not_found_uses_error_envelope(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    response = client.get("/api/v1/workflows/missing", headers=auth_headers())

    assert response.status_code == 404
    error = response_error(response)
    assert error["error_code"] == "WORKFLOW_NOT_FOUND"
    assert error["retryable"] is False


def test_run_query_api(tmp_path: Path) -> None:
    client, store, _container = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="Run source",
        definition=valid_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
        status=WorkflowRunStatus.PENDING,
    )

    listed = response_data(client.get("/api/v1/runs", headers=auth_headers()))
    loaded = response_data(
        client.get(f"/api/v1/runs/{run.workflow_run_id}", headers=auth_headers())
    )
    filtered = response_data(
        client.get(
            "/api/v1/runs",
            params={"status": "PENDING"},
            headers=auth_headers(),
        )
    )

    assert [item["workflow_run_id"] for item in listed] == ["run-1"]
    assert loaded["workflow_id"] == "workflow-1"
    assert loaded["revision_id"] == workflow.revision_id
    assert loaded["completion_reason"] is None
    assert filtered[0]["status"] == "PENDING"


def test_run_query_api_includes_completion_reason(tmp_path: Path) -> None:
    client, store, _container = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="Partial failure run",
        definition=valid_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
        status=WorkflowRunStatus.PENDING,
    )
    running = store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.RUNNING,
        expected_state_version=run.state_version,
    )
    assert running is not None
    failed = store.update_workflow_run_status(
        run.workflow_run_id,
        WorkflowRunStatus.FAILED,
        completion_reason=WorkflowRunCompletionReason.PARTIAL_FAILURE,
        expected_state_version=running.state_version,
    )
    assert failed is not None

    loaded = response_data(
        client.get(f"/api/v1/runs/{run.workflow_run_id}", headers=auth_headers())
    )

    assert loaded["status"] == "FAILED"
    assert loaded["completion_reason"] == "PARTIAL_FAILURE"


def test_start_empty_workflow_run_completes_in_process(tmp_path: Path) -> None:
    client, store, container = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="Empty run",
        definition=valid_definition(),
        workflow_id="workflow-1",
    )

    started = response_data(
        client.post(
            f"/api/v1/workflows/{workflow.workflow_id}/runs",
            headers=auth_headers(),
        )
    )
    run_id = started["workflow_run_id"]
    deadline = time.monotonic() + 5
    loaded = store.get_workflow_run(run_id)
    while time.monotonic() < deadline:
        loaded = store.get_workflow_run(run_id)
        if loaded is not None and loaded.status == "SUCCEEDED":
            break
        time.sleep(0.05)

    process = store.get_workflow_process_for_run(run_id)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        container.supervisor.sweep_exited_children()
        process = store.get_workflow_process_for_run(run_id)
        if process is not None and process.status == "EXITED":
            break
        time.sleep(0.05)
    events = store.list_runtime_events()

    assert loaded is not None
    assert loaded.status == "SUCCEEDED"
    assert process is not None
    assert process.os_pid is not None
    assert process.status == "EXITED"
    assert [event.event_type for event in events] == [
        "WORKFLOW_STARTED",
        "WORKFLOW_FINISHED",
    ]


def test_start_non_empty_workflow_completes_with_fake_executor(tmp_path: Path) -> None:
    client, store, container = make_client(tmp_path)
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": "DAG run",
            "definition": {
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
            },
        },
        headers=auth_headers(),
    )
    workflow = response_data(response)
    run = response_data(
        client.post(
            f"/api/v1/workflows/{workflow['workflow_id']}/runs",
            headers=auth_headers(),
        )
    )

    deadline = time.monotonic() + 5
    loaded_run = store.get_workflow_run(run["workflow_run_id"])
    node_runs = []
    while time.monotonic() < deadline:
        container.supervisor.sweep_exited_children()
        container.supervisor.drain_runtime_events()
        loaded_run = store.get_workflow_run(run["workflow_run_id"])
        node_runs = store.list_node_runs(run["workflow_run_id"])
        if loaded_run is not None and loaded_run.status == "SUCCEEDED":
            break
        time.sleep(0.05)

    process = store.get_workflow_process_for_run(run["workflow_run_id"])
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        container.supervisor.sweep_exited_children()
        process = store.get_workflow_process_for_run(run["workflow_run_id"])
        if process is not None and process.status == "EXITED":
            break
        time.sleep(0.05)

    api_node_runs = response_data(
        client.get(
            f"/api/v1/runs/{run['workflow_run_id']}/nodes",
            headers=auth_headers(),
        )
    )

    assert {node.node_instance_id: node.status for node in node_runs} == {
        "source": "SUCCEEDED",
        "transform": "SUCCEEDED",
    }
    assert [item["node_instance_id"] for item in api_node_runs] == [
        "source",
        "transform",
    ]
    assert loaded_run is not None
    assert loaded_run.status == "SUCCEEDED"
    assert process is not None
    assert process.status == "EXITED"


def test_start_workflow_run_accepts_preview_to_node_payload(tmp_path: Path) -> None:
    client, store, _container = make_client(tmp_path)
    workflow = response_data(
        client.post(
            "/api/v1/workflows",
            json={
                "name": "Preview run",
                "definition": {
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
                },
            },
            headers=auth_headers(),
        )
    )

    run = response_data(
        client.post(
            f"/api/v1/workflows/{workflow['workflow_id']}/runs",
            json={
                "run_mode": "preview_to_node",
                "target_node_instance_id": "transform",
            },
            headers=auth_headers(),
        )
    )

    loaded = store.get_workflow_run(run["workflow_run_id"])
    assert run["run_mode"] == "preview_to_node"
    assert run["target_node_instance_id"] == "transform"
    assert loaded is not None
    assert loaded.run_mode == "preview_to_node"
    assert loaded.target_node_instance_id == "transform"


def test_start_workflow_run_rejects_invalid_preview_payload(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)
    workflow = response_data(
        client.post(
            "/api/v1/workflows",
            json={
                "name": "Preview run",
                "definition": {
                    "schema_version": "1.0",
                    "nodes": [
                        {
                            "node_instance_id": "source",
                            "node_type": "core.source",
                            "node_version": "1.0",
                        }
                    ],
                    "connections": [],
                },
            },
            headers=auth_headers(),
        )
    )

    unsupported = client.post(
        f"/api/v1/workflows/{workflow['workflow_id']}/runs",
        json={"run_mode": "unknown"},
        headers=auth_headers(),
    )
    missing_target = client.post(
        f"/api/v1/workflows/{workflow['workflow_id']}/runs",
        json={"run_mode": "preview_to_node"},
        headers=auth_headers(),
    )
    unknown_target = client.post(
        f"/api/v1/workflows/{workflow['workflow_id']}/runs",
        json={
            "run_mode": "preview_to_node",
            "target_node_instance_id": "missing",
        },
        headers=auth_headers(),
    )

    assert unsupported.status_code == 422
    assert unsupported.json()["error"]["error_code"] == "WORKFLOW_RUN_MODE_UNSUPPORTED"
    assert missing_target.status_code == 422
    assert missing_target.json()["error"]["error_code"] == "TARGET_NODE_REQUIRED"
    assert unknown_target.status_code == 404
    assert unknown_target.json()["error"]["error_code"] == "TARGET_NODE_NOT_FOUND"


def test_cancel_run_marks_process_cancel_requested(tmp_path: Path) -> None:
    client, store, _container = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="Cancelable",
        definition=valid_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(workflow_id=workflow.workflow_id)
    process = store.create_workflow_process(workflow_run_id=run.workflow_run_id)

    response = client.post(
        f"/api/v1/runs/{run.workflow_run_id}/cancel",
        headers=auth_headers(),
    )
    data = response_data(response)

    assert process.process_id == data["process_id"]
    assert data["status"] == "CANCEL_REQUESTED"
    assert data["cancel_requested_at"] is not None


def test_run_not_found_uses_error_envelope(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    response = client.get("/api/v1/runs/missing", headers=auth_headers())

    assert response.status_code == 404
    assert response_error(response)["error_code"] == "WORKFLOW_RUN_NOT_FOUND"


def test_websocket_events_connects(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    with client.websocket_connect(f"/ws/v1/events?token={TOKEN}") as websocket:
        event = websocket.receive_json()

    assert event["event_type"] == "ENGINE_READY"
    assert event["event_id"]
    assert event["sequence_number"] == 1
    assert event["payload"] == {"status": "connected"}


def test_websocket_receives_workflow_process_runtime_event(tmp_path: Path) -> None:
    client, store, _container = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="WebSocket runtime event",
        definition=valid_definition(),
        workflow_id="workflow-1",
    )

    with client.websocket_connect(f"/ws/v1/events?token={TOKEN}") as websocket:
        ready = websocket.receive_json()
        assert ready["event_type"] == "ENGINE_READY"
        time.sleep(0.1)
        received: queue.Queue[object] = queue.Queue()

        def receive_one() -> None:
            try:
                received.put(websocket.receive_json())
            except Exception as exc:
                received.put(exc)

        thread = threading.Thread(target=receive_one, daemon=True)
        thread.start()
        started = response_data(
            client.post(
                f"/api/v1/workflows/{workflow.workflow_id}/runs",
                headers=auth_headers(),
            )
        )
        event = received.get(timeout=5)

    assert not isinstance(event, Exception)
    assert event["event_type"] == "WORKFLOW_STARTED"
    assert event["workflow_run_id"] == started["workflow_run_id"]


def test_runtime_events_can_be_restored_through_rest(tmp_path: Path) -> None:
    client, store, _container = make_client(tmp_path)
    store.append_runtime_event(
        EventModel(
            event_type=EventType.WORKFLOW_STARTED,
            workflow_run_id="run-1",
            payload={"run": "1"},
        )
    )
    store.append_runtime_event(
        EventModel(
            event_type=EventType.NODE_STARTED,
            workflow_run_id="run-1",
            node_run_id="node-run-1",
            payload={"node": "a"},
        )
    )
    store.append_runtime_event(
        EventModel(
            event_type=EventType.NODE_FINISHED,
            workflow_run_id="run-2",
            node_run_id="node-run-2",
            payload={"node": "b"},
        )
    )

    response = client.get(
        "/api/v1/events",
        params={
            "after_sequence_number": 1,
            "workflow_run_id": "run-1",
            "event_type": "NODE_STARTED",
        },
        headers=auth_headers(),
    )
    data = response_data(response)

    assert [event["sequence_number"] for event in data] == [2]
    assert data[0]["event_type"] == "NODE_STARTED"
    assert data[0]["workflow_run_id"] == "run-1"
    assert data[0]["node_run_id"] == "node-run-1"


def test_k0c_read_only_api_contracts_return_runtime_summaries(
    tmp_path: Path,
) -> None:
    client, store, _container = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="Runtime summaries",
        definition=valid_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
        status=WorkflowRunStatus.PENDING,
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="generate",
        node_type="GenerateTestTableNode",
        node_run_id="node-run-1",
    )
    table_ref = make_api_table_ref(
        table_ref_id="table-1",
        workflow_run_id=run.workflow_run_id,
        node_run_id=node.node_run_id,
    )
    store.register_table_ref(table_ref)
    publication = store.create_shared_publication(
        publication_id="publication-1",
        share_name="daily_report",
        producer_workflow_id=workflow.workflow_id,
        producer_run_id=run.workflow_run_id,
        members={"orders": table_ref.table_ref_id},
    )

    table_refs = response_data(
        client.get(
            f"/api/v1/runs/{run.workflow_run_id}/table-refs",
            headers=auth_headers(),
        )
    )
    publications = response_data(
        client.get("/api/v1/shared-publications", headers=auth_headers())
    )
    versions = response_data(
        client.get(
            "/api/v1/shared-publications/daily_report/versions",
            headers=auth_headers(),
        )
    )

    assert table_refs[0]["table_ref_id"] == table_ref.table_ref_id
    assert table_refs[0]["workflow_run_id"] == run.workflow_run_id
    assert table_refs[0]["node_run_id"] == node.node_run_id
    assert table_refs[0]["lifecycle_status"] == "PUBLISHED"
    assert [item["publication_id"] for item in publications] == [
        publication.publication_id
    ]
    assert versions[0]["share_name"] == "daily_report"
    assert versions[0]["publication_version"] == 1
    assert versions[0]["members"][0]["table_ref_id"] == table_ref.table_ref_id


def test_data_api_reads_table_ref_schema_summary_and_limited_rows(
    tmp_path: Path,
) -> None:
    client, store, container = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="Data preview",
        definition=valid_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
        status=WorkflowRunStatus.SUCCEEDED,
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="generate",
        node_type="GenerateTestTableNode",
        node_run_id="node-run-1",
    )
    provider = SQLiteRuntimeTableProvider(container.config.resolved_runtime_dir())
    schema = [
        FieldSchemaModel(
            field_id="orders-row-id",
            name="row_id",
            data_type="INTEGER",
            nullable=False,
            ordinal=0,
        ),
        FieldSchemaModel(
            field_id="orders-amount",
            name="amount",
            data_type="FLOAT",
            nullable=False,
            ordinal=1,
        ),
        FieldSchemaModel(
            field_id="orders-category",
            name="category",
            data_type="TEXT",
            nullable=False,
            ordinal=2,
        ),
    ]
    staging = provider.create_staging_table(
        workflow_run_id=run.workflow_run_id,
        node_run_id=node.node_run_id,
        output_name="orders",
        schema=schema,
    )
    provider.insert_rows(
        staging,
        [
            {"row_id": 1, "amount": 12.5, "category": "keep"},
            {"row_id": 2, "amount": 3.0, "category": "drop"},
            {"row_id": 3, "amount": 18.0, "category": "keep"},
        ],
    )
    published = provider.published_ref_from_staging(staging)
    provider.publish_staging(staging, published)
    store.register_table_ref(published)

    detail = response_data(
        client.get(
            f"/api/v1/data/{published.table_ref_id}",
            headers=auth_headers(),
        )
    )
    schema_response = response_data(
        client.get(
            f"/api/v1/data/{published.table_ref_id}/schema",
            headers=auth_headers(),
        )
    )
    summary = response_data(
        client.get(
            f"/api/v1/data/{published.table_ref_id}/summary",
            headers=auth_headers(),
        )
    )
    rows = response_data(
        client.get(
            f"/api/v1/data/{published.table_ref_id}/rows",
            params=[
                ("offset", "1"),
                ("limit", "1"),
                ("columns", "row_id"),
                ("columns", "amount"),
                ("order_by", "row_id"),
            ],
            headers=auth_headers(),
        )
    )

    assert detail["table_ref_id"] == published.table_ref_id
    assert "opaque_handle" not in detail
    assert schema_response["schema_fingerprint"] == published.schema_fingerprint
    assert [field["name"] for field in schema_response["schema"]] == [
        "row_id",
        "amount",
        "category",
    ]
    assert summary == {
        "table_ref_id": published.table_ref_id,
        "workflow_run_id": run.workflow_run_id,
        "node_run_id": node.node_run_id,
        "logical_table_id": "orders",
        "storage_kind": "RUNTIME_SQL",
        "lifecycle_status": "PUBLISHED",
        "version": 2,
        "schema_fingerprint": published.schema_fingerprint,
        "capabilities": ["READ"],
        "row_count": 3,
    }
    assert rows == {
        "table_ref_id": published.table_ref_id,
        "offset": 1,
        "limit": 1,
        "row_count": 3,
        "columns": ["row_id", "amount"],
        "rows": [{"row_id": 2, "amount": 3.0}],
        "has_more": True,
    }


def test_data_api_rejects_missing_and_invalid_table_ref_reads(
    tmp_path: Path,
) -> None:
    client, store, _container = make_client(tmp_path)
    workflow = store.create_workflow_definition(
        name="Data preview",
        definition=valid_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
        status=WorkflowRunStatus.SUCCEEDED,
    )
    node = store.create_node_run(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="generate",
        node_type="GenerateTestTableNode",
        node_run_id="node-run-1",
    )
    table_ref = make_api_table_ref(
        table_ref_id="table-1",
        workflow_run_id=run.workflow_run_id,
        node_run_id=node.node_run_id,
    )
    store.register_table_ref(table_ref)

    missing = response_error(
        client.get("/api/v1/data/missing/rows", headers=auth_headers())
    )
    invalid_column = response_error(
        client.get(
            f"/api/v1/data/{table_ref.table_ref_id}/rows",
            params=[("columns", "missing")],
            headers=auth_headers(),
        )
    )
    invalid_limit = response_error(
        client.get(
            f"/api/v1/data/{table_ref.table_ref_id}/rows",
            params={"limit": "0"},
            headers=auth_headers(),
        )
    )

    assert missing["error_code"] == "TABLE_REF_NOT_FOUND"
    assert invalid_column["error_code"] == "DATA_READ_REJECTED"
    assert invalid_limit["error_code"] == "VALIDATION_ERROR"


def test_create_app_can_migrate_default_store(tmp_path: Path) -> None:
    data_dir = tmp_path / "runtime"
    container = EngineHostBootstrap(
        EngineConfig(data_dir=data_dir, local_api_token=TOKEN)
    ).initialize()
    client = TestClient(create_app(container))

    response = client.get("/api/v1/workflows", headers=auth_headers())

    assert (data_dir / "metadata" / "flowweaver.db").exists()
    assert response_data(response) == []
    container.close()


def test_api_rejects_missing_token(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    response = client.get("/api/v1/workflows")

    assert response.status_code == 401
    assert response_error(response)["error_code"] == "UNAUTHORIZED"


def test_validate_api_rejects_unknown_node(tmp_path: Path) -> None:
    client, _store, _container = make_client(tmp_path)

    response = client.post(
        "/api/v1/workflows/validate",
        json={
            "definition": {
                "schema_version": "1.0",
                "nodes": [
                    {
                        "node_instance_id": "n1",
                        "node_type": "missing.node",
                        "node_version": "1.0",
                    }
                ],
                "connections": [],
            },
        },
        headers=auth_headers(),
    )

    result = response_data(response)
    assert result["valid"] is False
    assert result["errors"][0]["code"] == "UNKNOWN_NODE_TYPE"
