from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.enums import LifecycleStatus, TableRole, TableStorageKind
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


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
