from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import WRITE_SELECTED_COLUMNS_NODE_TYPE
from flowweaver.nodes.table_node_common import bool_status as _bool_status
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_write_selected_helpers import (
    write_selected_columns_status_schema as _write_selected_columns_status_schema,
)
from flowweaver.nodes.table_write_selected_helpers import (
    write_selected_runtime_target as _write_selected_runtime_target,
)
from flowweaver.nodes.table_write_selected_node_config import (
    write_selected_columns_node_config as _write_selected_columns_node_config,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class WriteSelectedColumnsNodeHandler:
    node_type = WRITE_SELECTED_COLUMNS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        config = _write_selected_columns_node_config(
            task.config,
            input_ref=input_ref,
            node_type=self.node_type,
        )
        source_row_count = context.count_rows(input_ref)
        target_ref: TableRefModel | None = None
        status = "skipped"
        actual_write = False
        affected_rows = 0
        skipped_rows = source_row_count
        skipped_reason = "enable_write is false"
        warnings: list[str] = []
        if config.enable_write:
            if config.source_type != "current_table":
                raise _NodeValidationError(
                    "WriteSelectedColumnsNode real writes currently require "
                    "source_type=current_table"
                )
            if config.target_type in {"run_table", "memory_table"}:
                target_ref = _write_selected_runtime_target(
                    task,
                    context,
                    input_ref=input_ref,
                    target_type=config.target_type,
                    target_table=config.target_table,
                    write_mode=config.write_mode,
                    selected_fields=config.selected_fields,
                    target_fields=config.target_fields,
                )
                status = "written"
                actual_write = True
                affected_rows = source_row_count
                skipped_rows = 0
                skipped_reason = ""
                if config.backup_before_write:
                    warnings.append(
                        "backup_before_write is ignored for runtime targets"
                    )
            else:
                skipped_reason = "sqlite target writes are not implemented"
        status_row = {
            "status": status,
            "source_type": config.source_type,
            "target_type": config.target_type,
            "target_table": config.target_table,
            "write_mode": config.write_mode,
            "overwrite_rule": config.overwrite_rule,
            "selected_field_count": len(config.selected_fields),
            "mapping_count": len(config.field_mappings),
            "source_row_count": source_row_count,
            "enable_write": _bool_status(config.enable_write),
            "backup_before_write": _bool_status(config.backup_before_write),
            "actual_write": _bool_status(actual_write),
            "affected_rows": affected_rows,
            "skipped_rows": skipped_rows,
            "warning_count": len(warnings),
            "warnings": "; ".join(warnings),
            "target_table_ref_id": target_ref.table_ref_id if target_ref else "",
            "selected_fields": ",".join(config.selected_fields),
            "target_fields": ",".join(config.target_fields),
            "skipped_reason": skipped_reason,
        }
        status_ref = context.publish_rows(
            task,
            output_name=f"{task.node_instance_id}_output",
            schema=_write_selected_columns_status_schema(),
            rows=[status_row],
        )
        return [status_ref] if target_ref is None else [status_ref, target_ref]

