from __future__ import annotations

import json
from typing import Any

from flowweaver.nodes.builtin_table_node_types import CONDITION_FLAG_NODE_TYPE
from flowweaver.nodes.table_node_common import bool_status as _bool_status
from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_common import row_matches as _row_matches
from flowweaver.nodes.table_node_config import node_string_config as _node_string_config
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.nodes.value_sources import ValueSourceError, parse_value_source

_NodeValidationError = BuiltinTableNodeValidationError


def condition_flag_value_source(config: dict[str, Any]):
    raw_value_source = config.get("value_source")
    if raw_value_source == "field":
        value_field = _node_string_config(
            config,
            "value_field",
            node_type=CONDITION_FLAG_NODE_TYPE,
        )
        raw_value_source = {
            "mode": "row_field",
            "field": value_field,
        }
    elif isinstance(raw_value_source, dict):
        raw_value_source = dict(raw_value_source)
        if raw_value_source.get("mode") == "field":
            raw_value_source["mode"] = "row_field"
    elif config.get("value_field") is not None:
        value_field = _node_string_config(
            config,
            "value_field",
            node_type=CONDITION_FLAG_NODE_TYPE,
        )
        raw_value_source = {
            "mode": "row_field",
            "field": value_field,
        }
    else:
        raw_value_source = config.get("value")
    try:
        return parse_value_source(raw_value_source)
    except ValueSourceError as exc:
        raise _NodeValidationError(str(exc)) from exc


def condition_flag_require_value_config(config: dict[str, Any]) -> None:
    if not condition_flag_has_value_config(config):
        raise _NodeValidationError("ConditionFlagNode config.value is required")


def condition_flag_has_value_config(config: dict[str, Any]) -> bool:
    return (
        "value" in config
        or "value_source" in config
        or "value_field" in config
    )


def normalize_condition_flag_operator(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _NodeValidationError("ConditionFlagNode config.operator is required")
    operator = value.strip().upper()
    if operator not in {
        "EQ",
        "NE",
        "GT",
        "GE",
        "LT",
        "LE",
        "CONTAINS",
        "IS_NULL",
        "IS_EMPTY",
    }:
        raise _NodeValidationError(
            f"Unsupported ConditionFlagNode operator: {value}"
        )
    return operator


def condition_flag_operator_requires_value(operator: str) -> bool:
    return operator not in {"IS_NULL", "IS_EMPTY"}


def condition_flag_cell_matches(
    cell_value: Any,
    *,
    operator: str,
    value: Any,
    case_sensitive: bool,
) -> bool:
    if operator == "IS_EMPTY":
        return _is_empty_cell(cell_value)
    if operator == "IS_NULL":
        return cell_value is None
    if not case_sensitive and operator in {"EQ", "NE", "CONTAINS"}:
        cell_text = "" if cell_value is None else str(cell_value)
        value_text = "" if value is None else str(value)
        candidate = cell_text.lower()
        expected = value_text.lower()
        if operator == "EQ":
            return candidate == expected
        if operator == "NE":
            return candidate != expected
        return expected in candidate
    try:
        return _row_matches(cell_value, operator=operator, value=value)
    except TypeError as exc:
        raise _NodeValidationError(
            "ConditionFlagNode cannot compare values with operator "
            f"{operator}"
        ) from exc


def condition_flag_output_text(value: Any) -> str:
    if isinstance(value, bool):
        return _bool_status(value)
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json_text(value)


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
