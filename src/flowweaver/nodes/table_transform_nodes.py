from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import (
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
)
from flowweaver.nodes.table_column_structure_nodes import (
    AddColumnsNodeHandler as AddColumnsNodeHandler,
)
from flowweaver.nodes.table_column_structure_nodes import (
    DeleteColumnsNodeHandler as DeleteColumnsNodeHandler,
)
from flowweaver.nodes.table_copy_column_nodes import (
    CopyColumnNodeHandler as CopyColumnNodeHandler,
)
from flowweaver.nodes.table_fill_nodes import (
    FillCellsNodeHandler as FillCellsNodeHandler,
)
from flowweaver.nodes.table_fill_nodes import (
    FillRangeNodeHandler as FillRangeNodeHandler,
)
from flowweaver.nodes.table_fill_nodes import (
    FillSequenceNodeHandler as FillSequenceNodeHandler,
)
from flowweaver.nodes.table_lookup_merge_nodes import (
    LookupMatchedFieldNameNodeHandler as LookupMatchedFieldNameNodeHandler,
)
from flowweaver.nodes.table_lookup_merge_nodes import (
    MergeColumnsNodeHandler as MergeColumnsNodeHandler,
)
from flowweaver.nodes.table_node_common import (
    row_matches as _row_matches,
)
from flowweaver.nodes.table_node_config import (
    int_config as _int_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import (
    primary_input_ref as _primary_input_ref,
)
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_numeric_datetime_nodes import (
    AddCurrentDateTimeColumnNodeHandler as AddCurrentDateTimeColumnNodeHandler,
)
from flowweaver.nodes.table_numeric_datetime_nodes import (
    NumericColumnOperationNodeHandler as NumericColumnOperationNodeHandler,
)
from flowweaver.nodes.table_numeric_datetime_nodes import (
    ParseDateTimeNodeHandler as ParseDateTimeNodeHandler,
)
from flowweaver.nodes.table_ops import (
    find_field,
)
from flowweaver.nodes.table_rename_columns_nodes import (
    RenameColumnsNodeHandler as RenameColumnsNodeHandler,
)
from flowweaver.nodes.table_reorder_columns_nodes import (
    ReorderColumnsNodeHandler as ReorderColumnsNodeHandler,
)
from flowweaver.nodes.table_row_nodes import (
    AdvancedFilterRowsNodeHandler as AdvancedFilterRowsNodeHandler,
)
from flowweaver.nodes.table_row_nodes import (
    CopyRowsNodeHandler as CopyRowsNodeHandler,
)
from flowweaver.nodes.table_row_nodes import (
    DeduplicateRowsNodeHandler as DeduplicateRowsNodeHandler,
)
from flowweaver.nodes.table_row_nodes import (
    DeleteRowsNodeHandler as DeleteRowsNodeHandler,
)
from flowweaver.nodes.table_row_nodes import (
    UnpivotRowsNodeHandler as UnpivotRowsNodeHandler,
)
from flowweaver.nodes.table_text_nodes import (
    ExtractTextNodeHandler as ExtractTextNodeHandler,
)
from flowweaver.nodes.table_text_nodes import (
    ReplaceTextNodeHandler as ReplaceTextNodeHandler,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

DEFAULT_COPY_ROWS_MAX_OUTPUT_ROWS = 100_000
_NodeValidationError = BuiltinTableNodeValidationError


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
        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=schema,
            row_batches=(rows,),
        )


class FilterRowsNodeHandler:
    node_type = FILTER_ROWS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = _primary_input_ref(
            task,
            context,
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

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=input_ref.schema,
            row_batches=filtered_batches(),
        )


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


def _infer_data_type(name: str) -> str:
    lowered = name.lower()
    if lowered in {"id", "row_id", "index"} or lowered.endswith("_id"):
        return "INTEGER"
    if lowered in {"amount", "score", "value", "price"}:
        return "FLOAT"
    return "TEXT"


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


