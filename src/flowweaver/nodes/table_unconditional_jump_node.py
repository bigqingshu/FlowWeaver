from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import UNCONDITIONAL_JUMP_NODE_TYPE
from flowweaver.nodes.table_control_status import (
    publish_control_status as _publish_control_status,
)
from flowweaver.nodes.table_jump_control_helpers import (
    unconditional_jump_target_config as _unconditional_jump_target_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class UnconditionalJumpNodeHandler:
    node_type = UNCONDITIONAL_JUMP_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        if len(task.input_refs) > 1:
            raise _NodeValidationError(
                "UnconditionalJumpNode accepts at most one input_ref"
            )
        target_mode, target_anchor, target_node_id, action, reason = (
            _unconditional_jump_target_config(task.config)
        )
        return [
            _publish_control_status(
                context,
                task,
                signal_type="jump",
                signal_status="planned",
                source_node_id=task.node_instance_id,
                target_node_id=target_node_id,
                target_anchor=target_anchor,
                action=action,
                reason=reason,
                details={
                    "target_mode": target_mode,
                    "target_anchor": target_anchor,
                    "target_node_id": target_node_id,
                    "reason": reason,
                    "input_ref_id": task.input_refs[0] if task.input_refs else "",
                },
            )
        ]
