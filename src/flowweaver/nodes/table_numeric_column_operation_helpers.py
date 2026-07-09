from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import (
    NUMERIC_COLUMN_OPERATION_NODE_TYPE,
)
from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_positive_int_config as _optional_positive_int_config,
)
from flowweaver.nodes.table_node_config import (
    positive_int_config as _positive_int_config,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.nodes.table_numeric_column_operation_values import (
    _parse_number as _parse_number,
)
from flowweaver.nodes.table_numeric_column_operation_values import (
    numeric_operation_value as numeric_operation_value,
)
from flowweaver.nodes.table_ops import (
    append_field,
    find_field,
    has_field,
    replace_field_schema,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def numeric_output_field(
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


def numeric_output_schema(
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


def numeric_row_selector(
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


def numeric_row_selected(
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


def numeric_operand_config(
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


