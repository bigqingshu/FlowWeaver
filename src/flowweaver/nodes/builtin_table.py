from __future__ import annotations

import re
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.builtin_sql import (
    SQL_MAPPING_NODE_TYPE,
    SqlMappingNodeRunner,
    SqlMappingTaskConfig,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeHandlerRegistry,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import (
    append_field,
    find_field,
    has_field,
    remove_fields,
    reorder_fields,
    replace_field_schema,
)
from flowweaver.nodes.value_sources import (
    ValueSourceError,
    parse_value_source,
)
from flowweaver.protocols.enums import ErrorOrigin, NodeResultStatus, TableRole
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

GENERATE_TEST_TABLE_NODE_TYPE = "GenerateTestTableNode"
FILTER_ROWS_NODE_TYPE = "FilterRowsNode"
ADD_COLUMNS_NODE_TYPE = "AddColumnsNode"
DELETE_COLUMNS_NODE_TYPE = "DeleteColumnsNode"
COPY_COLUMN_NODE_TYPE = "CopyColumnNode"
REORDER_COLUMNS_NODE_TYPE = "ReorderColumnsNode"
FILL_CELLS_NODE_TYPE = "FillCellsNode"
FILL_RANGE_NODE_TYPE = "FillRangeNode"
REPLACE_TEXT_NODE_TYPE = "ReplaceTextNode"
DELETE_ROWS_NODE_TYPE = "DeleteRowsNode"
SAVE_MEMORY_TABLE_NODE_TYPE = "SaveMemoryTableNode"
DEFAULT_FILL_RANGE_MAX_CELLS = 100_000
_NodeValidationError = BuiltinTableNodeValidationError


def table_node_types() -> tuple[str, ...]:
    return create_builtin_table_node_handler_registry().node_types()


def is_table_node_type(node_type: str) -> bool:
    return node_type in table_node_types()


def create_builtin_table_node_handler_registry() -> BuiltinTableNodeHandlerRegistry:
    return BuiltinTableNodeHandlerRegistry(
        handlers=(
            GenerateTestTableNodeHandler(),
            FilterRowsNodeHandler(),
            AddColumnsNodeHandler(),
            DeleteColumnsNodeHandler(),
            CopyColumnNodeHandler(),
            ReorderColumnsNodeHandler(),
            FillCellsNodeHandler(),
            FillRangeNodeHandler(),
            ReplaceTextNodeHandler(),
            DeleteRowsNodeHandler(),
            SaveMemoryTableNodeHandler(),
            SqlMappingNodeHandler(),
        )
    )


class GenerateTestTableNodeHandler:
    node_type = GENERATE_TEST_TABLE_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        if task.input_refs:
            raise _NodeValidationError("GenerateTestTableNode does not accept inputs")
        rows_count = _int_config(task.config, "rows")
        seed = _int_config(task.config, "seed", default=0)
        schema = _parse_columns(task.config.get("columns"))
        rows = [
            {
                field.name: _generated_value(field, row_number=row_number, seed=seed)
                for field in schema
            }
            for row_number in range(1, rows_count + 1)
        ]
        return [
            context.publish_rows(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=schema,
                rows=rows,
            )
        ]


class FilterRowsNodeHandler:
    node_type = FILTER_ROWS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        field = task.config.get("field")
        if not isinstance(field, str) or not field:
            raise _NodeValidationError("FilterRowsNode config.field is required")
        if find_field(input_ref.schema, field) is None:
            raise _NodeValidationError(f"Field does not exist: {field}")
        operator = _normalize_operator(task.config.get("operator"))
        value = task.config.get("value")

        def filtered_batches():
            for rows in context.iter_row_batches(input_ref):
                yield [
                    row
                    for row in rows
                    if _row_matches(row.get(field), operator=operator, value=value)
                ]

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=input_ref.schema,
                row_batches=filtered_batches(),
            )
        ]


class AddColumnsNodeHandler:
    node_type = ADD_COLUMNS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        column_name = _string_config(task.config, "column_name")
        if has_field(input_ref.schema, column_name):
            raise _NodeValidationError(f"Field already exists: {column_name}")
        data_type = _normalize_data_type(task.config.get("data_type", "TEXT"))
        default_value = _parse_default_value(
            task.config.get("default_value"),
            data_type=data_type,
        )
        schema = append_field(
            input_ref.schema,
            name=column_name,
            data_type=data_type,
            nullable=default_value is None,
        )

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                yield [
                    row | {column_name: default_value}
                    for row in rows
                ]

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=schema,
                row_batches=output_batches(),
            )
        ]


class DeleteColumnsNodeHandler:
    node_type = DELETE_COLUMNS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        columns = _string_list_config(
            task.config,
            "columns",
            node_type=self.node_type,
        )
        missing_columns = [
            column
            for column in columns
            if not has_field(input_ref.schema, column)
        ]
        if missing_columns:
            raise _NodeValidationError(
                f"Fields do not exist: {', '.join(missing_columns)}"
            )
        schema = remove_fields(input_ref.schema, columns)
        if not schema:
            raise _NodeValidationError("DeleteColumnsNode cannot delete all fields")
        output_columns = [field.name for field in schema]

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                yield [
                    {
                        column: row.get(column)
                        for column in output_columns
                    }
                    for row in rows
                ]

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=schema,
                row_batches=output_batches(),
            )
        ]


class CopyColumnNodeHandler:
    node_type = COPY_COLUMN_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        source_field = _node_string_config(
            task.config,
            "source_field",
            node_type=self.node_type,
        )
        source_schema = find_field(input_ref.schema, source_field)
        if source_schema is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        output_mode = _copy_column_output_mode_config(task.config)
        target_field = _copy_column_target_field_config(
            task.config,
            output_mode=output_mode,
        )
        if output_mode == "new_field":
            if has_field(input_ref.schema, target_field):
                raise _NodeValidationError(f"Field already exists: {target_field}")
            schema = append_field(
                input_ref.schema,
                name=target_field,
                data_type=source_schema.data_type,
                nullable=source_schema.nullable,
            )
        else:
            if not has_field(input_ref.schema, target_field):
                raise _NodeValidationError(f"Field does not exist: {target_field}")
            schema = replace_field_schema(
                input_ref.schema,
                target_field,
                data_type=source_schema.data_type,
                nullable=source_schema.nullable,
            )
        trim_value = _bool_config(task.config, "trim_value", default=False)
        empty_default = task.config.get("empty_default")

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                yield [
                    row | {
                        target_field: _copy_column_value(
                            row.get(source_field),
                            trim_value=trim_value,
                            empty_default=empty_default,
                        )
                    }
                    for row in rows
                ]

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=schema,
                row_batches=output_batches(),
            )
        ]


class ReorderColumnsNodeHandler:
    node_type = REORDER_COLUMNS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        order = _string_list_config(
            task.config,
            "order",
            node_type=self.node_type,
        )
        missing_policy = _enum_config(
            task.config,
            "missing_policy",
            default="error",
            allowed={"error", "skip", "warn"},
            node_type=self.node_type,
        )
        unlisted_policy = _enum_config(
            task.config,
            "unlisted_policy",
            default="append",
            allowed={"append", "drop", "error"},
            node_type=self.node_type,
        )
        missing_columns = [
            column
            for column in order
            if not has_field(input_ref.schema, column)
        ]
        if missing_columns and missing_policy == "error":
            raise _NodeValidationError(
                f"Fields do not exist: {', '.join(missing_columns)}"
            )
        order = [
            column
            for column in order
            if has_field(input_ref.schema, column)
        ]
        input_field_names = [field.name for field in input_ref.schema]
        unlisted_columns = [
            column
            for column in input_field_names
            if column not in order
        ]
        if unlisted_columns and unlisted_policy == "error":
            raise _NodeValidationError(
                f"Fields are not listed: {', '.join(unlisted_columns)}"
            )
        schema = reorder_fields(
            input_ref.schema,
            order,
            include_unlisted=unlisted_policy == "append",
        )
        if not schema:
            raise _NodeValidationError("ReorderColumnsNode output schema is empty")
        output_columns = [field.name for field in schema]

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                yield [
                    {
                        column: row.get(column)
                        for column in output_columns
                    }
                    for row in rows
                ]

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=schema,
                row_batches=output_batches(),
            )
        ]


class FillCellsNodeHandler:
    node_type = FILL_CELLS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        target_field = _node_string_config(
            task.config,
            "target_field",
            node_type=self.node_type,
        )
        if not has_field(input_ref.schema, target_field):
            raise _NodeValidationError(f"Field does not exist: {target_field}")
        value_source = _fill_cells_value_source_config(task.config)
        start_row = _positive_int_config(
            task.config,
            "start_row",
            default=1,
            node_type=self.node_type,
        )
        direction = _enum_config(
            task.config,
            "direction",
            default="down",
            allowed={"down", "up"},
            node_type=self.node_type,
        )
        count = _optional_positive_int_config(
            task.config,
            "count",
            node_type=self.node_type,
        )
        overwrite_rule = _enum_config(
            task.config,
            "overwrite_rule",
            default="all",
            allowed={"all", "empty_only"},
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        if start_row > total_rows and total_rows > 0:
            raise _NodeValidationError("FillCellsNode config.start_row is out of range")
        selected_rows = _fill_cells_selected_rows(
            start_row=start_row,
            direction=direction,
            count=count,
            total_rows=total_rows,
        )

        def output_batches():
            row_number = 1
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    if row_number in selected_rows and (
                        overwrite_rule == "all" or _is_empty_cell(row.get(target_field))
                    ):
                        try:
                            output_rows.append(
                                row | {target_field: value_source.resolve(row)}
                            )
                        except ValueSourceError as exc:
                            raise _NodeValidationError(str(exc)) from exc
                    else:
                        output_rows.append(row)
                    row_number += 1
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=input_ref.schema,
                row_batches=output_batches(),
            )
        ]


class FillRangeNodeHandler:
    node_type = FILL_RANGE_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        start_field = _node_string_config(
            task.config,
            "start_field",
            node_type=self.node_type,
        )
        end_field = _optional_node_string_config(
            task.config,
            "end_field",
            default=start_field,
            node_type=self.node_type,
        )
        target_fields = _field_range(
            input_ref.schema,
            start_field=start_field,
            end_field=end_field,
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        start_row = _positive_int_config(
            task.config,
            "start_row",
            default=1,
            node_type=self.node_type,
        )
        end_row = _optional_positive_int_config(
            task.config,
            "end_row",
            node_type=self.node_type,
        )
        if end_row is None:
            end_row = total_rows
        if total_rows > 0 and (start_row > total_rows or end_row > total_rows):
            raise _NodeValidationError("FillRangeNode row range is out of range")
        if start_row > end_row:
            raise _NodeValidationError("FillRangeNode start_row must be <= end_row")
        max_cells = _positive_int_config(
            task.config,
            "max_cells",
            default=DEFAULT_FILL_RANGE_MAX_CELLS,
            node_type=self.node_type,
        )
        target_row_count = 0 if total_rows <= 0 else end_row - start_row + 1
        target_cell_count = target_row_count * len(target_fields)
        if target_cell_count > max_cells:
            raise _NodeValidationError("FillRangeNode target range exceeds max_cells")
        value_source = _value_source_config(
            task.config,
            "value_source",
            fallback_key="manual_value",
        )
        overwrite_rule = _enum_config(
            task.config,
            "overwrite_rule",
            default="all",
            allowed={"all", "empty_only"},
            node_type=self.node_type,
        )

        def output_batches():
            row_number = 1
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    if start_row <= row_number <= end_row:
                        try:
                            fill_value = value_source.resolve(row)
                        except ValueSourceError as exc:
                            raise _NodeValidationError(str(exc)) from exc
                        output_row = dict(row)
                        for field in target_fields:
                            if overwrite_rule == "all" or _is_empty_cell(
                                output_row.get(field)
                            ):
                                output_row[field] = fill_value
                        output_rows.append(output_row)
                    else:
                        output_rows.append(row)
                    row_number += 1
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=input_ref.schema,
                row_batches=output_batches(),
            )
        ]


class ReplaceTextNodeHandler:
    node_type = REPLACE_TEXT_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        target_field = _node_string_config(
            task.config,
            "target_field",
            node_type=self.node_type,
        )
        if not has_field(input_ref.schema, target_field):
            raise _NodeValidationError(f"Field does not exist: {target_field}")
        match_mode = _enum_config(
            task.config,
            "match_mode",
            default="contains",
            allowed={
                "contains",
                "equals",
                "starts_with",
                "ends_with",
                "regex",
                "is_empty",
                "is_not_empty",
            },
            node_type=self.node_type,
        )
        replace_mode = _enum_config(
            task.config,
            "replace_mode",
            default="partial",
            allowed={"partial", "whole_cell"},
            node_type=self.node_type,
        )
        case_sensitive = _bool_config(
            task.config,
            "case_sensitive",
            default=True,
        )
        replace_count = _non_negative_int_config(
            task.config,
            "replace_count",
            default=0,
            node_type=self.node_type,
        )
        skip_empty_match_value = _bool_config(
            task.config,
            "skip_empty_match_value",
            default=True,
        )
        match_source = _value_source_config(
            task.config,
            "match_value_source",
            fallback_key="match_value",
        )
        replace_source = _value_source_config(
            task.config,
            "replace_value_source",
            fallback_key="replace_value",
        )

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    try:
                        output_rows.append(
                            row | {
                                target_field: _replace_text_value(
                                    row.get(target_field),
                                    row=row,
                                    match_mode=match_mode,
                                    match_source=match_source,
                                    replace_source=replace_source,
                                    replace_mode=replace_mode,
                                    case_sensitive=case_sensitive,
                                    replace_count=replace_count,
                                    skip_empty_match_value=skip_empty_match_value,
                                )
                            }
                        )
                    except (ValueSourceError, re.error) as exc:
                        raise _NodeValidationError(str(exc)) from exc
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=input_ref.schema,
                row_batches=output_batches(),
            )
        ]


class DeleteRowsNodeHandler:
    node_type = DELETE_ROWS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        delete_mode = _enum_config(
            task.config,
            "delete_mode",
            default="row_numbers",
            allowed={"row_numbers", "row_range", "condition", "empty"},
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        should_delete = _delete_rows_predicate(
            task.config,
            input_ref=input_ref,
            delete_mode=delete_mode,
            total_rows=total_rows,
        )

        def output_batches():
            row_number = 1
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    try:
                        if not should_delete(row_number, row):
                            output_rows.append(row)
                    except ValueSourceError as exc:
                        raise _NodeValidationError(str(exc)) from exc
                    row_number += 1
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=input_ref.schema,
                row_batches=output_batches(),
            )
        ]


class SaveMemoryTableNodeHandler:
    node_type = SAVE_MEMORY_TABLE_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        table_name = _save_memory_table_name_config(task.config)
        mode = str(task.config.get("mode", "overwrite"))
        if mode != "overwrite":
            raise _NodeValidationError(
                f"Unsupported SaveMemoryTableNode mode: {mode}"
            )
        rows = context.read_all_rows(input_ref)
        memory_ref = context.create_memory_table(
            task,
            logical_table_id=table_name,
            schema=input_ref.schema,
            rows=rows,
            role=TableRole.AUXILIARY,
        )
        return [input_ref, memory_ref]


class SqlMappingNodeHandler:
    node_type = SQL_MAPPING_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        if task.input_refs:
            raise _NodeValidationError("SqlMappingNode does not accept inputs")
        if context.sql_mapping_runner is None:
            raise _NodeValidationError("SqlMappingNode runner is not configured")
        try:
            table_ref = context.sql_mapping_runner.execute(
                SqlMappingTaskConfig(
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=task.node_run_id,
                    node_instance_id=task.node_instance_id,
                    config=task.config,
                )
            )
        except ValueError as exc:
            raise _NodeValidationError(str(exc)) from exc
        return [table_ref]


class BuiltinTableNodeRunner:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        registry: RuntimeDataRegistry,
        table_provider: SQLiteRuntimeTableProvider,
        memory_provider: MemoryTableProvider | None = None,
    ) -> None:
        memory_provider = memory_provider or MemoryTableProvider()
        self._context = BuiltinTableNodeContext(
            store=store,
            registry=registry,
            table_provider=table_provider,
            memory_provider=memory_provider,
            sql_mapping_runner=SqlMappingNodeRunner(store=store),
        )
        self._handler_registry = create_builtin_table_node_handler_registry()

    def execute(
        self,
        task: NodeTaskModel,
        *,
        executor_id: str,
    ) -> NodeTaskResultModel:
        started_at = utc_now()
        try:
            output_refs = self._execute_node(task)
        except _NodeValidationError as exc:
            return NodeTaskResultModel(
                task_id=task.task_id,
                node_run_id=task.node_run_id,
                attempt=task.attempt,
                executor_id=executor_id,
                process_generation=task.process_generation,
                status=NodeResultStatus.FAILED,
                error={
                    "error_code": "VALIDATION_ERROR",
                    "message": str(exc),
                    "origin": ErrorOrigin.NODE.value,
                },
                started_at=started_at,
                finished_at=utc_now(),
            )
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=[table_ref.table_ref_id for table_ref in output_refs],
            started_at=started_at,
            finished_at=utc_now(),
        )

    def _execute_node(self, task: NodeTaskModel) -> list[TableRefModel]:
        handler = self._handler_registry.get(task.node_type)
        if handler is not None:
            return handler.execute(task, self._context)
        raise _NodeValidationError(f"Unsupported builtin node type: {task.node_type}")


def _parse_columns(value: Any) -> list[FieldSchemaModel]:
    if value is None:
        value = ["row_id", "amount"]
    if not isinstance(value, list) or not value:
        raise _NodeValidationError(
            "GenerateTestTableNode config.columns must be a list"
        )
    fields: list[FieldSchemaModel] = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            name = item
            data_type = _infer_data_type(name)
            nullable = False
            field_id = name
        elif isinstance(item, dict):
            name_value = item.get("name")
            if not isinstance(name_value, str) or not name_value:
                raise _NodeValidationError("column.name is required")
            name = name_value
            data_type = str(item.get("data_type", _infer_data_type(name)))
            nullable = bool(item.get("nullable", False))
            field_id = str(item.get("field_id", name))
        else:
            raise _NodeValidationError("columns must contain strings or objects")
        fields.append(
            FieldSchemaModel(
                field_id=field_id,
                name=name,
                data_type=data_type,
                nullable=nullable,
                ordinal=index,
            )
        )
    return fields


def _int_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int | None = None,
) -> int:
    value = config.get(key, default)
    if not isinstance(value, int):
        raise _NodeValidationError(f"config.{key} must be an integer")
    if value < 0:
        raise _NodeValidationError(f"config.{key} must be non-negative")
    return value


def _positive_int_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int,
    node_type: str,
) -> int:
    value = config.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _NodeValidationError(f"{node_type} config.{key} must be an integer")
    if value < 1:
        raise _NodeValidationError(f"{node_type} config.{key} must be positive")
    return value


def _non_negative_int_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int,
    node_type: str,
) -> int:
    value = config.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _NodeValidationError(f"{node_type} config.{key} must be an integer")
    if value < 0:
        raise _NodeValidationError(f"{node_type} config.{key} must be non-negative")
    return value


def _optional_positive_int_config(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> int | None:
    value = config.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise _NodeValidationError(f"{node_type} config.{key} must be an integer")
    if value < 1:
        raise _NodeValidationError(f"{node_type} config.{key} must be positive")
    return value


def _string_config(config: dict[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _NodeValidationError(f"AddColumnsNode config.{key} is required")
    return value.strip()


def _node_string_config(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _NodeValidationError(f"{node_type} config.{key} is required")
    return value.strip()


def _optional_node_string_config(
    config: dict[str, Any],
    key: str,
    *,
    default: str,
    node_type: str,
) -> str:
    value = config.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise _NodeValidationError(f"{node_type} config.{key} is required")
    return value.strip()


def _bool_config(
    config: dict[str, Any],
    key: str,
    *,
    default: bool,
) -> bool:
    value = config.get(key, default)
    if not isinstance(value, bool):
        raise _NodeValidationError(f"config.{key} must be a boolean")
    return value


def _enum_config(
    config: dict[str, Any],
    key: str,
    *,
    default: str,
    allowed: set[str],
    node_type: str,
) -> str:
    value = config.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise _NodeValidationError(f"{node_type} config.{key} is required")
    normalized = value.strip().lower()
    if normalized not in allowed:
        raise _NodeValidationError(
            f"Unsupported {node_type} config.{key}: {value}"
        )
    return normalized


def _save_memory_table_name_config(config: dict[str, Any]) -> str:
    value = config.get("table_name")
    if not isinstance(value, str) or not value.strip():
        raise _NodeValidationError("SaveMemoryTableNode config.table_name is required")
    return value.strip()


def _string_list_config(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> list[str]:
    value = config.get(key)
    if not isinstance(value, list) or not value:
        raise _NodeValidationError(
            f"{node_type} config.{key} must be a non-empty string list"
        )
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise _NodeValidationError(
                f"{node_type} config.{key} must be a non-empty string list"
            )
        normalized = item.strip()
        if normalized in items:
            raise _NodeValidationError(
                f"{node_type} config.{key} contains duplicate field: {normalized}"
            )
        items.append(normalized)
    return items


def _field_range(
    schema: list[FieldSchemaModel],
    *,
    start_field: str,
    end_field: str,
    node_type: str,
) -> list[str]:
    start_schema = find_field(schema, start_field)
    if start_schema is None:
        raise _NodeValidationError(f"Field does not exist: {start_field}")
    end_schema = find_field(schema, end_field)
    if end_schema is None:
        raise _NodeValidationError(f"Field does not exist: {end_field}")
    if start_schema.ordinal > end_schema.ordinal:
        raise _NodeValidationError(
            f"{node_type} start_field must not be after end_field"
        )
    return [
        field.name
        for field in schema
        if start_schema.ordinal <= field.ordinal <= end_schema.ordinal
    ]


def _copy_column_output_mode_config(config: dict[str, Any]) -> str:
    value = config.get("output_mode", "new_field")
    if not isinstance(value, str) or not value:
        raise _NodeValidationError("CopyColumnNode config.output_mode is required")
    mode = value.strip().lower()
    if mode not in {"new_field", "overwrite"}:
        raise _NodeValidationError(f"Unsupported CopyColumnNode output_mode: {value}")
    return mode


def _copy_column_target_field_config(
    config: dict[str, Any],
    *,
    output_mode: str,
) -> str:
    key = "new_field" if output_mode == "new_field" else "target_field"
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _NodeValidationError(f"CopyColumnNode config.{key} is required")
    return value.strip()


def _copy_column_value(
    value: Any,
    *,
    trim_value: bool,
    empty_default: Any,
) -> Any:
    copied = value.strip() if trim_value and isinstance(value, str) else value
    if copied is None or copied == "":
        return empty_default
    return copied


def _fill_cells_value_source_config(config: dict[str, Any]):
    return _value_source_config(
        config,
        "value_source",
        fallback_key="manual_value",
    )


def _value_source_config(
    config: dict[str, Any],
    key: str,
    *,
    fallback_key: str,
):
    raw_value_source = config.get(key) if key in config else config.get(fallback_key)
    try:
        return parse_value_source(raw_value_source)
    except ValueSourceError as exc:
        raise _NodeValidationError(str(exc)) from exc


def _fill_cells_selected_rows(
    *,
    start_row: int,
    direction: str,
    count: int | None,
    total_rows: int,
) -> set[int]:
    if total_rows <= 0:
        return set()
    if direction == "down":
        end_row = (
            total_rows
            if count is None
            else min(total_rows, start_row + count - 1)
        )
        return set(range(start_row, end_row + 1))
    end_row = 1 if count is None else max(1, start_row - count + 1)
    return set(range(end_row, start_row + 1))


def _is_empty_cell(value: Any) -> bool:
    return value is None or value == ""


def _delete_rows_predicate(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    delete_mode: str,
    total_rows: int,
):
    if delete_mode == "row_numbers":
        row_numbers = _row_numbers_config(
            config,
            "row_spec",
            total_rows=total_rows,
            node_type=DELETE_ROWS_NODE_TYPE,
        )
        return lambda row_number, row: row_number in row_numbers
    if delete_mode == "row_range":
        if total_rows <= 0:
            return lambda row_number, row: False
        start_row = _positive_int_config(
            config,
            "start_row",
            default=1,
            node_type=DELETE_ROWS_NODE_TYPE,
        )
        end_row = _optional_positive_int_config(
            config,
            "end_row",
            node_type=DELETE_ROWS_NODE_TYPE,
        )
        if end_row is None:
            end_row = total_rows
        if start_row > total_rows or end_row > total_rows:
            raise _NodeValidationError("DeleteRowsNode row range is out of range")
        if start_row > end_row:
            raise _NodeValidationError("DeleteRowsNode start_row must be <= end_row")
        return lambda row_number, row: start_row <= row_number <= end_row
    if delete_mode == "condition":
        condition_field = _node_string_config(
            config,
            "condition_field",
            node_type=DELETE_ROWS_NODE_TYPE,
        )
        if find_field(input_ref.schema, condition_field) is None:
            raise _NodeValidationError(f"Field does not exist: {condition_field}")
        operator = _normalize_condition_operator(
            config.get("condition_op"),
            node_type=DELETE_ROWS_NODE_TYPE,
            key="condition_op",
        )
        value_source = _condition_value_source_config(config)
        if (
            value_source.field is not None
            and find_field(input_ref.schema, value_source.field) is None
        ):
            raise _NodeValidationError(f"Field does not exist: {value_source.field}")
        case_sensitive = _bool_config(
            config,
            "case_sensitive",
            default=True,
        )

        def condition_predicate(row_number: int, row: dict[str, Any]) -> bool:
            return _condition_cell_matches(
                row.get(condition_field),
                operator=operator,
                value=value_source.resolve(row),
                case_sensitive=case_sensitive,
            )

        return condition_predicate
    if delete_mode == "empty":
        empty_mode = _enum_config(
            config,
            "empty_mode",
            default="all_fields",
            allowed={"all_fields", "field"},
            node_type=DELETE_ROWS_NODE_TYPE,
        )
        if empty_mode == "field":
            empty_field = _node_string_config(
                config,
                "empty_field",
                node_type=DELETE_ROWS_NODE_TYPE,
            )
            if find_field(input_ref.schema, empty_field) is None:
                raise _NodeValidationError(f"Field does not exist: {empty_field}")
            return lambda row_number, row: _is_empty_cell(row.get(empty_field))
        field_names = [field.name for field in input_ref.schema]
        return lambda row_number, row: all(
            _is_empty_cell(row.get(field_name))
            for field_name in field_names
        )
    raise _NodeValidationError(f"Unsupported DeleteRowsNode delete_mode: {delete_mode}")


def _row_numbers_config(
    config: dict[str, Any],
    key: str,
    *,
    total_rows: int,
    node_type: str,
) -> set[int]:
    value = config.get(key)
    if not isinstance(value, list) or not value:
        raise _NodeValidationError(
            f"{node_type} config.{key} must be a non-empty row number list"
        )
    row_numbers: set[int] = set()
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool):
            raise _NodeValidationError(
                f"{node_type} config.{key} must contain integers"
            )
        if item < 1:
            raise _NodeValidationError(
                f"{node_type} config.{key} must contain positive row numbers"
            )
        if item > total_rows:
            raise _NodeValidationError(f"{node_type} config.{key} is out of range")
        if item in row_numbers:
            raise _NodeValidationError(
                f"{node_type} config.{key} contains duplicate row: {item}"
            )
        row_numbers.add(item)
    return row_numbers


def _condition_value_source_config(config: dict[str, Any]):
    if "condition_value_source" in config:
        raw_value_source = config.get("condition_value_source")
    elif config.get("condition_value_field") is not None:
        condition_value_field = _node_string_config(
            config,
            "condition_value_field",
            node_type=DELETE_ROWS_NODE_TYPE,
        )
        raw_value_source = {
            "mode": "row_field",
            "field": condition_value_field,
        }
    else:
        raw_value_source = config.get("condition_value")
    try:
        return parse_value_source(raw_value_source)
    except ValueSourceError as exc:
        raise _NodeValidationError(str(exc)) from exc


def _normalize_condition_operator(value: Any, *, node_type: str, key: str) -> str:
    if not isinstance(value, str) or not value:
        raise _NodeValidationError(f"{node_type} config.{key} is required")
    operator = value.upper()
    if operator not in {"EQ", "NE", "GT", "GE", "LT", "LE", "CONTAINS", "IS_NULL"}:
        raise _NodeValidationError(f"Unsupported {node_type} {key}: {value}")
    return operator


def _condition_cell_matches(
    cell_value: Any,
    *,
    operator: str,
    value: Any,
    case_sensitive: bool,
) -> bool:
    if case_sensitive or operator in {"GT", "GE", "LT", "LE", "IS_NULL"}:
        return _row_matches(cell_value, operator=operator, value=value)
    cell_text = "" if cell_value is None else str(cell_value)
    value_text = "" if value is None else str(value)
    candidate = cell_text.lower()
    expected = value_text.lower()
    if operator == "EQ":
        return candidate == expected
    if operator == "NE":
        return candidate != expected
    if operator == "CONTAINS":
        return expected in candidate
    return _row_matches(cell_value, operator=operator, value=value)


def _replace_text_value(
    cell_value: Any,
    *,
    row: dict[str, Any],
    match_mode: str,
    match_source,
    replace_source,
    replace_mode: str,
    case_sensitive: bool,
    replace_count: int,
    skip_empty_match_value: bool,
) -> Any:
    match_value = match_source.resolve(row)
    replace_value = replace_source.resolve(row)
    if match_mode not in {"is_empty", "is_not_empty"}:
        match_text = "" if match_value is None else str(match_value)
        if skip_empty_match_value and match_text == "":
            return cell_value
    else:
        match_text = ""
    if not _text_cell_matches(
        cell_value,
        match_mode=match_mode,
        match_text=match_text,
        case_sensitive=case_sensitive,
    ):
        return cell_value
    if replace_mode == "whole_cell" or match_mode in {"is_empty", "is_not_empty"}:
        return replace_value
    cell_text = "" if cell_value is None else str(cell_value)
    replacement = "" if replace_value is None else str(replace_value)
    if match_mode == "regex":
        flags = 0 if case_sensitive else re.IGNORECASE
        count = 0 if replace_count == 0 else replace_count
        return re.sub(match_text, replacement, cell_text, count=count, flags=flags)
    if case_sensitive:
        count = -1 if replace_count == 0 else replace_count
        return cell_text.replace(match_text, replacement, count)
    count = 0 if replace_count == 0 else replace_count
    return re.sub(
        re.escape(match_text),
        replacement,
        cell_text,
        count=count,
        flags=re.IGNORECASE,
    )


def _text_cell_matches(
    cell_value: Any,
    *,
    match_mode: str,
    match_text: str,
    case_sensitive: bool,
) -> bool:
    if match_mode == "is_empty":
        return _is_empty_cell(cell_value)
    if match_mode == "is_not_empty":
        return not _is_empty_cell(cell_value)
    cell_text = "" if cell_value is None else str(cell_value)
    candidate = cell_text if case_sensitive else cell_text.lower()
    expected = match_text if case_sensitive else match_text.lower()
    if match_mode == "contains":
        return expected in candidate
    if match_mode == "equals":
        return candidate == expected
    if match_mode == "starts_with":
        return candidate.startswith(expected)
    if match_mode == "ends_with":
        return candidate.endswith(expected)
    if match_mode == "regex":
        flags = 0 if case_sensitive else re.IGNORECASE
        return re.search(match_text, cell_text, flags=flags) is not None
    return False


def _infer_data_type(name: str) -> str:
    lowered = name.lower()
    if lowered in {"id", "row_id", "index"} or lowered.endswith("_id"):
        return "INTEGER"
    if lowered in {"amount", "score", "value", "price"}:
        return "FLOAT"
    return "TEXT"


def _normalize_data_type(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise _NodeValidationError("AddColumnsNode config.data_type is required")
    data_type = value.upper()
    if data_type not in {"TEXT", "INTEGER", "FLOAT", "BOOLEAN"}:
        raise _NodeValidationError(f"Unsupported AddColumnsNode data_type: {value}")
    return data_type


def _parse_default_value(value: Any, *, data_type: str) -> Any:
    if value is None:
        return None
    if data_type == "TEXT":
        return str(value)
    if data_type == "INTEGER":
        if isinstance(value, bool):
            raise _NodeValidationError("default_value must be an integer")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise _NodeValidationError("default_value must be an integer") from exc
    if data_type == "FLOAT":
        if isinstance(value, bool):
            raise _NodeValidationError("default_value must be a number")
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise _NodeValidationError("default_value must be a number") from exc
    if data_type == "BOOLEAN":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y"}:
                return True
            if normalized in {"false", "0", "no", "n"}:
                return False
        raise _NodeValidationError("default_value must be a boolean")
    return value


def _generated_value(
    field: FieldSchemaModel,
    *,
    row_number: int,
    seed: int,
) -> int | float | str:
    data_type = field.data_type.upper()
    if data_type in {"INT", "INTEGER"}:
        return row_number
    if data_type in {"FLOAT", "REAL", "DOUBLE", "NUMBER", "NUMERIC", "DECIMAL"}:
        return float(row_number)
    return f"{field.name}_{seed}_{row_number}"


def _normalize_operator(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise _NodeValidationError("FilterRowsNode config.operator is required")
    operator = value.upper()
    if operator not in {"EQ", "NE", "GT", "GE", "LT", "LE", "CONTAINS", "IS_NULL"}:
        raise _NodeValidationError(f"Unsupported filter operator: {value}")
    return operator


def _row_matches(cell_value: Any, *, operator: str, value: Any) -> bool:
    if operator == "EQ":
        return cell_value == value
    if operator == "NE":
        return cell_value != value
    if operator == "GT":
        return cell_value > value
    if operator == "GE":
        return cell_value >= value
    if operator == "LT":
        return cell_value < value
    if operator == "LE":
        return cell_value <= value
    if operator == "CONTAINS":
        return str(value) in str(cell_value)
    if operator == "IS_NULL":
        return cell_value is None
    return False
