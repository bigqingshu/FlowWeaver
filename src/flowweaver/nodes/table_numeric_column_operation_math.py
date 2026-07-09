from __future__ import annotations

import math

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError

_NodeValidationError = BuiltinTableNodeValidationError


def numeric_unary_operation(
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


def numeric_binary_operation(
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


def numeric_round_result(value: float, decimal_places: int | None) -> float:
    if decimal_places is None:
        return value
    return float(round(value, decimal_places))
