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


def writeback_runtime_target(
    task: NodeTaskModel,
    context: BuiltinTableNodeContext,
    *,
    input_ref: TableRefModel,
    target_type: str,
    target_table: str,
    write_mode: str,
    field_mappings: list[dict[str, str]],
    source_empty_policy: str,
) -> tuple[TableRefModel, int, int]:
    target_schema = _writeback_target_schema(
        input_ref.schema,
        field_mappings=field_mappings,
    )
    existing_ref = _find_latest_writeback_target_ref(
        context,
        workflow_run_id=task.workflow_run_id,
        target_type=target_type,
        target_table=target_table,
    )
    if write_mode == "create" and existing_ref is not None:
        raise _NodeValidationError(
            f"WriteBackTableNode target table already exists: {target_table}"
        )
    source_rows = context.read_all_rows(input_ref)
    target_rows, skipped_rows = _writeback_project_rows(
        source_rows,
        field_mappings=field_mappings,
        source_empty_policy=source_empty_policy,
    )
    affected_rows = len(target_rows)
    if write_mode == "append" and existing_ref is not None:
        _validate_writeback_append_schema(existing_ref.schema, target_schema)
        target_rows = context.read_all_rows(existing_ref) + target_rows
    version = _next_writeback_target_version(existing_ref)
    if target_type == "memory_table":
        target_ref = context.create_memory_table(
            task,
            logical_table_id=target_table,
            schema=target_schema,
            rows=target_rows,
            role=TableRole.AUXILIARY,
            version=version,
        )
    else:
        target_ref = context.publish_rows(
            task,
            output_name=target_table,
            schema=target_schema,
            rows=target_rows,
            role=TableRole.AUXILIARY,
            version=version,
        )
    return target_ref, affected_rows, skipped_rows


def _writeback_target_schema(
    input_schema: list[FieldSchemaModel],
    *,
    field_mappings: list[dict[str, str]],
) -> list[FieldSchemaModel]:
    fields_by_name = {field.name: field for field in input_schema}
    return [
        FieldSchemaModel(
            field_id=mapping["target_field"],
            name=mapping["target_field"],
            data_type=fields_by_name[mapping["source_field"]].data_type,
            nullable=True,
            ordinal=index,
        )
        for index, mapping in enumerate(field_mappings)
    ]


def _writeback_project_rows(
    source_rows: list[dict[str, Any]],
    *,
    field_mappings: list[dict[str, str]],
    source_empty_policy: str,
) -> tuple[list[dict[str, Any]], int]:
    target_rows: list[dict[str, Any]] = []
    skipped_rows = 0
    for source_row in source_rows:
        target_row: dict[str, Any] = {}
        skip_row = False
        for mapping in field_mappings:
            value = source_row.get(mapping["source_field"])
            if _is_empty_writeback_value(value):
                if source_empty_policy == "skip":
                    skip_row = True
                    break
                if source_empty_policy == "clear_target":
                    value = None
            target_row[mapping["target_field"]] = value
        if skip_row:
            skipped_rows += 1
        else:
            target_rows.append(target_row)
    return target_rows, skipped_rows


def _is_empty_writeback_value(value: Any) -> bool:
    return value is None or value == ""


def _find_latest_writeback_target_ref(
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


def _next_writeback_target_version(existing_ref: TableRefModel | None) -> int:
    if existing_ref is None:
        return 1
    return existing_ref.version + 1


def _validate_writeback_append_schema(
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
            "WriteBackTableNode append target schema does not match"
        )
