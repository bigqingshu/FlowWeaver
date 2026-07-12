from __future__ import annotations

from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_output_target_models import (
    TableOutputWriteResult,
)
from flowweaver.nodes.table_write_selected_projection import (
    validate_write_selected_append_schema as _validate_write_selected_append_schema,
)
from flowweaver.nodes.table_write_selected_projection import (
    write_selected_project_rows as _write_selected_project_rows,
)
from flowweaver.nodes.table_write_selected_projection import (
    write_selected_target_schema as _write_selected_target_schema,
)
from flowweaver.nodes.table_write_selected_targets import (
    find_latest_write_selected_target_ref as _find_latest_write_selected_target_ref,
)
from flowweaver.nodes.table_write_selected_targets import (
    next_write_selected_target_version as _next_write_selected_target_version,
)
from flowweaver.protocols.enums import TableRole
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel
from flowweaver.workflow_process.table_output_targets import TableOutputTargetKind

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
) -> TableOutputWriteResult:
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
    affected_rows = len(target_rows)
    target_existed = existing_ref is not None
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
            table_ref = existing_ref
        else:
            table_ref = context.replace_runtime_table_rows(
                task,
                target_ref=existing_ref,
                output_name=target_table,
                schema=target_schema,
                rows=target_rows,
            )
    elif target_type == "memory_table":
        table_ref = context.create_memory_table(
            task,
            logical_table_id=target_table,
            schema=target_schema,
            rows=target_rows,
            role=TableRole.AUXILIARY,
            version=_next_write_selected_target_version(existing_ref),
        )
    else:
        table_ref = context.publish_rows(
            task,
            output_name=target_table,
            schema=target_schema,
            rows=target_rows,
            role=TableRole.AUXILIARY,
            version=_next_write_selected_target_version(existing_ref),
        )
    return TableOutputWriteResult(
        slot="target",
        target_kind=_target_kind(target_type, target_existed=target_existed),
        table_ref=table_ref,
        write_mode=write_mode,
        affected_rows=affected_rows,
        target_existed=target_existed,
    )


def _target_kind(
    target_type: str,
    *,
    target_existed: bool,
) -> TableOutputTargetKind:
    if target_type == "memory_table":
        return (
            TableOutputTargetKind.EXISTING_MEMORY
            if target_existed
            else TableOutputTargetKind.NEW_MEMORY
        )
    return (
        TableOutputTargetKind.EXISTING_RUNTIME_SQL
        if target_existed
        else TableOutputTargetKind.NEW_RUNTIME_SQL
    )
