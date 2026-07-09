from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import LOOP_START_NODE_TYPE
from flowweaver.nodes.table_control_status import (
    publish_control_status as _publish_control_status,
)
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
