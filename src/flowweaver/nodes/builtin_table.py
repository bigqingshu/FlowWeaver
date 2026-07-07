from __future__ import annotations

import fnmatch
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

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
COPY_ROWS_NODE_TYPE = "CopyRowsNode"
DEDUPLICATE_ROWS_NODE_TYPE = "DeduplicateRowsNode"
ADVANCED_FILTER_ROWS_NODE_TYPE = "AdvancedFilterRowsNode"
EXTRACT_TEXT_NODE_TYPE = "ExtractTextNode"
LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE = "LookupMatchedFieldNameNode"
MERGE_COLUMNS_NODE_TYPE = "MergeColumnsNode"
NUMERIC_COLUMN_OPERATION_NODE_TYPE = "NumericColumnOperationNode"
ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE = "AddCurrentDateTimeColumnNode"
PARSE_DATETIME_NODE_TYPE = "ParseDateTimeNode"
SAVE_MEMORY_TABLE_NODE_TYPE = "SaveMemoryTableNode"
SAVE_RUN_TABLE_NODE_TYPE = "SaveRunTableNode"
WRITE_SELECTED_COLUMNS_NODE_TYPE = "WriteSelectedColumnsNode"
WRITE_BACK_TABLE_NODE_TYPE = "WriteBackTableNode"
LIST_FILES_NODE_TYPE = "ListFilesNode"
BATCH_RENAME_FILES_NODE_TYPE = "BatchRenameFilesNode"
PLUGIN_NODE_TYPE = "PluginNode"
DEFAULT_FILL_RANGE_MAX_CELLS = 100_000
DEFAULT_COPY_ROWS_MAX_OUTPUT_ROWS = 100_000
_SKIP_ROW = object()
_NodeValidationError = BuiltinTableNodeValidationError


class _LookupMatchedOutputFields(TypedDict):
    field: str
    value: str | None
    row: str | None
    status: str | None


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
            CopyRowsNodeHandler(),
            DeduplicateRowsNodeHandler(),
            AdvancedFilterRowsNodeHandler(),
            ExtractTextNodeHandler(),
            LookupMatchedFieldNameNodeHandler(),
            MergeColumnsNodeHandler(),
            NumericColumnOperationNodeHandler(),
            AddCurrentDateTimeColumnNodeHandler(),
            ParseDateTimeNodeHandler(),
            SaveMemoryTableNodeHandler(),
            SaveRunTableNodeHandler(),
            WriteSelectedColumnsNodeHandler(),
            WriteBackTableNodeHandler(),
            ListFilesNodeHandler(),
            BatchRenameFilesNodeHandler(),
            PluginNodeHandler(),
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


class CopyRowsNodeHandler:
    node_type = COPY_ROWS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        source_row_number = _positive_int_config(
            task.config,
            "source_row",
            default=1,
            node_type=self.node_type,
        )
        if source_row_number > total_rows:
            raise _NodeValidationError("CopyRowsNode config.source_row is out of range")
        copy_count = _non_negative_int_config(
            task.config,
            "copy_count",
            default=1,
            node_type=self.node_type,
        )
        insert_mode = _enum_config(
            task.config,
            "insert_mode",
            default="append",
            allowed={"append", "prepend", "before_row", "after_row"},
            node_type=self.node_type,
        )
        insert_row = source_row_number
        if insert_mode in {"before_row", "after_row"}:
            insert_row = _positive_int_config(
                task.config,
                "insert_row",
                default=source_row_number,
                node_type=self.node_type,
            )
            if insert_row > total_rows:
                raise _NodeValidationError(
                    "CopyRowsNode config.insert_row is out of range"
                )
        max_output_rows = _positive_int_config(
            task.config,
            "max_output_rows",
            default=DEFAULT_COPY_ROWS_MAX_OUTPUT_ROWS,
            node_type=self.node_type,
        )
        output_row_count = total_rows + copy_count
        if output_row_count > max_output_rows:
            raise _NodeValidationError("CopyRowsNode output exceeds max_output_rows")
        source_row = _copy_row_source_row(
            context,
            input_ref=input_ref,
            source_row_number=source_row_number,
        )

        def output_batches():
            if insert_mode == "prepend":
                yield from _copy_row_batches(
                    source_row,
                    copy_count=copy_count,
                    batch_size=context.row_batch_size,
                )
            row_number = 1
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    if insert_mode == "before_row" and row_number == insert_row:
                        if output_rows:
                            yield output_rows
                            output_rows = []
                        yield from _copy_row_batches(
                            source_row,
                            copy_count=copy_count,
                            batch_size=context.row_batch_size,
                        )
                    output_rows.append(row)
                    if insert_mode == "after_row" and row_number == insert_row:
                        if output_rows:
                            yield output_rows
                            output_rows = []
                        yield from _copy_row_batches(
                            source_row,
                            copy_count=copy_count,
                            batch_size=context.row_batch_size,
                        )
                    row_number += 1
                if output_rows:
                    yield output_rows
            if insert_mode == "append":
                yield from _copy_row_batches(
                    source_row,
                    copy_count=copy_count,
                    batch_size=context.row_batch_size,
                )

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=input_ref.schema,
                row_batches=output_batches(),
            )
        ]


class DeduplicateRowsNodeHandler:
    node_type = DEDUPLICATE_ROWS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        key_fields = _deduplicate_key_fields(task.config, input_ref)
        trim = _bool_config(task.config, "trim", default=False)
        ignore_case = _bool_config(task.config, "ignore_case", default=False)
        empty_key_policy = _enum_config(
            task.config,
            "empty_key_policy",
            default="include",
            allowed={"include", "skip"},
            node_type=self.node_type,
        )
        keep_policy = _enum_config(
            task.config,
            "keep_policy",
            default="first",
            allowed={"first", "last", "all"},
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="dedupe",
            allowed={"dedupe", "mark"},
            node_type=self.node_type,
        )
        add_marker_columns = _bool_config(
            task.config,
            "add_marker_columns",
            default=output_mode == "mark",
        )
        if output_mode == "mark" and not add_marker_columns:
            raise _NodeValidationError(
                "DeduplicateRowsNode output_mode=mark requires marker columns"
            )
        marker_fields = _deduplicate_marker_fields(task.config)
        output_schema = (
            _deduplicate_output_schema(input_ref.schema, marker_fields)
            if add_marker_columns
            else input_ref.schema
        )
        groups = _deduplicate_groups(
            context,
            input_ref=input_ref,
            key_fields=key_fields,
            trim=trim,
            ignore_case=ignore_case,
            empty_key_policy=empty_key_policy,
        )

        def output_batches():
            row_number = 1
            occurrence_counts: dict[tuple[Any, ...], int] = {}
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    key = _deduplicate_key(
                        row,
                        key_fields=key_fields,
                        trim=trim,
                        ignore_case=ignore_case,
                        empty_key_policy=empty_key_policy,
                    )
                    occurrence_index = _deduplicate_occurrence_index(
                        occurrence_counts,
                        key,
                    )
                    keep_row = _deduplicate_should_keep(
                        row_number,
                        key=key,
                        groups=groups,
                        keep_policy=keep_policy,
                    )
                    if output_mode == "mark" or keep_row:
                        output_row = dict(row)
                        if add_marker_columns:
                            output_row |= _deduplicate_marker_values(
                                key=key,
                                groups=groups,
                                occurrence_index=occurrence_index,
                                keep_row=keep_row,
                                marker_fields=marker_fields,
                            )
                        output_rows.append(output_row)
                    row_number += 1
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=output_schema,
                row_batches=output_batches(),
            )
        ]


class AdvancedFilterRowsNodeHandler:
    node_type = ADVANCED_FILTER_ROWS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        logic = _enum_config(
            task.config,
            "logic",
            default="and",
            allowed={"and", "or"},
            node_type=self.node_type,
        )
        conditions = _advanced_filter_conditions(task.config, input_ref)
        output_fields = _advanced_filter_output_fields(task.config, input_ref)
        output_schema = reorder_fields(
            input_ref.schema,
            output_fields,
            include_unlisted=False,
        )
        result_limit = _optional_non_negative_int_config(
            task.config,
            "result_limit",
            node_type=self.node_type,
        )
        max_intermediate = _optional_positive_int_config(
            task.config,
            "max_intermediate",
            node_type=self.node_type,
        )
        remove_duplicates = _bool_config(
            task.config,
            "remove_duplicates",
            default=False,
        )

        def output_batches():
            output_count = 0
            matched_count = 0
            seen_rows: set[tuple[Any, ...]] = set()
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    try:
                        if not _advanced_filter_row_matches(
                            row,
                            conditions=conditions,
                            logic=logic,
                        ):
                            continue
                    except ValueSourceError as exc:
                        raise _NodeValidationError(str(exc)) from exc
                    output_row = {
                        field_name: row.get(field_name)
                        for field_name in output_fields
                    }
                    if remove_duplicates:
                        output_key = tuple(
                            output_row.get(field)
                            for field in output_fields
                        )
                        if output_key in seen_rows:
                            continue
                        seen_rows.add(output_key)
                    matched_count += 1
                    if (
                        max_intermediate is not None
                        and matched_count > max_intermediate
                    ):
                        raise _NodeValidationError(
                            "AdvancedFilterRowsNode matched rows exceed "
                            "max_intermediate"
                        )
                    if result_limit is not None and output_count >= result_limit:
                        if output_rows:
                            yield output_rows
                        return
                    output_rows.append(output_row)
                    output_count += 1
                if output_rows:
                    yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=output_schema,
                row_batches=output_batches(),
            )
        ]


class ExtractTextNodeHandler:
    node_type = EXTRACT_TEXT_NODE_TYPE

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
        if find_field(input_ref.schema, source_field) is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        method = _enum_config(
            task.config,
            "method",
            default="regex",
            allowed={"regex", "position", "left", "right", "delimiter", "between"},
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="new_field",
            allowed={"new_field", "overwrite_source", "overwrite"},
            node_type=self.node_type,
        )
        output_field = _extract_text_output_field(
            task.config,
            input_ref=input_ref,
            source_field=source_field,
            output_mode=output_mode,
        )
        output_schema = _extract_text_output_schema(
            input_ref.schema,
            output_field=output_field,
            output_mode=output_mode,
        )
        strip_result = _bool_config(task.config, "strip_result", default=False)
        unmatched_mode = _enum_config(
            task.config,
            "unmatched_mode",
            default="empty",
            allowed={"empty", "keep_original", "fixed", "skip_row"},
            node_type=self.node_type,
        )
        rule_source = _value_source_config(
            task.config,
            "rule_value_source",
            fallback_key=_extract_text_rule_fallback_key(method),
        )
        unmatched_source = _value_source_config(
            task.config,
            "unmatched_value_source",
            fallback_key="unmatched_value",
        )

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    try:
                        extracted = _extract_text_value(
                            row.get(source_field),
                            row=row,
                            config=task.config,
                            method=method,
                            rule_source=rule_source,
                            strip_result=strip_result,
                        )
                        if extracted is None:
                            extracted = _extract_text_unmatched_value(
                                row,
                                source_value=row.get(source_field),
                                unmatched_mode=unmatched_mode,
                                unmatched_source=unmatched_source,
                            )
                        if extracted is _SKIP_ROW:
                            continue
                    except (ValueSourceError, re.error, IndexError) as exc:
                        raise _NodeValidationError(str(exc)) from exc
                    output_rows.append(dict(row) | {output_field: extracted})
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=output_schema,
                row_batches=output_batches(),
            )
        ]


class LookupMatchedFieldNameNodeHandler:
    node_type = LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        if len(task.input_refs) != 2:
            raise _NodeValidationError(
                "LookupMatchedFieldNameNode requires main and lookup input_refs"
            )
        main_ref = context.input_ref(task.input_refs[0])
        lookup_ref = context.input_ref(task.input_refs[1])
        source_field = _node_string_config(
            task.config,
            "source_field",
            node_type=self.node_type,
        )
        if find_field(main_ref.schema, source_field) is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        lookup_fields = _string_list_config(
            task.config,
            "lookup_fields",
            node_type=self.node_type,
        )
        missing_lookup_fields = [
            field_name
            for field_name in lookup_fields
            if not has_field(lookup_ref.schema, field_name)
        ]
        if missing_lookup_fields:
            raise _NodeValidationError(
                f"Fields do not exist: {', '.join(missing_lookup_fields)}"
            )
        match_mode = _enum_config(
            task.config,
            "match_mode",
            default="equals",
            allowed={"equals"},
            node_type=self.node_type,
        )
        multi_match_policy = _enum_config(
            task.config,
            "multi_match_policy",
            default="first",
            allowed={"first", "last", "error"},
            node_type=self.node_type,
        )
        output_fields = _lookup_matched_output_fields(task.config)
        output_schema = _lookup_matched_output_schema(main_ref.schema, output_fields)
        no_match_value = task.config.get("no_match_value", "")
        lookup_index = _lookup_matched_field_index(
            context,
            lookup_ref=lookup_ref,
            lookup_fields=lookup_fields,
            match_mode=match_mode,
        )

        def output_batches():
            for rows in context.iter_row_batches(main_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    matches = lookup_index.get(row.get(source_field), [])
                    if len(matches) > 1 and multi_match_policy == "error":
                        raise _NodeValidationError(
                            "LookupMatchedFieldNameNode found multiple matches"
                        )
                    match = _lookup_matched_select_match(
                        matches,
                        multi_match_policy=multi_match_policy,
                    )
                    output_rows.append(
                        dict(row)
                        | _lookup_matched_values(
                            match,
                            match_count=len(matches),
                            output_fields=output_fields,
                            no_match_value=no_match_value,
                        )
                    )
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=output_schema,
                row_batches=output_batches(),
            )
        ]


class MergeColumnsNodeHandler:
    node_type = MERGE_COLUMNS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        fields = _string_list_config(
            task.config,
            "fields",
            node_type=self.node_type,
        )
        missing_fields = [
            field_name
            for field_name in fields
            if not has_field(input_ref.schema, field_name)
        ]
        if missing_fields:
            raise _NodeValidationError(
                f"Fields do not exist: {', '.join(missing_fields)}"
            )
        separators = _merge_columns_separators(task.config, field_count=len(fields))
        output_field = _optional_node_string_config(
            task.config,
            "output_field",
            default="merged",
            node_type=self.node_type,
        )
        conflict_mode = _enum_config(
            task.config,
            "conflict_mode",
            default="error",
            allowed={"error", "overwrite"},
            node_type=self.node_type,
        )
        output_schema = _merge_columns_output_schema(
            input_ref.schema,
            output_field=output_field,
            conflict_mode=conflict_mode,
        )
        skip_empty = _bool_config(task.config, "skip_empty", default=False)
        trim_value = _bool_config(task.config, "trim_value", default=False)
        empty_placeholder = task.config.get("empty_placeholder", "")

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                yield [
                    row
                    | {
                        output_field: _merge_columns_value(
                            row,
                            fields=fields,
                            separators=separators,
                            skip_empty=skip_empty,
                            trim_value=trim_value,
                            empty_placeholder=empty_placeholder,
                        )
                    }
                    for row in rows
                ]

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=output_schema,
                row_batches=output_batches(),
            )
        ]


class NumericColumnOperationNodeHandler:
    node_type = NUMERIC_COLUMN_OPERATION_NODE_TYPE

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
        if find_field(input_ref.schema, target_field) is None:
            raise _NodeValidationError(f"Field does not exist: {target_field}")
        operation = _enum_config(
            task.config,
            "operation",
            default="add",
            allowed={
                "add",
                "subtract",
                "multiply",
                "divide",
                "sequence",
                "round",
                "floor",
                "ceil",
            },
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="overwrite",
            allowed={"overwrite", "new_field"},
            node_type=self.node_type,
        )
        output_field = _numeric_output_field(
            task.config,
            input_ref=input_ref,
            target_field=target_field,
            output_mode=output_mode,
        )
        output_schema = _numeric_output_schema(
            input_ref.schema,
            output_field=output_field,
            output_mode=output_mode,
        )
        row_selector = _numeric_row_selector(task.config, input_ref=input_ref)
        operand_config = _numeric_operand_config(task.config, input_ref=input_ref)
        decimal_places = _optional_non_negative_int_config(
            task.config,
            "decimal_places",
            node_type=self.node_type,
        )
        non_number_policy = _enum_config(
            task.config,
            "non_number_policy",
            default="error",
            allowed={"error", "empty", "fixed", "keep_original"},
            node_type=self.node_type,
        )
        divide_zero_policy = _enum_config(
            task.config,
            "divide_zero_policy",
            default="error",
            allowed={"error", "empty", "fixed", "keep_original"},
            node_type=self.node_type,
        )

        def output_batches():
            row_number = 1
            sequence_index = 0
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    if not _numeric_row_selected(
                        row,
                        row_number=row_number,
                        selector=row_selector,
                    ):
                        output_rows.append(
                            dict(row) | {output_field: row.get(target_field)}
                        )
                        row_number += 1
                        continue
                    sequence_index += 1
                    output_value = _numeric_operation_value(
                        row,
                        row_number=row_number,
                        sequence_index=sequence_index,
                        target_field=target_field,
                        operation=operation,
                        operand_config=operand_config,
                        decimal_places=decimal_places,
                        non_number_policy=non_number_policy,
                        divide_zero_policy=divide_zero_policy,
                        config=task.config,
                    )
                    output_rows.append(dict(row) | {output_field: output_value})
                    row_number += 1
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=output_schema,
                row_batches=output_batches(),
            )
        ]


class AddCurrentDateTimeColumnNodeHandler:
    node_type = ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="new_field",
            allowed={"new_field", "overwrite"},
            node_type=self.node_type,
        )
        output_field = _datetime_output_field(
            task.config,
            input_ref=input_ref,
            output_mode=output_mode,
        )
        output_schema = _datetime_output_schema(
            input_ref.schema,
            output_field=output_field,
            output_mode=output_mode,
        )
        time_mode = _enum_config(
            task.config,
            "time_mode",
            default="fixed",
            allowed={"fixed", "per_row"},
            node_type=self.node_type,
        )
        format_mode = _enum_config(
            task.config,
            "format_mode",
            default="iso",
            allowed={"iso", "strftime", "template"},
            node_type=self.node_type,
        )
        fixed_value = (
            _datetime_formatted_value(
                utc_now(),
                config=task.config,
                format_mode=format_mode,
            )
            if time_mode == "fixed"
            else None
        )

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    value = fixed_value
                    if value is None:
                        value = _datetime_formatted_value(
                            utc_now(),
                            config=task.config,
                            format_mode=format_mode,
                        )
                    output_rows.append(dict(row) | {output_field: value})
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=output_schema,
                row_batches=output_batches(),
            )
        ]


class ParseDateTimeNodeHandler:
    node_type = PARSE_DATETIME_NODE_TYPE

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
        if find_field(input_ref.schema, source_field) is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        use_separate_time_field = _bool_config(
            task.config,
            "use_separate_time_field",
            default=False,
        )
        time_source_field = None
        if use_separate_time_field:
            time_source_field = _node_string_config(
                task.config,
                "time_source_field",
                node_type=self.node_type,
            )
            if find_field(input_ref.schema, time_source_field) is None:
                raise _NodeValidationError(f"Field does not exist: {time_source_field}")
        parse_type = _enum_config(
            task.config,
            "parse_type",
            default="datetime",
            allowed={"date", "time", "datetime"},
            node_type=self.node_type,
        )
        input_structure = _enum_config(
            task.config,
            "input_structure",
            default="auto",
            allowed={"auto", "strptime"},
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="new_field",
            allowed={"new_field", "overwrite_source", "overwrite"},
            node_type=self.node_type,
        )
        output_field = _parse_datetime_output_field(
            task.config,
            input_ref=input_ref,
            source_field=source_field,
            output_mode=output_mode,
        )
        output_status = _bool_config(task.config, "output_status", default=True)
        status_field = None
        if output_status:
            status_field = _optional_node_string_config(
                task.config,
                "status_field",
                default="parse_status",
                node_type=self.node_type,
            )
        output_schema = _parse_datetime_output_schema(
            input_ref.schema,
            output_field=output_field,
            output_mode=output_mode,
            status_field=status_field,
        )
        unmatched_mode = _enum_config(
            task.config,
            "unmatched_mode",
            default="empty",
            allowed={"empty", "keep_original", "fixed"},
            node_type=self.node_type,
        )

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    raw_value = row.get(source_field)
                    if time_source_field is not None:
                        raw_value = f"{raw_value} {row.get(time_source_field)}"
                    parsed = _parse_datetime_value(
                        raw_value,
                        config=task.config,
                        parse_type=parse_type,
                        input_structure=input_structure,
                    )
                    status = "parsed" if parsed is not None else "failed"
                    output_value = (
                        _format_parsed_datetime(
                            parsed,
                            config=task.config,
                            parse_type=parse_type,
                        )
                        if parsed is not None
                        else _parse_datetime_unmatched_value(
                            raw_value,
                            config=task.config,
                            unmatched_mode=unmatched_mode,
                        )
                    )
                    output_row = dict(row) | {output_field: output_value}
                    if status_field is not None:
                        output_row[status_field] = status
                    output_rows.append(output_row)
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=output_schema,
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
        table_name = _named_output_config(
            task.config,
            node_type=self.node_type,
            keys=("table_name",),
        )
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


class SaveRunTableNodeHandler:
    node_type = SAVE_RUN_TABLE_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        save_memory = _bool_config(
            task.config,
            "save_memory",
            default=True,
        )
        if not save_memory:
            return [input_ref]
        table_name = _named_output_config(
            task.config,
            node_type=self.node_type,
            keys=("transit_name", "table_name"),
        )
        mode = str(task.config.get("mode", "overwrite"))
        if mode != "overwrite":
            raise _NodeValidationError(
                f"Unsupported SaveRunTableNode mode: {mode}"
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
        skipped_reason = (
            "enable_write is false"
            if not enable_write
            else "write execution is not implemented"
        )
        status_row = {
            "status": "skipped",
            "source_type": source_type,
            "target_type": target_type,
            "target_table": target_table,
            "write_mode": write_mode,
            "overwrite_rule": overwrite_rule,
            "selected_field_count": len(selected_fields),
            "mapping_count": len(field_mappings),
            "source_row_count": context.count_rows(input_ref),
            "enable_write": _bool_status(enable_write),
            "backup_before_write": _bool_status(backup_before_write),
            "actual_write": "false",
            "selected_fields": ",".join(selected_fields),
            "target_fields": ",".join(target_fields),
            "skipped_reason": skipped_reason,
        }
        return [
            context.publish_rows(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=_write_selected_columns_status_schema(),
                rows=[status_row],
            )
        ]


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
        skipped_reason = (
            "enable_write is false"
            if not enable_write
            else "writeback execution is not implemented"
        )
        status_row = {
            "status": "skipped",
            "writeback_direction": direction,
            "source_table": source_table,
            "target_table": target_table,
            "use_match_rules": _bool_status(use_match_rules),
            "match_rule_count": match_rule_count,
            "field_mapping_count": len(field_mappings),
            "source_row_count": context.count_rows(input_ref),
            "enable_write": _bool_status(enable_write),
            "backup_before_write": _bool_status(backup_before_write),
            "output_preview_table": _bool_status(output_preview_table),
            "actual_write": "false",
            "overwrite_policy": overwrite_policy,
            "source_empty_policy": source_empty_policy,
            "no_match_policy": no_match_policy,
            "multi_match_policy": multi_match_policy,
            "duplicate_target_policy": duplicate_target_policy,
            "match_fields": match_fields,
            "mapped_fields": mapped_fields,
            "skipped_reason": skipped_reason,
        }
        return [
            context.publish_rows(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=_writeback_status_schema(),
                rows=[status_row],
            )
        ]


class ListFilesNodeHandler:
    node_type = LIST_FILES_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        if task.input_refs:
            raise _NodeValidationError("ListFilesNode does not accept inputs")
        directory = _list_files_directory_config(task.config)
        recursive = _bool_config(task.config, "recursive", default=False)
        include_files = _bool_config(task.config, "include_files", default=True)
        include_dirs = _bool_config(task.config, "include_dirs", default=False)
        if not include_files and not include_dirs:
            raise _NodeValidationError(
                "ListFilesNode must include files or directories"
            )
        include_hidden = _bool_config(
            task.config,
            "include_hidden",
            default=False,
        )
        extensions = _list_files_extensions_config(task.config)
        name_contains = _optional_string_config(
            task.config,
            "name_contains",
            node_type=self.node_type,
        )
        glob_pattern = _optional_string_config(
            task.config,
            "glob_pattern",
            default="*",
            node_type=self.node_type,
        )
        if not glob_pattern.strip():
            raise _NodeValidationError("ListFilesNode config.glob_pattern is required")
        max_files = _positive_int_config(
            task.config,
            "max_files",
            default=10_000,
            node_type=self.node_type,
        )
        rows = _list_file_rows(
            directory,
            recursive=recursive,
            include_files=include_files,
            include_dirs=include_dirs,
            include_hidden=include_hidden,
            extensions=extensions,
            name_contains=name_contains,
            glob_pattern=glob_pattern,
            max_files=max_files,
        )
        return [
            context.publish_rows(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=_list_files_schema(),
                rows=rows,
            )
        ]


class BatchRenameFilesNodeHandler:
    node_type = BATCH_RENAME_FILES_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        path_field = _node_string_config(
            task.config,
            "path_field",
            node_type=self.node_type,
        )
        new_name_field = _node_string_config(
            task.config,
            "new_name_field",
            node_type=self.node_type,
        )
        _require_fields(input_ref.schema, [path_field, new_name_field])
        name_value_type = _enum_config(
            task.config,
            "name_value_type",
            default="file_name",
            allowed={"file_name", "full_path"},
            node_type=self.node_type,
        )
        new_path_field = _optional_node_string_config(
            task.config,
            "new_path_field",
            default="new_path",
            node_type=self.node_type,
        )
        status_field = _optional_node_string_config(
            task.config,
            "status_field",
            default="rename_status",
            node_type=self.node_type,
        )
        if new_path_field == status_field:
            raise _NodeValidationError(
                "BatchRenameFilesNode new_path_field and status_field must differ"
            )
        auto_append_ext = _bool_config(task.config, "auto_append_ext", default=True)
        allow_dirs = _bool_config(task.config, "allow_dirs", default=False)
        create_target_dirs = _bool_config(
            task.config,
            "create_target_dirs",
            default=False,
        )
        conflict_mode = _enum_config(
            task.config,
            "conflict_mode",
            default="error",
            allowed={"error", "skip", "overwrite", "append_number"},
            node_type=self.node_type,
        )
        actual_rename = _bool_config(task.config, "actual_rename", default=False)
        write_log = _bool_config(task.config, "write_log", default=False)
        log_path = _optional_string_config(
            task.config,
            "log_path",
            node_type=self.node_type,
        )

        def output_batches():
            row_number = 1
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    output_rows.append(
                        _batch_rename_plan_row(
                            row,
                            row_number=row_number,
                            path_field=path_field,
                            new_name_field=new_name_field,
                            name_value_type=name_value_type,
                            new_path_field=new_path_field,
                            status_field=status_field,
                            auto_append_ext=auto_append_ext,
                            allow_dirs=allow_dirs,
                            create_target_dirs=create_target_dirs,
                            conflict_mode=conflict_mode,
                            actual_rename=actual_rename,
                            write_log=write_log,
                            log_path=log_path,
                        )
                    )
                    row_number += 1
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=_batch_rename_status_schema(
                    new_path_field=new_path_field,
                    status_field=status_field,
                ),
                row_batches=output_batches(),
            )
        ]


class PluginNodeHandler:
    node_type = PLUGIN_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        plugin_id = _node_string_config(
            task.config,
            "plugin_id",
            node_type=self.node_type,
        )
        plugin_version = _optional_string_config(
            task.config,
            "plugin_version",
            node_type=self.node_type,
        )
        params = _object_config(task.config, "params", node_type=self.node_type)
        input_bindings = _object_config(
            task.config,
            "input_bindings",
            node_type=self.node_type,
        )
        output_bindings = _object_config(
            task.config,
            "output_bindings",
            node_type=self.node_type,
        )
        execution_mode = _enum_config(
            task.config,
            "execution_mode",
            default="external_process",
            allowed={"in_process", "external_process"},
            node_type=self.node_type,
        )
        allow_external_actions = _bool_config(
            task.config,
            "allow_external_actions",
            default=False,
        )
        enable_execute = _bool_config(
            task.config,
            "enable_execute",
            default=False,
        )
        skipped_reason = (
            "enable_execute is false"
            if not enable_execute
            else "plugin execution is not implemented"
        )
        status_row = {
            "status": "skipped",
            "plugin_id": plugin_id,
            "plugin_version": plugin_version,
            "execution_mode": execution_mode,
            "input_ref_count": len(task.input_refs),
            "param_count": len(params),
            "input_binding_count": len(input_bindings),
            "output_binding_count": len(output_bindings),
            "allow_external_actions": _bool_status(allow_external_actions),
            "enable_execute": _bool_status(enable_execute),
            "actual_execute": "false",
            "skipped_reason": skipped_reason,
        }
        return [
            context.publish_rows(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=_plugin_status_schema(),
                rows=[status_row],
            )
        ]


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
            summary=_table_output_summary(output_refs),
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


def _table_output_summary(output_refs: list[TableRefModel]) -> dict[str, Any]:
    return {
        "output_ref_count": len(output_refs),
        "outputs": [
            {
                "table_ref_id": table_ref.table_ref_id,
                "logical_table_id": table_ref.logical_table_id,
                "role": table_ref.role.value,
                "storage_kind": table_ref.storage_kind.value,
            }
            for table_ref in output_refs
        ],
    }


def _simple_schema(fields: list[tuple[str, str, bool]]) -> list[FieldSchemaModel]:
    return [
        FieldSchemaModel(
            field_id=name,
            name=name,
            data_type=data_type,
            nullable=nullable,
            ordinal=index,
        )
        for index, (name, data_type, nullable) in enumerate(fields)
    ]


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


def _optional_non_negative_int_config(
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
    if value < 0:
        raise _NodeValidationError(f"{node_type} config.{key} must be non-negative")
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


def _named_output_config(
    config: dict[str, Any],
    *,
    node_type: str,
    keys: tuple[str, ...],
) -> str:
    for key in keys:
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    joined_keys = " or ".join(f"config.{key}" for key in keys)
    raise _NodeValidationError(f"{node_type} {joined_keys} is required")


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


def _optional_string_config(
    config: dict[str, Any],
    key: str,
    *,
    default: str = "",
    node_type: str,
) -> str:
    value = config.get(key, default)
    if not isinstance(value, str):
        raise _NodeValidationError(f"{node_type} config.{key} must be a string")
    return value


def _object_config(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> dict[str, Any]:
    value = config.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise _NodeValidationError(f"{node_type} config.{key} must be an object")
    return value


def _write_selected_target_table_config(
    config: dict[str, Any],
    *,
    target_type: str,
) -> str:
    if target_type in {"run_table", "memory_table"}:
        return _named_output_config(
            config,
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
            keys=("target_transit_table", "target_table"),
        )
    return _named_output_config(
        config,
        node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
        keys=("target_table",),
    )


def _write_selected_field_mappings_config(
    config: dict[str, Any],
    *,
    selected_fields: list[str],
) -> dict[str, str]:
    value = config.get("field_mappings", [])
    if value is None:
        return {}
    if not isinstance(value, list):
        raise _NodeValidationError(
            "WriteSelectedColumnsNode config.field_mappings must be a list"
        )
    selected = set(selected_fields)
    mappings: dict[str, str] = {}
    for item in value:
        if not isinstance(item, dict):
            raise _NodeValidationError(
                "WriteSelectedColumnsNode config.field_mappings must contain objects"
            )
        source_value = item.get("source_field", item.get("source"))
        target_value = item.get("target_field", item.get("target"))
        if not isinstance(source_value, str) or not source_value.strip():
            raise _NodeValidationError(
                "WriteSelectedColumnsNode field_mappings.source_field is required"
            )
        if not isinstance(target_value, str) or not target_value.strip():
            raise _NodeValidationError(
                "WriteSelectedColumnsNode field_mappings.target_field is required"
            )
        source_field = source_value.strip()
        target_field = target_value.strip()
        if source_field not in selected:
            raise _NodeValidationError(
                f"WriteSelectedColumnsNode mapping source is not selected: "
                f"{source_field}"
            )
        if source_field in mappings:
            raise _NodeValidationError(
                f"WriteSelectedColumnsNode duplicate mapping source: {source_field}"
            )
        mappings[source_field] = target_field
    return mappings


def _write_selected_target_fields(
    config: dict[str, Any],
    *,
    selected_fields: list[str],
    field_name_mode: str,
    field_mappings: dict[str, str],
) -> list[str]:
    if field_name_mode == "mapping":
        missing_mappings = [
            field
            for field in selected_fields
            if field not in field_mappings
        ]
        if missing_mappings:
            raise _NodeValidationError(
                "WriteSelectedColumnsNode field_mappings missing selected fields: "
                f"{', '.join(missing_mappings)}"
            )
        target_fields = [field_mappings[field] for field in selected_fields]
    elif field_name_mode == "prefix":
        prefix = _optional_string_config(
            config,
            "field_prefix",
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
        )
        target_fields = [f"{prefix}{field}" for field in selected_fields]
    elif field_name_mode == "suffix":
        suffix = _optional_string_config(
            config,
            "field_suffix",
            node_type=WRITE_SELECTED_COLUMNS_NODE_TYPE,
        )
        target_fields = [f"{field}{suffix}" for field in selected_fields]
    else:
        target_fields = list(selected_fields)
    duplicates = sorted(
        field
        for field in set(target_fields)
        if target_fields.count(field) > 1
    )
    if duplicates:
        raise _NodeValidationError(
            f"WriteSelectedColumnsNode target fields are duplicated: "
            f"{', '.join(duplicates)}"
        )
    return target_fields


def _write_selected_columns_status_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("status", "TEXT", False),
            ("source_type", "TEXT", False),
            ("target_type", "TEXT", False),
            ("target_table", "TEXT", False),
            ("write_mode", "TEXT", False),
            ("overwrite_rule", "TEXT", False),
            ("selected_field_count", "INTEGER", False),
            ("mapping_count", "INTEGER", False),
            ("source_row_count", "INTEGER", False),
            ("enable_write", "TEXT", False),
            ("backup_before_write", "TEXT", False),
            ("actual_write", "TEXT", False),
            ("selected_fields", "TEXT", False),
            ("target_fields", "TEXT", False),
            ("skipped_reason", "TEXT", False),
        ]
    )


def _bool_status(value: bool) -> str:
    return "true" if value else "false"


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
            ("target_table", "TEXT", False),
            ("use_match_rules", "TEXT", False),
            ("match_rule_count", "INTEGER", False),
            ("field_mapping_count", "INTEGER", False),
            ("source_row_count", "INTEGER", False),
            ("enable_write", "TEXT", False),
            ("backup_before_write", "TEXT", False),
            ("output_preview_table", "TEXT", False),
            ("actual_write", "TEXT", False),
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


def _list_files_directory_config(config: dict[str, Any]) -> Path:
    directory_value = config.get("directory")
    if not isinstance(directory_value, str) or not directory_value.strip():
        raise _NodeValidationError("ListFilesNode config.directory is required")
    directory = Path(directory_value).expanduser()
    try:
        directory = directory.resolve()
    except OSError as exc:
        raise _NodeValidationError(str(exc)) from exc
    if not directory.exists():
        raise _NodeValidationError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        raise _NodeValidationError(f"Path is not a directory: {directory}")
    return directory


def _list_files_extensions_config(config: dict[str, Any]) -> set[str] | None:
    value = config.get("extensions")
    if value in (None, ""):
        return None
    if not isinstance(value, list):
        raise _NodeValidationError("ListFilesNode config.extensions must be a list")
    extensions: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise _NodeValidationError(
                "ListFilesNode config.extensions must contain strings"
            )
        extension = item.strip().lower()
        if not extension.startswith("."):
            extension = f".{extension}"
        extensions.add(extension)
    return extensions or None


def _list_file_rows(
    directory: Path,
    *,
    recursive: bool,
    include_files: bool,
    include_dirs: bool,
    include_hidden: bool,
    extensions: set[str] | None,
    name_contains: str,
    glob_pattern: str,
    max_files: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pending_dirs = [directory]
    while pending_dirs and len(rows) < max_files:
        current_dir = pending_dirs.pop()
        try:
            entries = sorted(
                current_dir.iterdir(),
                key=lambda path: path.name.lower(),
            )
        except OSError as exc:
            raise _NodeValidationError(str(exc)) from exc
        for entry in entries:
            if len(rows) >= max_files:
                break
            if not include_hidden and _is_hidden_entry(entry, directory):
                continue
            try:
                is_dir = entry.is_dir()
                is_file = entry.is_file()
            except OSError:
                continue
            if recursive and is_dir and not entry.is_symlink():
                pending_dirs.append(entry)
            if not _list_files_entry_matches(
                entry,
                is_dir=is_dir,
                is_file=is_file,
                include_files=include_files,
                include_dirs=include_dirs,
                extensions=extensions,
                name_contains=name_contains,
                glob_pattern=glob_pattern,
            ):
                continue
            rows.append(
                _list_file_row(
                    entry,
                    directory,
                    is_dir=is_dir,
                    is_file=is_file,
                )
            )
    return rows


def _list_files_entry_matches(
    entry: Path,
    *,
    is_dir: bool,
    is_file: bool,
    include_files: bool,
    include_dirs: bool,
    extensions: set[str] | None,
    name_contains: str,
    glob_pattern: str,
) -> bool:
    if is_file and not include_files:
        return False
    if is_dir and not include_dirs:
        return False
    if not is_file and not is_dir:
        return False
    if is_file and extensions is not None and entry.suffix.lower() not in extensions:
        return False
    if name_contains and name_contains not in entry.name:
        return False
    return fnmatch.fnmatch(entry.name, glob_pattern)


def _is_hidden_entry(entry: Path, root: Path) -> bool:
    try:
        relative_parts = entry.relative_to(root).parts
    except ValueError:
        relative_parts = entry.parts
    return any(part.startswith(".") for part in relative_parts)


def _list_file_row(
    entry: Path,
    root: Path,
    *,
    is_dir: bool,
    is_file: bool,
) -> dict[str, Any]:
    try:
        stat_result = entry.stat()
    except OSError:
        stat_result = None
    relative_path = entry.relative_to(root).as_posix()
    return {
        "name": entry.name,
        "path": str(entry),
        "parent_path": str(entry.parent),
        "relative_path": relative_path,
        "extension": "" if is_dir else entry.suffix.lower(),
        "stem": entry.stem,
        "is_dir": _bool_status(is_dir),
        "is_file": _bool_status(is_file),
        "is_symlink": _bool_status(entry.is_symlink()),
        "size_bytes": (
            stat_result.st_size
            if stat_result is not None and is_file
            else None
        ),
        "modified_at": (
            datetime.fromtimestamp(
                stat_result.st_mtime,
                tz=UTC,
            ).isoformat()
            if stat_result is not None
            else None
        ),
    }


def _list_files_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("name", "TEXT", False),
            ("path", "TEXT", False),
            ("parent_path", "TEXT", False),
            ("relative_path", "TEXT", False),
            ("extension", "TEXT", False),
            ("stem", "TEXT", False),
            ("is_dir", "TEXT", False),
            ("is_file", "TEXT", False),
            ("is_symlink", "TEXT", False),
            ("size_bytes", "INTEGER", True),
            ("modified_at", "TEXT", True),
        ]
    )


def _require_fields(
    schema: list[FieldSchemaModel],
    field_names: list[str],
) -> None:
    missing_fields = [
        field_name
        for field_name in field_names
        if find_field(schema, field_name) is None
    ]
    if missing_fields:
        raise _NodeValidationError(
            f"Fields do not exist: {', '.join(missing_fields)}"
        )


def _batch_rename_plan_row(
    row: dict[str, Any],
    *,
    row_number: int,
    path_field: str,
    new_name_field: str,
    name_value_type: str,
    new_path_field: str,
    status_field: str,
    auto_append_ext: bool,
    allow_dirs: bool,
    create_target_dirs: bool,
    conflict_mode: str,
    actual_rename: bool,
    write_log: bool,
    log_path: str,
) -> dict[str, Any]:
    original_value = row.get(path_field)
    new_name_value = row.get(new_name_field)
    if not isinstance(original_value, str) or not original_value.strip():
        return _batch_rename_status_row(
            row_number=row_number,
            original_path="" if original_value is None else str(original_value),
            new_path="",
            new_path_field=new_path_field,
            status_field=status_field,
            status="failed",
            error_message="source path is required",
            actual_rename=actual_rename,
            write_log=write_log,
            log_path=log_path,
        )
    if not isinstance(new_name_value, str) or not new_name_value.strip():
        return _batch_rename_status_row(
            row_number=row_number,
            original_path=original_value,
            new_path="",
            new_path_field=new_path_field,
            status_field=status_field,
            status="failed",
            error_message="new name is required",
            actual_rename=actual_rename,
            write_log=write_log,
            log_path=log_path,
        )
    source_path = Path(original_value).expanduser()
    target_path = _batch_rename_target_path(
        source_path,
        new_name_value.strip(),
        name_value_type=name_value_type,
        auto_append_ext=auto_append_ext,
    )
    status = "planned"
    error_message = ""
    skipped_reason = ""
    try:
        source_exists = source_path.exists()
        source_is_dir = source_path.is_dir() if source_exists else False
        target_exists = target_path.exists()
    except OSError as exc:
        source_exists = False
        source_is_dir = False
        target_exists = False
        status = "failed"
        error_message = str(exc)
    if status != "failed" and not source_exists:
        status = "failed"
        error_message = "source path does not exist"
    elif status != "failed" and source_is_dir and not allow_dirs:
        status = "failed"
        error_message = "directories are not allowed"
    elif status != "failed" and not target_path.parent.exists():
        if create_target_dirs:
            status = "planned"
        else:
            status = "failed"
            error_message = "target directory does not exist"
    elif status != "failed" and target_exists:
        if conflict_mode == "error":
            status = "failed"
            error_message = "target path already exists"
        elif conflict_mode == "skip":
            status = "skipped"
            skipped_reason = "target path already exists"
    if status == "planned" and actual_rename:
        status = "skipped"
        skipped_reason = "rename execution is not implemented"
    return _batch_rename_status_row(
        row_number=row_number,
        original_path=str(source_path),
        new_path=str(target_path),
        new_path_field=new_path_field,
        status_field=status_field,
        status=status,
        error_message=error_message,
        skipped_reason=skipped_reason,
        actual_rename=actual_rename,
        write_log=write_log,
        log_path=log_path,
    )


def _batch_rename_target_path(
    source_path: Path,
    new_name: str,
    *,
    name_value_type: str,
    auto_append_ext: bool,
) -> Path:
    if name_value_type == "full_path":
        target_path = Path(new_name).expanduser()
    else:
        target_path = source_path.with_name(new_name)
    if auto_append_ext and source_path.suffix and not target_path.suffix:
        target_path = target_path.with_suffix(source_path.suffix)
    return target_path


def _batch_rename_status_row(
    *,
    row_number: int,
    original_path: str,
    new_path: str,
    new_path_field: str,
    status_field: str,
    status: str,
    error_message: str,
    actual_rename: bool,
    write_log: bool,
    log_path: str,
    skipped_reason: str = "",
) -> dict[str, Any]:
    return {
        "source_row_number": row_number,
        "original_path": original_path,
        new_path_field: new_path,
        status_field: status,
        "error_message": error_message,
        "rename_requested": _bool_status(actual_rename),
        "actual_rename": "false",
        "write_log": _bool_status(write_log),
        "log_path": log_path,
        "skipped_reason": skipped_reason,
    }


def _batch_rename_status_schema(
    *,
    new_path_field: str,
    status_field: str,
) -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("source_row_number", "INTEGER", False),
            ("original_path", "TEXT", False),
            (new_path_field, "TEXT", False),
            (status_field, "TEXT", False),
            ("error_message", "TEXT", False),
            ("rename_requested", "TEXT", False),
            ("actual_rename", "TEXT", False),
            ("write_log", "TEXT", False),
            ("log_path", "TEXT", False),
            ("skipped_reason", "TEXT", False),
        ]
    )


def _plugin_status_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("status", "TEXT", False),
            ("plugin_id", "TEXT", False),
            ("plugin_version", "TEXT", False),
            ("execution_mode", "TEXT", False),
            ("input_ref_count", "INTEGER", False),
            ("param_count", "INTEGER", False),
            ("input_binding_count", "INTEGER", False),
            ("output_binding_count", "INTEGER", False),
            ("allow_external_actions", "TEXT", False),
            ("enable_execute", "TEXT", False),
            ("actual_execute", "TEXT", False),
            ("skipped_reason", "TEXT", False),
        ]
    )


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


def _copy_row_source_row(
    context: BuiltinTableNodeContext,
    *,
    input_ref: TableRefModel,
    source_row_number: int,
) -> dict[str, Any]:
    row_number = 1
    for rows in context.iter_row_batches(input_ref):
        for row in rows:
            if row_number == source_row_number:
                return dict(row)
            row_number += 1
    raise _NodeValidationError("CopyRowsNode config.source_row is out of range")


def _copy_row_batches(
    source_row: dict[str, Any],
    *,
    copy_count: int,
    batch_size: int,
):
    remaining = copy_count
    while remaining > 0:
        current_batch_size = min(remaining, batch_size)
        yield [
            dict(source_row)
            for _ in range(current_batch_size)
        ]
        remaining -= current_batch_size


def _deduplicate_key_fields(
    config: dict[str, Any],
    input_ref: TableRefModel,
) -> list[str]:
    dedupe_mode = _enum_config(
        config,
        "dedupe_mode",
        default="key_fields",
        allowed={"key_fields", "entire_row"},
        node_type=DEDUPLICATE_ROWS_NODE_TYPE,
    )
    if dedupe_mode == "entire_row":
        return [field.name for field in input_ref.schema]
    key_fields = _string_list_config(
        config,
        "key_fields",
        node_type=DEDUPLICATE_ROWS_NODE_TYPE,
    )
    missing_fields = [
        field_name
        for field_name in key_fields
        if not has_field(input_ref.schema, field_name)
    ]
    if missing_fields:
        raise _NodeValidationError(
            f"Fields do not exist: {', '.join(missing_fields)}"
        )
    return key_fields


def _deduplicate_groups(
    context: BuiltinTableNodeContext,
    *,
    input_ref: TableRefModel,
    key_fields: list[str],
    trim: bool,
    ignore_case: bool,
    empty_key_policy: str,
) -> dict[tuple[Any, ...], dict[str, int]]:
    groups: dict[tuple[Any, ...], dict[str, int]] = {}
    row_number = 1
    for rows in context.iter_row_batches(input_ref):
        for row in rows:
            key = _deduplicate_key(
                row,
                key_fields=key_fields,
                trim=trim,
                ignore_case=ignore_case,
                empty_key_policy=empty_key_policy,
            )
            if key is not None:
                group = groups.setdefault(
                    key,
                    {
                        "count": 0,
                        "first": row_number,
                        "last": row_number,
                    },
                )
                group["count"] += 1
                group["last"] = row_number
            row_number += 1
    return groups


def _deduplicate_key(
    row: dict[str, Any],
    *,
    key_fields: list[str],
    trim: bool,
    ignore_case: bool,
    empty_key_policy: str,
) -> tuple[Any, ...] | None:
    key_values = tuple(
        _deduplicate_key_value(
            row.get(field_name),
            trim=trim,
            ignore_case=ignore_case,
        )
        for field_name in key_fields
    )
    if empty_key_policy == "skip" and all(
        _is_empty_cell(value)
        for value in key_values
    ):
        return None
    return key_values


def _deduplicate_key_value(value: Any, *, trim: bool, ignore_case: bool) -> Any:
    normalized = value
    if isinstance(normalized, str):
        if trim:
            normalized = normalized.strip()
        if ignore_case:
            normalized = normalized.lower()
    try:
        hash(normalized)
    except TypeError:
        return ("repr", type(normalized).__name__, repr(normalized))
    return normalized


def _deduplicate_should_keep(
    row_number: int,
    *,
    key: tuple[Any, ...] | None,
    groups: dict[tuple[Any, ...], dict[str, int]],
    keep_policy: str,
) -> bool:
    if key is None:
        return True
    group = groups[key]
    if group["count"] <= 1 or keep_policy == "all":
        return True
    if keep_policy == "first":
        return row_number == group["first"]
    return row_number == group["last"]


def _deduplicate_occurrence_index(
    occurrence_counts: dict[tuple[Any, ...], int],
    key: tuple[Any, ...] | None,
) -> int:
    if key is None:
        return 1
    occurrence_counts[key] = occurrence_counts.get(key, 0) + 1
    return occurrence_counts[key]


def _deduplicate_marker_fields(config: dict[str, Any]) -> dict[str, str]:
    return {
        "group": _optional_node_string_config(
            config,
            "duplicate_group_field",
            default="_duplicate_group",
            node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        ),
        "status": _optional_node_string_config(
            config,
            "duplicate_status_field",
            default="_duplicate_status",
            node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        ),
        "index": _optional_node_string_config(
            config,
            "duplicate_index_field",
            default="_duplicate_index",
            node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        ),
        "count": _optional_node_string_config(
            config,
            "duplicate_count_field",
            default="_duplicate_count",
            node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        ),
        "keep": _optional_node_string_config(
            config,
            "keep_flag_field",
            default="_keep_row",
            node_type=DEDUPLICATE_ROWS_NODE_TYPE,
        ),
    }


def _deduplicate_output_schema(
    input_schema: list[FieldSchemaModel],
    marker_fields: dict[str, str],
) -> list[FieldSchemaModel]:
    marker_names = list(marker_fields.values())
    duplicate_marker_names = [
        field_name
        for index, field_name in enumerate(marker_names)
        if field_name in marker_names[:index]
    ]
    if duplicate_marker_names:
        raise _NodeValidationError(
            f"DeduplicateRowsNode marker fields are duplicated: "
            f"{', '.join(duplicate_marker_names)}"
        )
    existing_marker_fields = [
        field_name
        for field_name in marker_names
        if has_field(input_schema, field_name)
    ]
    if existing_marker_fields:
        raise _NodeValidationError(
            f"Fields already exist: {', '.join(existing_marker_fields)}"
        )
    schema = append_field(
        input_schema,
        name=marker_fields["group"],
        data_type="TEXT",
        nullable=True,
    )
    schema = append_field(
        schema,
        name=marker_fields["status"],
        data_type="TEXT",
        nullable=False,
    )
    schema = append_field(
        schema,
        name=marker_fields["index"],
        data_type="INTEGER",
        nullable=False,
    )
    schema = append_field(
        schema,
        name=marker_fields["count"],
        data_type="INTEGER",
        nullable=False,
    )
    return append_field(
        schema,
        name=marker_fields["keep"],
        data_type="BOOLEAN",
        nullable=False,
    )


def _deduplicate_marker_values(
    *,
    key: tuple[Any, ...] | None,
    groups: dict[tuple[Any, ...], dict[str, int]],
    occurrence_index: int,
    keep_row: bool,
    marker_fields: dict[str, str],
) -> dict[str, Any]:
    if key is None:
        return {
            marker_fields["group"]: None,
            marker_fields["status"]: "skipped_empty_key",
            marker_fields["index"]: occurrence_index,
            marker_fields["count"]: 1,
            marker_fields["keep"]: True,
        }
    group = groups[key]
    group_count = group["count"]
    if group_count <= 1:
        status = "unique"
    elif keep_row:
        status = "kept"
    else:
        status = "duplicate"
    return {
        marker_fields["group"]: f"group-{group['first']}",
        marker_fields["status"]: status,
        marker_fields["index"]: occurrence_index,
        marker_fields["count"]: group_count,
        marker_fields["keep"]: keep_row,
    }


def _advanced_filter_conditions(
    config: dict[str, Any],
    input_ref: TableRefModel,
) -> list[dict[str, Any]]:
    raw_conditions = config.get("conditions", [])
    if raw_conditions is None:
        raw_conditions = []
    if not isinstance(raw_conditions, list):
        raise _NodeValidationError(
            "AdvancedFilterRowsNode config.conditions must be a list"
        )
    conditions: list[dict[str, Any]] = []
    for index, item in enumerate(raw_conditions):
        if not isinstance(item, dict):
            raise _NodeValidationError(
                "AdvancedFilterRowsNode config.conditions must contain objects"
            )
        field = item.get("field")
        if not isinstance(field, str) or not field.strip():
            raise _NodeValidationError(
                f"AdvancedFilterRowsNode conditions[{index}].field is required"
            )
        field = field.strip()
        if find_field(input_ref.schema, field) is None:
            raise _NodeValidationError(f"Field does not exist: {field}")
        operator = _normalize_condition_operator(
            item.get("operator", item.get("op")),
            node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
            key=f"conditions[{index}].operator",
        )
        value_source = _value_source_from_mapping(
            item,
            value_key="value",
            value_source_key="value_source",
            value_field_key="value_field",
            node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
        )
        if (
            value_source.field is not None
            and find_field(input_ref.schema, value_source.field) is None
        ):
            raise _NodeValidationError(f"Field does not exist: {value_source.field}")
        case_sensitive = item.get("case_sensitive", True)
        if not isinstance(case_sensitive, bool):
            raise _NodeValidationError(
                "AdvancedFilterRowsNode condition.case_sensitive must be a boolean"
            )
        conditions.append(
            {
                "field": field,
                "operator": operator,
                "value_source": value_source,
                "case_sensitive": case_sensitive,
            }
        )
    return conditions


def _value_source_from_mapping(
    mapping: dict[str, Any],
    *,
    value_key: str,
    value_source_key: str,
    value_field_key: str,
    node_type: str,
):
    if value_source_key in mapping:
        raw_value_source = mapping.get(value_source_key)
    elif mapping.get(value_field_key) is not None:
        value_field = mapping.get(value_field_key)
        if not isinstance(value_field, str) or not value_field.strip():
            raise _NodeValidationError(f"{node_type} {value_field_key} is required")
        raw_value_source = {
            "mode": "row_field",
            "field": value_field.strip(),
        }
    else:
        raw_value_source = mapping.get(value_key)
    try:
        return parse_value_source(raw_value_source)
    except ValueSourceError as exc:
        raise _NodeValidationError(str(exc)) from exc


def _advanced_filter_output_fields(
    config: dict[str, Any],
    input_ref: TableRefModel,
) -> list[str]:
    raw_output_fields = config.get("output_fields")
    if raw_output_fields is None or raw_output_fields == []:
        return [field.name for field in input_ref.schema]
    output_fields = _string_list_config(
        config,
        "output_fields",
        node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
    )
    missing_fields = [
        field_name
        for field_name in output_fields
        if not has_field(input_ref.schema, field_name)
    ]
    if missing_fields:
        raise _NodeValidationError(
            f"Fields do not exist: {', '.join(missing_fields)}"
        )
    return output_fields


def _advanced_filter_row_matches(
    row: dict[str, Any],
    *,
    conditions: list[dict[str, Any]],
    logic: str,
) -> bool:
    if not conditions:
        return True
    if logic == "and":
        for condition in conditions:
            if not _advanced_filter_condition_matches(row, condition):
                return False
        return True
    for condition in conditions:
        if _advanced_filter_condition_matches(row, condition):
            return True
    return False


def _advanced_filter_condition_matches(
    row: dict[str, Any],
    condition: dict[str, Any],
) -> bool:
    value = condition["value_source"].resolve(row)
    return _condition_cell_matches(
        row.get(condition["field"]),
        operator=condition["operator"],
        value=value,
        case_sensitive=condition["case_sensitive"],
    )


def _extract_text_output_field(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    source_field: str,
    output_mode: str,
) -> str:
    if output_mode == "overwrite_source":
        return source_field
    key = "new_field" if output_mode == "new_field" else "target_field"
    output_field = _node_string_config(
        config,
        key,
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    if output_mode == "new_field":
        if has_field(input_ref.schema, output_field):
            raise _NodeValidationError(f"Field already exists: {output_field}")
    elif find_field(input_ref.schema, output_field) is None:
        raise _NodeValidationError(f"Field does not exist: {output_field}")
    return output_field


def _extract_text_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    output_field: str,
    output_mode: str,
) -> list[FieldSchemaModel]:
    if output_mode == "new_field":
        return append_field(
            input_schema,
            name=output_field,
            data_type="TEXT",
            nullable=True,
        )
    return replace_field_schema(
        input_schema,
        output_field,
        data_type="TEXT",
        nullable=True,
    )


def _extract_text_rule_fallback_key(method: str) -> str:
    if method == "regex":
        return "regex_pattern"
    if method == "delimiter":
        return "delimiter"
    return "rule_value"


def _extract_text_value(
    source_value: Any,
    *,
    row: dict[str, Any],
    config: dict[str, Any],
    method: str,
    rule_source,
    strip_result: bool,
) -> str | None:
    source_text = "" if source_value is None else str(source_value)
    if method == "regex":
        result = _extract_text_regex(
            source_text,
            row=row,
            config=config,
            rule_source=rule_source,
        )
    elif method == "position":
        result = _extract_text_position(source_text, config=config)
    elif method == "left":
        result = _extract_text_left(source_text, config=config)
    elif method == "right":
        result = _extract_text_right(source_text, config=config)
    elif method == "delimiter":
        result = _extract_text_delimiter(
            source_text,
            row=row,
            config=config,
            rule_source=rule_source,
        )
    elif method == "between":
        result = _extract_text_between(source_text, config=config)
    else:
        raise _NodeValidationError(f"Unsupported ExtractTextNode method: {method}")
    if result is not None and strip_result:
        return result.strip()
    return result


def _extract_text_regex(
    source_text: str,
    *,
    row: dict[str, Any],
    config: dict[str, Any],
    rule_source,
) -> str | None:
    pattern = rule_source.resolve(row)
    if pattern is None or str(pattern) == "":
        raise _NodeValidationError("ExtractTextNode regex pattern is required")
    match = re.search(str(pattern), source_text)
    if match is None:
        return None
    regex_group = _non_negative_int_config(
        config,
        "regex_group",
        default=0,
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    try:
        return match.group(regex_group)
    except IndexError:
        return None


def _extract_text_position(source_text: str, *, config: dict[str, Any]) -> str | None:
    start_pos = _non_negative_int_config(
        config,
        "start_pos",
        default=1,
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    position_base = _enum_config(
        config,
        "position_base",
        default="one",
        allowed={"zero", "one"},
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    start_index = start_pos if position_base == "zero" else start_pos - 1
    if start_index < 0 or start_index >= len(source_text):
        return None
    extract_len = _optional_positive_int_config(
        config,
        "extract_len",
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    if extract_len is None:
        return source_text[start_index:]
    return source_text[start_index:start_index + extract_len]


def _extract_text_left(source_text: str, *, config: dict[str, Any]) -> str:
    n_chars = _extract_text_n_chars(config)
    return source_text[:n_chars]


def _extract_text_right(source_text: str, *, config: dict[str, Any]) -> str:
    n_chars = _extract_text_n_chars(config)
    return source_text[-n_chars:] if n_chars > 0 else ""


def _extract_text_n_chars(config: dict[str, Any]) -> int:
    if config.get("n_chars") is not None:
        return _positive_int_config(
            config,
            "n_chars",
            default=1,
            node_type=EXTRACT_TEXT_NODE_TYPE,
        )
    return _positive_int_config(
        config,
        "extract_len",
        default=1,
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )


def _extract_text_delimiter(
    source_text: str,
    *,
    row: dict[str, Any],
    config: dict[str, Any],
    rule_source,
) -> str | None:
    delimiter = rule_source.resolve(row)
    if delimiter is None or str(delimiter) == "":
        raise _NodeValidationError("ExtractTextNode delimiter is required")
    parts = source_text.split(str(delimiter))
    part_index = _int_config(config, "part_index", default=1)
    position_base = _enum_config(
        config,
        "position_base",
        default="one",
        allowed={"zero", "one"},
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    selected_index = part_index if position_base == "zero" else part_index - 1
    if selected_index < 0 or selected_index >= len(parts):
        return None
    return parts[selected_index]


def _extract_text_between(source_text: str, *, config: dict[str, Any]) -> str | None:
    before_key = _node_string_config(
        config,
        "before_key",
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    after_key = _node_string_config(
        config,
        "after_key",
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    start_index = source_text.find(before_key)
    if start_index < 0:
        return None
    content_start = start_index + len(before_key)
    end_index = source_text.find(after_key, content_start)
    if end_index < 0:
        return None
    return source_text[content_start:end_index]


def _extract_text_unmatched_value(
    row: dict[str, Any],
    *,
    source_value: Any,
    unmatched_mode: str,
    unmatched_source,
) -> Any:
    if unmatched_mode == "empty":
        return ""
    if unmatched_mode == "keep_original":
        return source_value
    if unmatched_mode == "fixed":
        return unmatched_source.resolve(row)
    if unmatched_mode == "skip_row":
        return _SKIP_ROW
    raise _NodeValidationError(
        f"Unsupported ExtractTextNode unmatched_mode: {unmatched_mode}"
    )


def _lookup_matched_output_fields(config: dict[str, Any]) -> _LookupMatchedOutputFields:
    output_fields: _LookupMatchedOutputFields = {
        "field": _optional_node_string_config(
            config,
            "output_field",
            default="matched_field",
            node_type=LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
        ),
        "value": None,
        "row": None,
        "status": None,
    }
    if _bool_config(config, "output_match_value", default=False):
        output_fields["value"] = _optional_node_string_config(
            config,
            "match_value_field",
            default="matched_value",
            node_type=LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
        )
    if _bool_config(config, "output_match_row", default=False):
        output_fields["row"] = _optional_node_string_config(
            config,
            "match_row_field",
            default="matched_row",
            node_type=LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
        )
    if _bool_config(config, "output_status", default=True):
        output_fields["status"] = _optional_node_string_config(
            config,
            "status_field",
            default="match_status",
            node_type=LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
        )
    return output_fields


def _lookup_matched_output_schema(
    input_schema: list[FieldSchemaModel],
    output_fields: _LookupMatchedOutputFields,
) -> list[FieldSchemaModel]:
    field_names_to_add = [
        field_name
        for field_name in (
            output_fields["field"],
            output_fields["value"],
            output_fields["row"],
            output_fields["status"],
        )
        if field_name is not None
    ]
    duplicate_field_names = [
        field_name
        for index, field_name in enumerate(field_names_to_add)
        if field_name in field_names_to_add[:index]
    ]
    if duplicate_field_names:
        raise _NodeValidationError(
            f"LookupMatchedFieldNameNode output fields are duplicated: "
            f"{', '.join(duplicate_field_names)}"
        )
    existing_fields = [
        field_name
        for field_name in field_names_to_add
        if has_field(input_schema, field_name)
    ]
    if existing_fields:
        raise _NodeValidationError(
            f"Fields already exist: {', '.join(existing_fields)}"
        )
    schema = list(input_schema)
    schema = append_field(
        schema,
        name=output_fields["field"],
        data_type="TEXT",
        nullable=True,
    )
    if output_fields["value"] is not None:
        schema = append_field(
            schema,
            name=output_fields["value"],
            data_type="TEXT",
            nullable=True,
        )
    if output_fields["row"] is not None:
        schema = append_field(
            schema,
            name=output_fields["row"],
            data_type="INTEGER",
            nullable=True,
        )
    if output_fields["status"] is not None:
        schema = append_field(
            schema,
            name=output_fields["status"],
            data_type="TEXT",
            nullable=False,
        )
    return schema


def _lookup_matched_field_index(
    context: BuiltinTableNodeContext,
    *,
    lookup_ref: TableRefModel,
    lookup_fields: list[str],
    match_mode: str,
) -> dict[Any, list[dict[str, Any]]]:
    if match_mode != "equals":
        raise _NodeValidationError(
            f"Unsupported LookupMatchedFieldNameNode match_mode: {match_mode}"
        )
    index: dict[Any, list[dict[str, Any]]] = {}
    row_number = 1
    for rows in context.iter_row_batches(lookup_ref):
        for row in rows:
            for field_name in lookup_fields:
                value = row.get(field_name)
                try:
                    hash(value)
                except TypeError:
                    value = ("repr", type(value).__name__, repr(value))
                index.setdefault(value, []).append(
                    {
                        "field": field_name,
                        "value": row.get(field_name),
                        "row": row_number,
                    }
                )
            row_number += 1
    return index


def _lookup_matched_select_match(
    matches: list[dict[str, Any]],
    *,
    multi_match_policy: str,
) -> dict[str, Any] | None:
    if not matches:
        return None
    if multi_match_policy == "last":
        return matches[-1]
    return matches[0]


def _lookup_matched_values(
    match: dict[str, Any] | None,
    *,
    match_count: int,
    output_fields: _LookupMatchedOutputFields,
    no_match_value: Any,
) -> dict[str, Any]:
    if match is None:
        values: dict[str, Any] = {
            output_fields["field"]: no_match_value,
        }
        if output_fields["value"] is not None:
            values[output_fields["value"]] = no_match_value
        if output_fields["row"] is not None:
            values[output_fields["row"]] = None
        if output_fields["status"] is not None:
            values[output_fields["status"]] = "not_matched"
        return values
    values = {
        output_fields["field"]: match["field"],
    }
    if output_fields["value"] is not None:
        values[output_fields["value"]] = match["value"]
    if output_fields["row"] is not None:
        values[output_fields["row"]] = match["row"]
    if output_fields["status"] is not None:
        values[output_fields["status"]] = (
            "multiple_matched"
            if match_count > 1
            else "matched"
        )
    return values


def _merge_columns_separators(
    config: dict[str, Any],
    *,
    field_count: int,
) -> list[str]:
    separator_count = max(0, field_count - 1)
    raw_separators = config.get("separators", [""] * separator_count)
    if isinstance(raw_separators, str):
        return [raw_separators] * separator_count
    if not isinstance(raw_separators, list):
        raise _NodeValidationError("MergeColumnsNode config.separators must be a list")
    if separator_count == 0:
        return []
    if len(raw_separators) == 1:
        separator = raw_separators[0]
        if not isinstance(separator, str):
            raise _NodeValidationError(
                "MergeColumnsNode config.separators must contain strings"
            )
        return [separator] * separator_count
    if len(raw_separators) != separator_count:
        raise _NodeValidationError(
            "MergeColumnsNode config.separators must contain one separator or "
            "field_count - 1 separators"
        )
    separators: list[str] = []
    for separator in raw_separators:
        if not isinstance(separator, str):
            raise _NodeValidationError(
                "MergeColumnsNode config.separators must contain strings"
            )
        separators.append(separator)
    return separators


def _merge_columns_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    output_field: str,
    conflict_mode: str,
) -> list[FieldSchemaModel]:
    if has_field(input_schema, output_field):
        if conflict_mode == "error":
            raise _NodeValidationError(f"Field already exists: {output_field}")
        return replace_field_schema(
            input_schema,
            output_field,
            data_type="TEXT",
            nullable=True,
        )
    return append_field(
        input_schema,
        name=output_field,
        data_type="TEXT",
        nullable=True,
    )


def _merge_columns_value(
    row: dict[str, Any],
    *,
    fields: list[str],
    separators: list[str],
    skip_empty: bool,
    trim_value: bool,
    empty_placeholder: Any,
) -> str:
    values: list[str] = []
    for field_name in fields:
        value = row.get(field_name)
        if value is None:
            text_value = ""
        else:
            text_value = str(value)
        if trim_value:
            text_value = text_value.strip()
        if _is_empty_cell(text_value):
            if skip_empty:
                continue
            text_value = "" if empty_placeholder is None else str(empty_placeholder)
        values.append(text_value)
    if skip_empty:
        separator = separators[0] if separators else ""
        return separator.join(values)
    merged = ""
    for index, value in enumerate(values):
        if index > 0:
            merged += separators[index - 1]
        merged += value
    return merged


def _numeric_output_field(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    target_field: str,
    output_mode: str,
) -> str:
    if output_mode == "overwrite":
        return target_field
    output_field = _optional_node_string_config(
        config,
        "output_field",
        default=f"{target_field}_result",
        node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
    )
    if has_field(input_ref.schema, output_field):
        raise _NodeValidationError(f"Field already exists: {output_field}")
    return output_field


def _numeric_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    output_field: str,
    output_mode: str,
) -> list[FieldSchemaModel]:
    if output_mode == "new_field":
        return append_field(
            input_schema,
            name=output_field,
            data_type="FLOAT",
            nullable=True,
        )
    return replace_field_schema(
        input_schema,
        output_field,
        data_type="FLOAT",
        nullable=True,
    )


def _numeric_row_selector(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> dict[str, Any]:
    range_mode = _enum_config(
        config,
        "range_mode",
        default="all",
        allowed={"all", "row_range", "reference_non_empty"},
        node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
    )
    selector: dict[str, Any] = {"range_mode": range_mode}
    if range_mode == "row_range":
        start_row = _positive_int_config(
            config,
            "start_row",
            default=1,
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        )
        end_row = _optional_positive_int_config(
            config,
            "end_row",
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        )
        if end_row is not None and start_row > end_row:
            raise _NodeValidationError(
                "NumericColumnOperationNode start_row must be <= end_row"
            )
        selector |= {"start_row": start_row, "end_row": end_row}
    elif range_mode == "reference_non_empty":
        reference_field = _node_string_config(
            config,
            "reference_field",
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        )
        if find_field(input_ref.schema, reference_field) is None:
            raise _NodeValidationError(f"Field does not exist: {reference_field}")
        selector["reference_field"] = reference_field
    return selector


def _numeric_row_selected(
    row: dict[str, Any],
    *,
    row_number: int,
    selector: dict[str, Any],
) -> bool:
    range_mode = selector["range_mode"]
    if range_mode == "all":
        return True
    if range_mode == "row_range":
        end_row = selector.get("end_row")
        if end_row is None:
            return row_number >= selector["start_row"]
        return selector["start_row"] <= row_number <= end_row
    if range_mode == "reference_non_empty":
        return not _is_empty_cell(row.get(selector["reference_field"]))
    return True


def _numeric_operand_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> dict[str, Any]:
    operand_source = _enum_config(
        config,
        "operand_source",
        default="literal",
        allowed={"literal", "row_field", "row_number", "sequence"},
        node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
    )
    operand_config: dict[str, Any] = {"operand_source": operand_source}
    if operand_source == "literal":
        operand_config["value"] = config.get("operand_value", 0)
    elif operand_source == "row_field":
        operand_field = _node_string_config(
            config,
            "operand_field",
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        )
        if find_field(input_ref.schema, operand_field) is None:
            raise _NodeValidationError(f"Field does not exist: {operand_field}")
        operand_config["field"] = operand_field
    elif operand_source == "sequence":
        operand_config["start"] = _number_config(
            config,
            "sequence_start",
            default=1,
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        )
        operand_config["step"] = _number_config(
            config,
            "sequence_step",
            default=1,
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        )
    return operand_config


def _number_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int | float,
    node_type: str,
) -> float:
    value = config.get(key, default)
    number = _parse_number(value)
    if number is None:
        raise _NodeValidationError(f"{node_type} config.{key} must be a number")
    return number


def _numeric_operation_value(
    row: dict[str, Any],
    *,
    row_number: int,
    sequence_index: int,
    target_field: str,
    operation: str,
    operand_config: dict[str, Any],
    decimal_places: int | None,
    non_number_policy: str,
    divide_zero_policy: str,
    config: dict[str, Any],
) -> Any:
    original_value = row.get(target_field)
    if operation == "sequence":
        result = _numeric_operand_value(
            row,
            row_number=row_number,
            sequence_index=sequence_index,
            operand_config=operand_config,
        )
        return _numeric_round_result(result, decimal_places)
    target_number = _parse_number(original_value)
    if target_number is None:
        return _numeric_policy_value(
            config,
            policy=non_number_policy,
            fixed_key="non_number_fixed",
            original_value=original_value,
            error_message="NumericColumnOperationNode target value is not a number",
        )
    if operation in {"round", "floor", "ceil"}:
        result = _numeric_unary_operation(
            target_number,
            operation=operation,
            decimal_places=decimal_places,
        )
        return _numeric_round_result(result, decimal_places)
    operand_value = _numeric_operand_value(
        row,
        row_number=row_number,
        sequence_index=sequence_index,
        operand_config=operand_config,
    )
    operand_number = _parse_number(operand_value)
    if operand_number is None:
        return _numeric_policy_value(
            config,
            policy=non_number_policy,
            fixed_key="non_number_fixed",
            original_value=original_value,
            error_message="NumericColumnOperationNode operand is not a number",
        )
    if operation == "divide" and operand_number == 0:
        return _numeric_policy_value(
            config,
            policy=divide_zero_policy,
            fixed_key="divide_zero_fixed",
            original_value=original_value,
            error_message="NumericColumnOperationNode cannot divide by zero",
        )
    result = _numeric_binary_operation(
        target_number,
        operand_number,
        operation=operation,
    )
    return _numeric_round_result(result, decimal_places)


def _numeric_operand_value(
    row: dict[str, Any],
    *,
    row_number: int,
    sequence_index: int,
    operand_config: dict[str, Any],
) -> Any:
    operand_source = operand_config["operand_source"]
    if operand_source == "literal":
        return operand_config["value"]
    if operand_source == "row_field":
        return row.get(operand_config["field"])
    if operand_source == "row_number":
        return row_number
    if operand_source == "sequence":
        return operand_config["start"] + (sequence_index - 1) * operand_config["step"]
    return None


def _numeric_unary_operation(
    value: float,
    *,
    operation: str,
    decimal_places: int | None,
) -> float:
    if operation == "round":
        places = 0 if decimal_places is None else decimal_places
        return float(round(value, places))
    if operation == "floor":
        return float(math.floor(value))
    if operation == "ceil":
        return float(math.ceil(value))
    return value


def _numeric_binary_operation(
    target_number: float,
    operand_number: float,
    *,
    operation: str,
) -> float:
    if operation == "add":
        return target_number + operand_number
    if operation == "subtract":
        return target_number - operand_number
    if operation == "multiply":
        return target_number * operand_number
    if operation == "divide":
        return target_number / operand_number
    raise _NodeValidationError(
        f"Unsupported NumericColumnOperationNode operation: {operation}"
    )


def _numeric_round_result(value: float, decimal_places: int | None) -> float:
    if decimal_places is None:
        return value
    return float(round(value, decimal_places))


def _numeric_policy_value(
    config: dict[str, Any],
    *,
    policy: str,
    fixed_key: str,
    original_value: Any,
    error_message: str,
) -> Any:
    if policy == "empty":
        return None
    if policy == "fixed":
        return config.get(fixed_key)
    if policy == "keep_original":
        return original_value
    raise _NodeValidationError(error_message)


def _parse_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _datetime_output_field(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    output_mode: str,
) -> str:
    key = "new_field" if output_mode == "new_field" else "target_field"
    output_field = _optional_node_string_config(
        config,
        key,
        default="current_datetime" if output_mode == "new_field" else "",
        node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
    )
    if output_mode == "new_field":
        if has_field(input_ref.schema, output_field):
            raise _NodeValidationError(f"Field already exists: {output_field}")
    elif find_field(input_ref.schema, output_field) is None:
        raise _NodeValidationError(f"Field does not exist: {output_field}")
    return output_field


def _datetime_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    output_field: str,
    output_mode: str,
) -> list[FieldSchemaModel]:
    if output_mode == "new_field":
        return append_field(
            input_schema,
            name=output_field,
            data_type="TEXT",
            nullable=False,
        )
    return replace_field_schema(
        input_schema,
        output_field,
        data_type="TEXT",
        nullable=False,
    )


def _datetime_formatted_value(
    value,
    *,
    config: dict[str, Any],
    format_mode: str,
) -> str:
    if format_mode == "iso":
        return value.isoformat()
    if format_mode == "strftime":
        template = _optional_node_string_config(
            config,
            "strftime_template",
            default="%Y-%m-%d %H:%M:%S",
            node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
        )
        return value.strftime(template)
    template = _optional_node_string_config(
        config,
        "template",
        default="{datetime}",
        node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
    )
    replacements = {
        "iso": value.isoformat(),
        "date": value.date().isoformat(),
        "time": value.strftime("%H:%M:%S"),
        "datetime": value.strftime("%Y-%m-%d %H:%M:%S"),
        "year": f"{value.year:04d}",
        "month": f"{value.month:02d}",
        "day": f"{value.day:02d}",
        "hour": f"{value.hour:02d}",
        "minute": f"{value.minute:02d}",
        "second": f"{value.second:02d}",
    }
    try:
        return template.format(**replacements)
    except (KeyError, ValueError) as exc:
        raise _NodeValidationError(str(exc)) from exc


def _parse_datetime_output_field(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    source_field: str,
    output_mode: str,
) -> str:
    if output_mode == "overwrite_source":
        return source_field
    key = "new_field" if output_mode == "new_field" else "target_field"
    output_field = _optional_node_string_config(
        config,
        key,
        default="parsed_datetime" if output_mode == "new_field" else "",
        node_type=PARSE_DATETIME_NODE_TYPE,
    )
    if output_mode == "new_field":
        if has_field(input_ref.schema, output_field):
            raise _NodeValidationError(f"Field already exists: {output_field}")
    elif find_field(input_ref.schema, output_field) is None:
        raise _NodeValidationError(f"Field does not exist: {output_field}")
    return output_field


def _parse_datetime_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    output_field: str,
    output_mode: str,
    status_field: str | None,
) -> list[FieldSchemaModel]:
    schema = (
        append_field(
            input_schema,
            name=output_field,
            data_type="TEXT",
            nullable=True,
        )
        if output_mode == "new_field"
        else replace_field_schema(
            input_schema,
            output_field,
            data_type="TEXT",
            nullable=True,
        )
    )
    if status_field is None:
        return schema
    if has_field(schema, status_field):
        raise _NodeValidationError(f"Field already exists: {status_field}")
    return append_field(
        schema,
        name=status_field,
        data_type="TEXT",
        nullable=False,
    )


def _parse_datetime_value(
    value: Any,
    *,
    config: dict[str, Any],
    parse_type: str,
    input_structure: str,
):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    if input_structure == "strptime":
        input_format = _node_string_config(
            config,
            "input_format",
            node_type=PARSE_DATETIME_NODE_TYPE,
        )
        try:
            return datetime.strptime(text, input_format)
        except ValueError:
            return None
    return _parse_datetime_auto(text, parse_type=parse_type, config=config)


def _parse_datetime_auto(text: str, *, parse_type: str, config: dict[str, Any]):
    try:
        if parse_type == "date":
            return datetime.fromisoformat(text).date()
        if parse_type == "time":
            return datetime.strptime(text, "%H:%M:%S").time()
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for input_format in _parse_datetime_auto_formats(parse_type, config=config):
        try:
            parsed = datetime.strptime(text, input_format)
        except ValueError:
            continue
        if parse_type == "date":
            return parsed.date()
        if parse_type == "time":
            return parsed.time()
        return parsed
    return None


def _parse_datetime_auto_formats(
    parse_type: str,
    *,
    config: dict[str, Any],
) -> list[str]:
    date_order = _enum_config(
        config,
        "date_order",
        default="ymd",
        allowed={"ymd", "mdy", "dmy"},
        node_type=PARSE_DATETIME_NODE_TYPE,
    )
    if parse_type == "time":
        return ["%H:%M:%S", "%H:%M"]
    date_formats_by_order = {
        "ymd": ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%y-%m-%d", "%y/%m/%d"],
        "mdy": ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y"],
        "dmy": ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"],
    }
    date_formats = date_formats_by_order[date_order]
    if parse_type == "date":
        return date_formats
    time_formats = ["%H:%M:%S", "%H:%M"]
    return [
        f"{date_format} {time_format}"
        for date_format in date_formats
        for time_format in time_formats
    ]


def _format_parsed_datetime(
    value: Any,
    *,
    config: dict[str, Any],
    parse_type: str,
) -> str:
    if parse_type == "date":
        template = _optional_node_string_config(
            config,
            "output_template",
            default="%Y-%m-%d",
            node_type=PARSE_DATETIME_NODE_TYPE,
        )
        return value.strftime(template)
    if parse_type == "time":
        template = _optional_node_string_config(
            config,
            "time_output_template",
            default="%H:%M:%S",
            node_type=PARSE_DATETIME_NODE_TYPE,
        )
        return value.strftime(template)
    template = _optional_node_string_config(
        config,
        "datetime_output_template",
        default="%Y-%m-%d %H:%M:%S",
        node_type=PARSE_DATETIME_NODE_TYPE,
    )
    return value.strftime(template)


def _parse_datetime_unmatched_value(
    original_value: Any,
    *,
    config: dict[str, Any],
    unmatched_mode: str,
) -> Any:
    if unmatched_mode == "empty":
        return ""
    if unmatched_mode == "keep_original":
        return original_value
    return config.get("unmatched_fixed")


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
