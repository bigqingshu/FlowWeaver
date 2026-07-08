from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import (
    LOOP_JUDGE_NODE_TYPE,
    LOOP_START_NODE_TYPE,
)
from flowweaver.nodes.table_condition_flag_nodes import (
    _condition_flag_result as _condition_flag_result,
)
from flowweaver.nodes.table_control_status import (
    publish_control_status as _publish_control_status,
)
from flowweaver.nodes.table_node_common import bool_status as _bool_status
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_list_config as _optional_string_list_config,
)
from flowweaver.nodes.table_node_config import (
    positive_int_config as _positive_int_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import find_field
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class LoopStartNodeHandler:
    node_type = LOOP_START_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        if len(task.input_refs) > 1:
            raise _NodeValidationError("LoopStartNode accepts at most one input_ref")
        input_ref = context.input_ref(task.input_refs[0]) if task.input_refs else None
        loop_id = _node_string_config(
            task.config,
            "loop_id",
            node_type=self.node_type,
        )
        source_type = _enum_config(
            task.config,
            "source_type",
            default="current_table",
            allowed={"current_table", "named_table", "sqlite"},
            node_type=self.node_type,
        )
        fields = _optional_string_list_config(
            task.config,
            "fields",
            node_type=self.node_type,
        )
        max_loop_count = _positive_int_config(
            task.config,
            "max_loop_count",
            default=1,
            node_type=self.node_type,
        )
        output_current_as_table = _bool_config(
            task.config,
            "output_current_as_table",
            default=True,
        )
        current_table_name = _optional_string_config(
            task.config,
            "current_table_name",
            default="current_loop_item",
            node_type=self.node_type,
        )
        total_items = context.count_rows(input_ref) if input_ref is not None else 0
        planned_iterations = min(total_items, max_loop_count)
        return [
            _publish_control_status(
                context,
                task,
                signal_type="loop_plan",
                signal_status="planned",
                source_node_id=task.node_instance_id,
                target_anchor=loop_id,
                action="declare_loop_plan",
                reason="preview only; no loop scheduling is performed",
                details={
                    "loop_id": loop_id,
                    "source_type": source_type,
                    "fields": fields,
                    "max_loop_count": max_loop_count,
                    "total_items": total_items,
                    "planned_iterations": planned_iterations,
                    "output_current_as_table": output_current_as_table,
                    "current_table_name": current_table_name,
                    "input_ref_id": input_ref.table_ref_id if input_ref else "",
                },
            )
        ]


class LoopJudgeNodeHandler:
    node_type = LOOP_JUDGE_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        loop_id = _node_string_config(
            task.config,
            "loop_id",
            node_type=self.node_type,
        )
        condition_mode = _enum_config(
            task.config,
            "condition_mode",
            default="always_success",
            allowed={"always_success", "row_count", "field_value"},
            node_type=self.node_type,
        )
        on_success = _enum_config(
            task.config,
            "on_success",
            default="continue_loop",
            allowed={"continue_loop", "end_loop"},
            node_type=self.node_type,
        )
        on_fail = _enum_config(
            task.config,
            "on_fail",
            default="end_loop",
            allowed={"continue_loop", "end_loop"},
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        condition_result, matched_count, condition_details = _loop_judge_result(
            task.config,
            context,
            input_ref=input_ref,
            condition_mode=condition_mode,
            total_rows=total_rows,
        )
        selected_action = on_success if condition_result else on_fail
        return [
            _publish_control_status(
                context,
                task,
                signal_type="loop_decision",
                signal_status="matched" if condition_result else "not_matched",
                source_node_id=task.node_instance_id,
                target_anchor=loop_id,
                condition_result=_bool_status(condition_result),
                selected_branch=selected_action,
                action=f"{selected_action}_preview",
                reason=(
                    f"condition result is {_bool_status(condition_result)}; "
                    "preview only; no loop scheduling is performed"
                ),
                details={
                    "loop_id": loop_id,
                    "condition_mode": condition_mode,
                    "matched_count": matched_count,
                    "total_rows": total_rows,
                    "on_success": on_success,
                    "on_fail": on_fail,
                    "selected_action": selected_action,
                    "condition_details": condition_details,
                    "input_ref_id": input_ref.table_ref_id,
                    "result_table_name": _optional_string_config(
                        task.config,
                        "result_table_name",
                        default="loop_result",
                        node_type=self.node_type,
                    ),
                },
            )
        ]


def _loop_judge_result(
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
