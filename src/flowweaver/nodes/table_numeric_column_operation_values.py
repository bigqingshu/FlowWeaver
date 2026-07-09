from __future__ import annotations

import math
from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError

_NodeValidationError = BuiltinTableNodeValidationError


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
