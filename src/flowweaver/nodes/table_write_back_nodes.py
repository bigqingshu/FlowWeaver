from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import WRITE_BACK_TABLE_NODE_TYPE
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    named_output_config as _named_output_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
)
from flowweaver.nodes.table_write_back_config import (
    writeback_field_mappings_config as _writeback_field_mappings_config,
)
from flowweaver.nodes.table_write_back_config import (
    writeback_match_rules_config as _writeback_match_rules_config,
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
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        direction = _enum_config(
            task.config,
            "writeback_direction",
            default="source_to_target",
            allowed={"source_to_target", "target_to_source"},
            node_type=self.node_type,
        )
        source_table = _optional_string_config(
            task.config,
            "source_table",
            default=input_ref.logical_table_id,
            node_type=self.node_type,
        ).strip()
        if not source_table:
            source_table = input_ref.logical_table_id
        target_table = _named_output_config(
            task.config,
            node_type=self.node_type,
            keys=("target_table",),
        )
        target_type = _enum_config(
            task.config,
            "target_type",
            default="sqlite",
            allowed={"run_table", "memory_table", "sqlite"},
            node_type=self.node_type,
        )
        write_mode = _enum_config(
            task.config,
            "write_mode",
            default="overwrite",
            allowed={"create", "overwrite", "append"},
            node_type=self.node_type,
        )
        use_match_rules = _bool_config(
            task.config,
            "use_match_rules",
            default=True,
        )
        match_rule_count = 0
        match_fields = ""
        if use_match_rules:
            match_rules = _writeback_match_rules_config(
                task.config,
                input_ref=input_ref,
            )
            match_rule_count = len(match_rules)
            match_fields = ",".join(
                f"{rule['source_field']}->{rule['target_field']}"
                for rule in match_rules
            )
        field_mappings = _writeback_field_mappings_config(
            task.config,
            input_ref=input_ref,
        )
        mapped_fields = ",".join(
            f"{mapping['source_field']}->{mapping['target_field']}"
            for mapping in field_mappings
        )
        overwrite_policy = _enum_config(
            task.config,
            "overwrite_policy",
            default="overwrite",
            allowed={"overwrite", "empty_only", "skip_existing"},
            node_type=self.node_type,
        )
        source_empty_policy = _enum_config(
            task.config,
            "source_empty_policy",
            default="skip",
            allowed={"skip", "write_empty", "clear_target"},
            node_type=self.node_type,
        )
        no_match_policy = _enum_config(
            task.config,
            "no_match_policy",
            default="skip",
            allowed={"skip", "insert", "error"},
            node_type=self.node_type,
        )
        multi_match_policy = _enum_config(
            task.config,
            "multi_match_policy",
            default="error",
            allowed={"first", "skip", "error"},
            node_type=self.node_type,
        )
        duplicate_target_policy = _enum_config(
            task.config,
            "duplicate_target_policy",
            default="error",
            allowed={"first", "skip", "error"},
            node_type=self.node_type,
        )
        enable_write = _bool_config(task.config, "enable_write", default=False)
        backup_before_write = _bool_config(
            task.config,
            "backup_before_write",
            default=False,
        )
        output_preview_table = _bool_config(
            task.config,
            "output_preview_table",
            default=True,
        )
        source_row_count = context.count_rows(input_ref)
        status = "skipped"
        actual_write = False
        affected_rows = 0
        skipped_rows = source_row_count
        target_ref: TableRefModel | None = None
        warnings: list[str] = []
        skipped_reason = "enable_write is false"
        if enable_write:
            if direction != "source_to_target":
                skipped_reason = (
                    "target_to_source runtime writes are not implemented"
                )
            elif target_type in {"run_table", "memory_table"}:
                target_ref, affected_rows, skipped_rows = _writeback_runtime_target(
                    task,
                    context,
                    input_ref=input_ref,
                    target_type=target_type,
                    target_table=target_table,
                    write_mode=write_mode,
                    field_mappings=field_mappings,
                    source_empty_policy=source_empty_policy,
                )
                status = "written"
                actual_write = True
                skipped_reason = ""
                if use_match_rules:
                    warnings.append(
                        "match_rules are recorded only for runtime target writes"
                    )
                if backup_before_write:
                    warnings.append(
                        "backup_before_write is ignored for runtime targets"
                    )
            else:
                skipped_reason = "sqlite target writes are not implemented"
        status_row = _writeback_status_row(
            status=status,
            direction=direction,
            source_table=source_table,
            target_type=target_type,
            target_table=target_table,
            write_mode=write_mode,
            use_match_rules=use_match_rules,
            match_rule_count=match_rule_count,
            field_mapping_count=len(field_mappings),
            source_row_count=source_row_count,
            enable_write=enable_write,
            backup_before_write=backup_before_write,
            output_preview_table=output_preview_table,
            actual_write=actual_write,
            affected_rows=affected_rows,
            skipped_rows=skipped_rows,
            warnings=warnings,
            target_ref=target_ref,
            overwrite_policy=overwrite_policy,
            source_empty_policy=source_empty_policy,
            no_match_policy=no_match_policy,
            multi_match_policy=multi_match_policy,
            duplicate_target_policy=duplicate_target_policy,
            match_fields=match_fields,
            mapped_fields=mapped_fields,
            skipped_reason=skipped_reason,
        )
        status_ref = context.publish_rows(
            task,
            output_name=f"{task.node_instance_id}_output",
            schema=_writeback_status_schema(),
            rows=[status_row],
        )
        return [status_ref] if target_ref is None else [status_ref, target_ref]
