from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import WRITE_SELECTED_COLUMNS_NODE_TYPE
from flowweaver.nodes.table_node_common import simple_schema as _simple_schema
from flowweaver.nodes.table_node_config import (
    named_output_config as _named_output_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.enums import LifecycleStatus, TableRole, TableStorageKind
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def write_selected_target_table_config(
    config: dict[str, Any],
    *,
    target_type: str,
) -> str:
    if target_type in {"run_table", "memory_table"}:
        return _named_output_config(
            config,
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            keys=("target_transit_table", "target_table"),
        )
    return _named_output_config(
        config,
        node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
        keys=("target_table",),
    )


def write_selected_field_mappings_config(
    config: dict[str, Any],
    *,
    selected_fields: list[str],
) -> dict[str, str]:
    value = config.get("field_mappings", [])
    if value is None:
        return {}
    if not isinstance(value, list):
        raise _NodeValidationError(
            "WriteSelectedColumnsNode config.field_mappings must be a list"
        )
    selected = set(selected_fields)
    mappings: dict[str, str] = {}
    for item in value:
        if not isinstance(item, dict):
            raise _NodeValidationError(
                "WriteSelectedColumnsNode config.field_mappings must contain objects"
            )
        source_value = item.get("source_field", item.get("source"))
        target_value = item.get("target_field", item.get("target"))
        if not isinstance(source_value, str) or not source_value.strip():
            raise _NodeValidationError(
                "WriteSelectedColumnsNode field_mappings.source_field is required"
            )
        if not isinstance(target_value, str) or not target_value.strip():
            raise _NodeValidationError(
                "WriteSelectedColumnsNode field_mappings.target_field is required"
            )
        source_field = source_value.strip()
        target_field = target_value.strip()
        if source_field not in selected:
            raise _NodeValidationError(
                f"WriteSelectedColumnsNode mapping source is not selected: "
                f"{source_field}"
            )
        if source_field in mappings:
            raise _NodeValidationError(
                f"WriteSelectedColumnsNode duplicate mapping source: {source_field}"
            )
        mappings[source_field] = target_field
    return mappings


def write_selected_target_fields(
    config: dict[str, Any],
    *,
    selected_fields: list[str],
    field_name_mode: str,
    field_mappings: dict[str, str],
) -> list[str]:
    if field_name_mode == "mapping":
        missing_mappings = [
            field
            for field in selected_fields
            if field not in field_mappings
        ]
        if missing_mappings:
            raise _NodeValidationError(
                "WriteSelectedColumnsNode field_mappings missing selected fields: "
                f"{', '.join(missing_mappings)}"
            )
        target_fields = [field_mappings[field] for field in selected_fields]
    elif field_name_mode == "prefix":
        prefix = _optional_string_config(
            config,
            "field_prefix",
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
        )
        target_fields = [f"{prefix}{field}" for field in selected_fields]
    elif field_name_mode == "suffix":
        suffix = _optional_string_config(
            config,
            "field_suffix",
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
        )
        target_fields = [f"{field}{suffix}" for field in selected_fields]
    else:
        target_fields = list(selected_fields)
    duplicates = sorted(
        field
        for field in set(target_fields)
        if target_fields.count(field) > 1
    )
    if duplicates:
        raise _NodeValidationError(
            f"WriteSelectedColumnsNode target fields are duplicated: "
            f"{', '.join(duplicates)}"
        )
    return target_fields


def write_selected_runtime_target(
    task: NodeTaskModel,
    context: BuiltinTableNodeContext,
    *,
    input_ref: TableRefModel,
    target_type: str,
    target_table: str,
    write_mode: str,
    selected_fields: list[str],
    target_fields: list[str],
) -> TableRefModel:
    if write_mode == "upsert":
        raise _NodeValidationError(
            "WriteSelectedColumnsNode write_mode=upsert is not supported for "
            "runtime targets yet"
        )
    target_schema = _write_selected_target_schema(
        input_ref.schema,
        selected_fields=selected_fields,
        target_fields=target_fields,
    )
    existing_ref = _find_latest_write_selected_target_ref(
        context,
        workflow_run_id=task.workflow_run_id,
        target_type=target_type,
        target_table=target_table,
    )
    if write_mode == "create" and existing_ref is not None:
        raise _NodeValidationError(
            f"WriteSelectedColumnsNode target table already exists: {target_table}"
        )
    source_rows = context.read_all_rows(input_ref)
    target_rows = _write_selected_project_rows(
        source_rows,
        selected_fields=selected_fields,
        target_fields=target_fields,
    )
    if write_mode == "append" and existing_ref is not None:
        _validate_write_selected_append_schema(
            existing_ref.schema,
            target_schema,
        )
        target_rows = context.read_all_rows(existing_ref) + target_rows
    if write_mode == "overwrite" and existing_ref is not None:
        _validate_write_selected_append_schema(
            existing_ref.schema,
            target_schema,
        )
        if target_type == "memory_table":
            context.replace_memory_table_rows(existing_ref, target_rows)
            return existing_ref
        return context.replace_runtime_table_rows(
            task,
            target_ref=existing_ref,
            output_name=target_table,
            schema=target_schema,
            rows=target_rows,
        )
    if target_type == "memory_table":
        return context.create_memory_table(
            task,
            logical_table_id=target_table,
            schema=target_schema,
            rows=target_rows,
            role=TableRole.AUXILIARY,
            version=_next_write_selected_target_version(existing_ref),
        )
    return context.publish_rows(
        task,
        output_name=target_table,
        schema=target_schema,
        rows=target_rows,
        role=TableRole.AUXILIARY,
        version=_next_write_selected_target_version(existing_ref),
    )


def _write_selected_target_schema(
    input_schema: list[FieldSchemaModel],
    *,
    selected_fields: list[str],
    target_fields: list[str],
) -> list[FieldSchemaModel]:
    fields_by_name = {field.name: field for field in input_schema}
    return [
        FieldSchemaModel(
            field_id=target_field,
            name=target_field,
            data_type=fields_by_name[source_field].data_type,
            nullable=fields_by_name[source_field].nullable,
            ordinal=index,
        )
        for index, (source_field, target_field) in enumerate(
            zip(selected_fields, target_fields, strict=True)
        )
    ]


def _write_selected_project_rows(
    source_rows: list[dict[str, Any]],
    *,
    selected_fields: list[str],
    target_fields: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            target_field: row.get(source_field)
            for source_field, target_field in zip(
                selected_fields,
                target_fields,
                strict=True,
            )
        }
        for row in source_rows
    ]


def _find_latest_write_selected_target_ref(
    context: BuiltinTableNodeContext,
    *,
    workflow_run_id: str,
    target_type: str,
    target_table: str,
) -> TableRefModel | None:
    storage_kind = (
        TableStorageKind.MEMORY
        if target_type == "memory_table"
        else TableStorageKind.RUNTIME_SQL
    )
    candidates = [
        table_ref
        for table_ref in context.registry.list_by_workflow_run(workflow_run_id)
        if table_ref.logical_table_id == target_table
        and table_ref.storage_kind == storage_kind
        and table_ref.lifecycle_status in {
            LifecycleStatus.ACTIVE,
            LifecycleStatus.PUBLISHED,
        }
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda table_ref: table_ref.created_at)


def _next_write_selected_target_version(existing_ref: TableRefModel | None) -> int:
    if existing_ref is None:
        return 1
    return existing_ref.version + 1


def _validate_write_selected_append_schema(
    existing_schema: list[FieldSchemaModel],
    target_schema: list[FieldSchemaModel],
) -> None:
    existing = [
        (field.name, field.data_type.upper())
        for field in sorted(existing_schema, key=lambda item: item.ordinal)
    ]
    target = [
        (field.name, field.data_type.upper())
        for field in sorted(target_schema, key=lambda item: item.ordinal)
    ]
    if existing != target:
        raise _NodeValidationError(
            "WriteSelectedColumnsNode append target schema does not match"
        )


def write_selected_columns_status_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("status", "TEXT", False),
            ("source_type", "TEXT", False),
            ("target_type", "TEXT", False),
            ("target_table", "TEXT", False),
            ("write_mode", "TEXT", False),
            ("overwrite_rule", "TEXT", False),
            ("selected_field_count", "INTEGER", False),
            ("mapping_count", "INTEGER", False),
            ("source_row_count", "INTEGER", False),
            ("enable_write", "TEXT", False),
            ("backup_before_write", "TEXT", False),
            ("actual_write", "TEXT", False),
            ("affected_rows", "INTEGER", False),
            ("skipped_rows", "INTEGER", False),
            ("warning_count", "INTEGER", False),
            ("warnings", "TEXT", False),
            ("target_table_ref_id", "TEXT", False),
            ("selected_fields", "TEXT", False),
            ("target_fields", "TEXT", False),
            ("skipped_reason", "TEXT", False),
        ]
    )
