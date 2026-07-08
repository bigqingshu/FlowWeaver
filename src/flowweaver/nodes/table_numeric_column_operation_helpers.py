from __future__ import annotations

import math
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


def numeric_operation_value(
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
