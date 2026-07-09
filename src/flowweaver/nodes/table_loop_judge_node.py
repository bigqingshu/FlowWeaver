from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import LOOP_JUDGE_NODE_TYPE
from flowweaver.nodes.table_control_status import (
    publish_control_status as _publish_control_status,
)
from flowweaver.nodes.table_loop_control_helpers import (
    loop_judge_result as _loop_judge_result,
)
from flowweaver.nodes.table_node_common import bool_status as _bool_status
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel


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
