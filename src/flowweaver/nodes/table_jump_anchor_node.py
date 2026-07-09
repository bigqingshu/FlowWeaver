from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import JUMP_ANCHOR_NODE_TYPE
from flowweaver.nodes.table_control_status import (
    publish_control_status as _publish_control_status,
)
from flowweaver.nodes.table_jump_control_helpers import (
    jump_anchor_config as _jump_anchor_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class JumpAnchorNodeHandler:
    node_type = JUMP_ANCHOR_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        if task.input_refs:
            raise _NodeValidationError("JumpAnchorNode does not accept inputs")
        anchor_name, description, allow_multiple_hits = _jump_anchor_config(
            task.config
        )
        return [
            _publish_control_status(
                context,
                task,
                signal_type="anchor",
                signal_status="planned",
                source_node_id=task.node_instance_id,
                target_anchor=anchor_name,
                action="declare_anchor",
                reason=description,
                details={
                    "anchor_name": anchor_name,
                    "description": description,
                    "allow_multiple_hits": allow_multiple_hits,
                },
            )
        ]
