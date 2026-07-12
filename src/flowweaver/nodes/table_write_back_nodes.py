from __future__ import annotations

from flowweaver.nodes.builtin_table_execution_result import (
    BuiltinTableExecutionResult,
)
from flowweaver.nodes.builtin_table_node_types import WRITE_BACK_TABLE_NODE_TYPE
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
)
from flowweaver.nodes.table_node_io import primary_input_ref as _primary_input_ref
from flowweaver.nodes.table_node_output_target_models import (
    TableOutputWriteResult,
)
from flowweaver.nodes.table_write_back_node_config import (
    writeback_node_config as _writeback_node_config,
)
from flowweaver.nodes.table_write_back_runtime import (
    writeback_runtime_target as _writeback_runtime_target,
)
from flowweaver.nodes.table_write_back_status import (
    writeback_status_row as _writeback_status_row,
)
from flowweaver.nodes.table_write_back_status import (
    writeback_status_schema as _writeback_status_schema,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel


class WriteBackTableNodeHandler:
    node_type = WRITE_BACK_TABLE_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> BuiltinTableExecutionResult:
        input_ref = _primary_input_ref(
            task,
            context,
            node_type=self.node_type,
        )
        config = _writeback_node_config(
            task.config,
            input_ref=input_ref,
            node_type=self.node_type,
        )
        source_row_count = context.count_rows(input_ref)
        status = "skipped"
        actual_write = False
        affected_rows = 0
        skipped_rows = source_row_count
        write_result: TableOutputWriteResult | None = None
        target_ref: TableRefModel | None = None
        warnings: list[str] = []
        skipped_reason = "enable_write is false"
        if config.enable_write:
            if config.direction != "source_to_target":
                skipped_reason = (
                    "target_to_source runtime writes are not implemented"
                )
            elif config.target_type in {"run_table", "memory_table"}:
                write_result, skipped_rows = _writeback_runtime_target(
                    task,
                    context,
                    input_ref=input_ref,
                    target_type=config.target_type,
                    target_table=config.target_table,
                    write_mode=config.write_mode,
                    field_mappings=config.field_mappings,
                    source_empty_policy=config.source_empty_policy,
                )
                target_ref = write_result.table_ref
                affected_rows = write_result.affected_rows
                status = "written"
                actual_write = True
                skipped_reason = ""
                if config.use_match_rules:
                    warnings.append(
                        "match_rules are recorded only for runtime target writes"
                    )
                if config.backup_before_write:
                    warnings.append(
                        "backup_before_write is ignored for runtime targets"
                    )
            else:
                skipped_reason = "sqlite target writes are not implemented"
        status_row = _writeback_status_row(
            status=status,
            direction=config.direction,
            source_table=config.source_table,
            target_type=config.target_type,
            target_table=config.target_table,
            write_mode=config.write_mode,
            use_match_rules=config.use_match_rules,
            match_rule_count=config.match_rule_count,
            field_mapping_count=len(config.field_mappings),
            source_row_count=source_row_count,
            enable_write=config.enable_write,
            backup_before_write=config.backup_before_write,
            output_preview_table=config.output_preview_table,
            actual_write=actual_write,
            affected_rows=affected_rows,
            skipped_rows=skipped_rows,
            warnings=warnings,
            target_ref=target_ref,
            overwrite_policy=config.overwrite_policy,
            source_empty_policy=config.source_empty_policy,
            no_match_policy=config.no_match_policy,
            multi_match_policy=config.multi_match_policy,
            duplicate_target_policy=config.duplicate_target_policy,
            match_fields=config.match_fields,
            mapped_fields=config.mapped_fields,
            skipped_reason=skipped_reason,
        )
        status_ref = context.publish_rows(
            task,
            output_name=f"{task.node_instance_id}_output",
            schema=_writeback_status_schema(),
            rows=[status_row],
        )
        output_refs = (status_ref,) if target_ref is None else (status_ref, target_ref)
        output_slot_bindings = {"status": status_ref.table_ref_id}
        if target_ref is not None:
            output_slot_bindings["target"] = target_ref.table_ref_id
        return BuiltinTableExecutionResult(
            output_refs=output_refs,
            writes=(write_result,) if write_result is not None else (),
            output_slot_bindings=output_slot_bindings,
            summary_details={
                "operation": "write_back_table",
                "operation_status": status,
                "actual_write": actual_write,
                "source_row_count": source_row_count,
                "affected_rows": affected_rows,
                "skipped_rows": skipped_rows,
                "skipped_reason": skipped_reason,
                "warnings": warnings,
            },
        )
