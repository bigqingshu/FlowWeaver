from __future__ import annotations

from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_output_target_models import (
    TableOutputWriteResult,
)
from flowweaver.nodes.table_write_back_runtime_rows import (
    validate_writeback_append_schema as _validate_writeback_append_schema,
)
from flowweaver.nodes.table_write_back_runtime_rows import (
    writeback_project_rows as _writeback_project_rows,
)
from flowweaver.nodes.table_write_back_runtime_rows import (
    writeback_target_schema as _writeback_target_schema,
)
from flowweaver.nodes.table_write_back_runtime_targets import (
    find_latest_writeback_target_ref as _find_latest_writeback_target_ref,
)
from flowweaver.nodes.table_write_back_runtime_targets import (
    next_writeback_target_version as _next_writeback_target_version,
)
from flowweaver.protocols.enums import TableRole
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel
from flowweaver.workflow_process.table_output_targets import TableOutputTargetKind

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
) -> tuple[TableOutputWriteResult, int]:
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
    target_existed = existing_ref is not None
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
    return (
        TableOutputWriteResult(
            slot="target",
            target_kind=_target_kind(
                target_type,
                target_existed=target_existed,
            ),
            table_ref=target_ref,
            write_mode=write_mode,
            affected_rows=affected_rows,
            target_existed=target_existed,
        ),
        skipped_rows,
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
