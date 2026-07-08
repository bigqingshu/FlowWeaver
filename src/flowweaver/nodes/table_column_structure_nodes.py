from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import (
    ADD_COLUMNS_NODE_TYPE,
    DELETE_COLUMNS_NODE_TYPE,
)
from flowweaver.nodes.table_node_config import string_config as _string_config
from flowweaver.nodes.table_node_config import (
    string_list_config as _string_list_config,
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
from flowweaver.nodes.table_ops import append_field, has_field, remove_fields
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class AddColumnsNodeHandler:
    node_type = ADD_COLUMNS_NODE_TYPE

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

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=schema,
            row_batches=output_batches(),
        )


class DeleteColumnsNodeHandler:
    node_type = DELETE_COLUMNS_NODE_TYPE

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

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=schema,
            row_batches=output_batches(),
        )


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
