from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import CONDITION_FLAG_NODE_TYPE
from flowweaver.nodes.table_condition_flag_values import (
    condition_flag_cell_matches as _condition_flag_cell_matches,
)
from flowweaver.nodes.table_condition_flag_values import (
    condition_flag_has_value_config as _condition_flag_has_value_config,
)
from flowweaver.nodes.table_condition_flag_values import (
    condition_flag_operator_requires_value as _condition_flag_operator_requires_value,
)
from flowweaver.nodes.table_condition_flag_values import (
    condition_flag_require_value_config as _condition_flag_require_value_config,
)
from flowweaver.nodes.table_condition_flag_values import (
    condition_flag_value_source as _condition_flag_value_source,
)
from flowweaver.nodes.table_condition_flag_values import (
    normalize_condition_flag_operator as _normalize_condition_flag_operator,
)
from flowweaver.nodes.table_node_common import simple_schema as _simple_schema
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import node_string_config as _node_string_config
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import find_field
from flowweaver.nodes.value_sources import ValueSourceError
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def condition_flag_result(
    config: dict[str, Any],
    context: BuiltinTableNodeContext,
    *,
    input_ref: TableRefModel,
    condition_type: str,
    aggregation: str,
    total_rows: int,
) -> tuple[bool, int, dict[str, Any]]:
    if condition_type == "row_count":
        return _condition_flag_row_count_result(config, total_rows=total_rows)
    if condition_type == "field_exists":
        return _condition_flag_field_exists_result(
            config,
            input_ref=input_ref,
            total_rows=total_rows,
        )
    if condition_type == "field_value":
        return _condition_flag_field_value_result(
            config,
            context,
            input_ref=input_ref,
            aggregation=aggregation,
            total_rows=total_rows,
        )
    raise _NodeValidationError(
        f"Unsupported ConditionFlagNode condition_type: {condition_type}"
    )


def _condition_flag_row_count_result(
    config: dict[str, Any],
    *,
    total_rows: int,
) -> tuple[bool, int, dict[str, Any]]:
    operator = _normalize_condition_flag_operator(config.get("operator", "GE"))
    if _condition_flag_operator_requires_value(
        operator
    ) and not _condition_flag_has_value_config(config):
        value = 1
    else:
        value = _condition_flag_value_source(config).resolve({})
    result = _condition_flag_cell_matches(
        total_rows,
        operator=operator,
        value=value,
        case_sensitive=True,
    )
    details = {
        "row_count": total_rows,
        "operator": operator,
        "value": value,
    }
    return result, total_rows if result else 0, details


def _condition_flag_field_exists_result(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    total_rows: int,
) -> tuple[bool, int, dict[str, Any]]:
    field = _node_string_config(
        config,
        "field",
        node_type=CONDITION_FLAG_NODE_TYPE,
    )
    exists = find_field(input_ref.schema, field) is not None
    return (
        exists,
        total_rows if exists else 0,
        {
            "field": field,
            "exists": exists,
        },
    )


def _condition_flag_field_value_result(
    config: dict[str, Any],
    context: BuiltinTableNodeContext,
    *,
    input_ref: TableRefModel,
    aggregation: str,
    total_rows: int,
) -> tuple[bool, int, dict[str, Any]]:
    field = _node_string_config(
        config,
        "field",
        node_type=CONDITION_FLAG_NODE_TYPE,
    )
    if find_field(input_ref.schema, field) is None:
        raise _NodeValidationError(f"Field does not exist: {field}")
    operator = _normalize_condition_flag_operator(config.get("operator"))
    if _condition_flag_operator_requires_value(operator):
        _condition_flag_require_value_config(config)
    value_source = _condition_flag_value_source(config)
    if (
        value_source.field is not None
        and find_field(input_ref.schema, value_source.field) is None
    ):
        raise _NodeValidationError(f"Field does not exist: {value_source.field}")
    case_sensitive = _bool_config(config, "case_sensitive", default=True)
    matched_count = 0
    first_match: bool | None = None
    for rows in context.iter_row_batches(input_ref):
        for row in rows:
            try:
                value = value_source.resolve(row)
            except ValueSourceError as exc:
                raise _NodeValidationError(str(exc)) from exc
            matched = _condition_flag_cell_matches(
                row.get(field),
                operator=operator,
                value=value,
                case_sensitive=case_sensitive,
            )
            if aggregation == "first":
                first_match = matched
                matched_count = 1 if matched else 0
                break
            if matched:
                matched_count += 1
        if aggregation == "first" and first_match is not None:
            break
    if aggregation == "any":
        result = matched_count > 0
    elif aggregation == "all":
        result = total_rows > 0 and matched_count == total_rows
    elif aggregation == "first":
        result = bool(first_match)
    else:
        result = matched_count > 0
    details = {
        "field": field,
        "operator": operator,
        "value_source": (
            "field"
            if value_source.field is not None
            else "literal"
        ),
        "value_field": value_source.field or "",
        "case_sensitive": case_sensitive,
    }
    return result, matched_count, details


def condition_flag_status_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("flag_name", "TEXT", False),
            ("condition_type", "TEXT", False),
            ("aggregation", "TEXT", False),
            ("result", "TEXT", False),
            ("true_value", "TEXT", False),
            ("false_value", "TEXT", False),
            ("output_value", "TEXT", False),
            ("matched_count", "INTEGER", False),
            ("total_rows", "INTEGER", False),
            ("details", "TEXT", False),
        ]
    )
