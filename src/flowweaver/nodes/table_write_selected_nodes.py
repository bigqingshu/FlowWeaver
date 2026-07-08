from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import WRITE_SELECTED_COLUMNS_NODE_TYPE
from flowweaver.nodes.table_node_common import bool_status as _bool_status
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import string_list_config as _string_list_config
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import find_field
from flowweaver.nodes.table_write_selected_helpers import (
    write_selected_columns_status_schema as _write_selected_columns_status_schema,
)
from flowweaver.nodes.table_write_selected_helpers import (
    write_selected_field_mappings_config as _write_selected_field_mappings_config,
)
from flowweaver.nodes.table_write_selected_helpers import (
    write_selected_runtime_target as _write_selected_runtime_target,
)
from flowweaver.nodes.table_write_selected_helpers import (
    write_selected_target_fields as _write_selected_target_fields,
)
from flowweaver.nodes.table_write_selected_helpers import (
    write_selected_target_table_config as _write_selected_target_table_config,
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
        source_type = _enum_config(
            task.config,
            "source_type",
            default="current_table",
            allowed={"current_table", "run_table", "sqlite"},
            node_type=self.node_type,
        )
        selected_fields = _string_list_config(
            task.config,
            "selected_fields",
            node_type=self.node_type,
        )
        missing_fields = [
            field
            for field in selected_fields
            if find_field(input_ref.schema, field) is None
        ]
        if missing_fields:
            raise _NodeValidationError(
                f"Fields do not exist: {', '.join(missing_fields)}"
            )
        target_type = _enum_config(
            task.config,
            "target_type",
            default="run_table",
            allowed={"run_table", "memory_table", "sqlite"},
            node_type=self.node_type,
        )
        target_table = _write_selected_target_table_config(
            task.config,
            target_type=target_type,
        )
        write_mode = _enum_config(
            task.config,
            "write_mode",
            default="overwrite",
            allowed={"create", "overwrite", "append", "upsert"},
            node_type=self.node_type,
        )
        field_name_mode = _enum_config(
            task.config,
            "field_name_mode",
            default="keep",
            allowed={"keep", "prefix", "suffix", "mapping"},
            node_type=self.node_type,
        )
        overwrite_rule = _enum_config(
            task.config,
            "overwrite_rule",
            default="all",
            allowed={"all", "empty_only", "skip_existing"},
            node_type=self.node_type,
        )
        field_mappings = _write_selected_field_mappings_config(
            task.config,
            selected_fields=selected_fields,
        )
        target_fields = _write_selected_target_fields(
            task.config,
            selected_fields=selected_fields,
            field_name_mode=field_name_mode,
            field_mappings=field_mappings,
        )
        enable_write = _bool_config(task.config, "enable_write", default=False)
        backup_before_write = _bool_config(
            task.config,
            "backup_before_write",
            default=False,
        )
        source_row_count = context.count_rows(input_ref)
        target_ref: TableRefModel | None = None
        status = "skipped"
        actual_write = False
        affected_rows = 0
        skipped_rows = source_row_count
        skipped_reason = "enable_write is false"
        warnings: list[str] = []
        if enable_write:
            if source_type != "current_table":
                raise _NodeValidationError(
                    "WriteSelectedColumnsNode real writes currently require "
                    "source_type=current_table"
                )
            if target_type in {"run_table", "memory_table"}:
                target_ref = _write_selected_runtime_target(
                    task,
                    context,
                    input_ref=input_ref,
                    target_type=target_type,
                    target_table=target_table,
                    write_mode=write_mode,
                    selected_fields=selected_fields,
                    target_fields=target_fields,
                )
                status = "written"
                actual_write = True
                affected_rows = source_row_count
                skipped_rows = 0
                skipped_reason = ""
                if backup_before_write:
                    warnings.append(
                        "backup_before_write is ignored for runtime targets"
                    )
            else:
                skipped_reason = "sqlite target writes are not implemented"
        status_row = {
            "status": status,
            "source_type": source_type,
            "target_type": target_type,
            "target_table": target_table,
            "write_mode": write_mode,
            "overwrite_rule": overwrite_rule,
            "selected_field_count": len(selected_fields),
            "mapping_count": len(field_mappings),
            "source_row_count": source_row_count,
            "enable_write": _bool_status(enable_write),
            "backup_before_write": _bool_status(backup_before_write),
            "actual_write": _bool_status(actual_write),
            "affected_rows": affected_rows,
            "skipped_rows": skipped_rows,
            "warning_count": len(warnings),
            "warnings": "; ".join(warnings),
            "target_table_ref_id": target_ref.table_ref_id if target_ref else "",
            "selected_fields": ",".join(selected_fields),
            "target_fields": ",".join(target_fields),
            "skipped_reason": skipped_reason,
        }
        status_ref = context.publish_rows(
            task,
            output_name=f"{task.node_instance_id}_output",
            schema=_write_selected_columns_status_schema(),
            rows=[status_row],
        )
        return [status_ref] if target_ref is None else [status_ref, target_ref]

