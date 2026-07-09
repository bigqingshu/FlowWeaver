from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_numeric_column_operation_math import (
    numeric_binary_operation as _numeric_binary_operation,
)
from flowweaver.nodes.table_numeric_column_operation_math import (
    numeric_round_result as _numeric_round_result,
)
from flowweaver.nodes.table_numeric_column_operation_math import (
    numeric_unary_operation as _numeric_unary_operation,
)
from flowweaver.nodes.table_numeric_column_operation_policies import (
    numeric_policy_value as _numeric_policy_value,
)
from flowweaver.nodes.table_numeric_column_operation_policies import (
    parse_number as _parse_number,
)


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
