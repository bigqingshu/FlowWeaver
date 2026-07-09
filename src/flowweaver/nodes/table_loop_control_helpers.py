from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import LOOP_JUDGE_NODE_TYPE
from flowweaver.nodes.table_condition_flag_nodes import (
    _condition_flag_result as _condition_flag_result,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import find_field
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def loop_judge_result(
    config: dict[str, Any],
    context: BuiltinTableNodeContext,
    *,
    input_ref: TableRefModel,
    condition_mode: str,
    total_rows: int,
) -> tuple[bool, int, dict[str, Any]]:
    if condition_mode == "always_success":
        return True, total_rows, {"condition_mode": condition_mode}
    if condition_mode == "row_count":
        judge_config = {
            "operator": config.get("condition_op", "GE"),
            "value": config.get("condition_value", 1),
        }
        result, matched_count, details = _condition_flag_result(
            judge_config,
            context,
            input_ref=input_ref,
            condition_type="row_count",
            aggregation="any",
            total_rows=total_rows,
        )
        return result, matched_count, details | {"condition_mode": condition_mode}
    if condition_mode == "field_value":
        condition_field = _node_string_config(
            config,
            "condition_field",
            node_type=LOOP_JUDGE_NODE_TYPE,
        )
        if find_field(input_ref.schema, condition_field) is None:
            raise _NodeValidationError(f"Field does not exist: {condition_field}")
        judge_config = {
            "field": condition_field,
            "operator": config.get("condition_op", "EQ"),
            "aggregation": "any",
        }
        if "condition_value_source" in config:
            judge_config["value_source"] = config["condition_value_source"]
        elif "condition_value_field" in config:
            judge_config["value_field"] = config["condition_value_field"]
        else:
            judge_config["value"] = config.get("condition_value")
        result, matched_count, details = _condition_flag_result(
            judge_config,
            context,
            input_ref=input_ref,
            condition_type="field_value",
            aggregation="any",
            total_rows=total_rows,
        )
        return result, matched_count, details | {"condition_mode": condition_mode}
    raise _NodeValidationError(
        f"Unsupported LoopJudgeNode condition_mode: {condition_mode}"
    )
