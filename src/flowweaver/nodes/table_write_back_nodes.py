from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import WRITE_BACK_TABLE_NODE_TYPE
from flowweaver.nodes.table_node_common import bool_status as _bool_status
from flowweaver.nodes.table_node_common import simple_schema as _simple_schema
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
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import find_field
from flowweaver.protocols.enums import LifecycleStatus, TableRole, TableStorageKind
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


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
        status_row = {
            "status": status,
            "writeback_direction": direction,
            "source_table": source_table,
            "target_type": target_type,
            "target_table": target_table,
            "write_mode": write_mode,
            "use_match_rules": _bool_status(use_match_rules),
            "match_rule_count": match_rule_count,
            "field_mapping_count": len(field_mappings),
            "source_row_count": source_row_count,
            "enable_write": _bool_status(enable_write),
            "backup_before_write": _bool_status(backup_before_write),
            "output_preview_table": _bool_status(output_preview_table),
            "actual_write": _bool_status(actual_write),
            "affected_rows": affected_rows,
            "skipped_rows": skipped_rows,
            "warning_count": len(warnings),
            "warnings": "; ".join(warnings),
            "target_table_ref_id": target_ref.table_ref_id if target_ref else "",
            "overwrite_policy": overwrite_policy,
            "source_empty_policy": source_empty_policy,
            "no_match_policy": no_match_policy,
            "multi_match_policy": multi_match_policy,
            "duplicate_target_policy": duplicate_target_policy,
            "match_fields": match_fields,
            "mapped_fields": mapped_fields,
            "skipped_reason": skipped_reason,
        }
        status_ref = context.publish_rows(
            task,
            output_name=f"{task.node_instance_id}_output",
            schema=_writeback_status_schema(),
            rows=[status_row],
        )
        return [status_ref] if target_ref is None else [status_ref, target_ref]


def _writeback_match_rules_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> list[dict[str, str]]:
    value = config.get("match_rules")
    if not isinstance(value, list) or not value:
        raise _NodeValidationError(
            "WriteBackTableNode config.match_rules must be a non-empty list"
        )
    rules: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise _NodeValidationError(
                "WriteBackTableNode config.match_rules must contain objects"
            )
        source_field = _mapping_string(
            item,
            "source_field",
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
        )
        target_field = _mapping_string(
            item,
            "target_field",
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
        )
        if find_field(input_ref.schema, source_field) is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        operator = item.get("operator", "equals")
        if not isinstance(operator, str) or not operator.strip():
            raise _NodeValidationError(
                "WriteBackTableNode match rule operator is required"
            )
        normalized_operator = operator.strip().lower()
        if normalized_operator not in {
            "equals",
            "contains",
            "starts_with",
            "ends_with",
        }:
            raise _NodeValidationError(
                f"Unsupported WriteBackTableNode match rule operator: {operator}"
            )
        rules.append(
            {
                "source_field": source_field,
                "target_field": target_field,
                "operator": normalized_operator,
            }
        )
    return rules


def _writeback_field_mappings_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> list[dict[str, str]]:
    value = config.get("field_mappings")
    if not isinstance(value, list) or not value:
        raise _NodeValidationError(
            "WriteBackTableNode config.field_mappings must be a non-empty list"
        )
    mappings: list[dict[str, str]] = []
    source_fields: set[str] = set()
    target_fields: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise _NodeValidationError(
                "WriteBackTableNode config.field_mappings must contain objects"
            )
        source_field = _mapping_string(
            item,
            "source_field",
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
        )
        target_field = _mapping_string(
            item,
            "target_field",
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
        )
        if find_field(input_ref.schema, source_field) is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        if source_field in source_fields:
            raise _NodeValidationError(
                f"WriteBackTableNode duplicate mapping source: {source_field}"
            )
        if target_field in target_fields:
            raise _NodeValidationError(
                f"WriteBackTableNode duplicate mapping target: {target_field}"
            )
        source_fields.add(source_field)
        target_fields.add(target_field)
        mappings.append(
            {
                "source_field": source_field,
                "target_field": target_field,
            }
        )
    return mappings


def _writeback_runtime_target(
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


def _mapping_string(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _NodeValidationError(f"{node_type} {key} is required")
    return value.strip()


def _writeback_status_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("status", "TEXT", False),
            ("writeback_direction", "TEXT", False),
            ("source_table", "TEXT", False),
            ("target_type", "TEXT", False),
            ("target_table", "TEXT", False),
            ("write_mode", "TEXT", False),
            ("use_match_rules", "TEXT", False),
            ("match_rule_count", "INTEGER", False),
            ("field_mapping_count", "INTEGER", False),
            ("source_row_count", "INTEGER", False),
            ("enable_write", "TEXT", False),
            ("backup_before_write", "TEXT", False),
            ("output_preview_table", "TEXT", False),
            ("actual_write", "TEXT", False),
            ("affected_rows", "INTEGER", False),
            ("skipped_rows", "INTEGER", False),
            ("warning_count", "INTEGER", False),
            ("warnings", "TEXT", False),
            ("target_table_ref_id", "TEXT", False),
            ("overwrite_policy", "TEXT", False),
            ("source_empty_policy", "TEXT", False),
            ("no_match_policy", "TEXT", False),
            ("multi_match_policy", "TEXT", False),
            ("duplicate_target_policy", "TEXT", False),
            ("match_fields", "TEXT", False),
            ("mapped_fields", "TEXT", False),
            ("skipped_reason", "TEXT", False),
        ]
    )
