from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import CONDITION_FLAG_NODE_TYPE
from flowweaver.nodes.table_condition_flag_helpers import (
    condition_flag_output_text as _condition_flag_output_text,
)
from flowweaver.nodes.table_condition_flag_helpers import (
    condition_flag_result as _condition_flag_result,
)
from flowweaver.nodes.table_condition_flag_helpers import (
    condition_flag_status_schema as _condition_flag_status_schema,
)
from flowweaver.nodes.table_condition_flag_helpers import json_text as _json_text
from flowweaver.nodes.table_node_common import bool_status as _bool_status
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class ConditionFlagNodeHandler:
    node_type = CONDITION_FLAG_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        flag_name = _optional_node_string_config(
            task.config,
            "flag_name",
            default="condition",
            node_type=self.node_type,
        )
        condition_type = _enum_config(
            task.config,
            "condition_type",
            default="row_count",
            allowed={"row_count", "field_exists", "field_value"},
            node_type=self.node_type,
        )
        aggregation = _enum_config(
            task.config,
            "aggregation",
            default="any",
            allowed={"any", "all", "first", "count"},
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        result, matched_count, details = _condition_flag_result(
            task.config,
            context,
            input_ref=input_ref,
            condition_type=condition_type,
            aggregation=aggregation,
            total_rows=total_rows,
        )
        true_value = task.config.get("true_value", True)
        false_value = task.config.get("false_value", False)
        output_value = true_value if result else false_value
        status_row = {
            "flag_name": flag_name,
            "condition_type": condition_type,
            "aggregation": aggregation,
            "result": _bool_status(result),
            "true_value": _condition_flag_output_text(true_value),
            "false_value": _condition_flag_output_text(false_value),
            "output_value": _condition_flag_output_text(output_value),
            "matched_count": matched_count,
            "total_rows": total_rows,
            "details": _json_text(details),
        }
        status_ref = context.publish_rows(
            task,
            output_name=f"{task.node_instance_id}_output",
            schema=_condition_flag_status_schema(),
            rows=[status_row],
        )
        return [status_ref]

