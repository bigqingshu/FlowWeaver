from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import (
    CONDITIONAL_JUMP_NODE_TYPE,
    JUMP_ANCHOR_NODE_TYPE,
    UNCONDITIONAL_JUMP_NODE_TYPE,
)
from flowweaver.nodes.table_control_status import (
    publish_control_status as _publish_control_status,
)
from flowweaver.nodes.table_jump_control_helpers import (
    condition_jump_bool as _condition_jump_bool,
)
from flowweaver.nodes.table_jump_control_helpers import (
    conditional_jump_target_config as _conditional_jump_target_config,
)
from flowweaver.nodes.table_node_common import bool_status as _bool_status
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import find_field
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
        anchor_name = _node_string_config(
            task.config,
            "anchor_name",
            node_type=self.node_type,
        )
        description = _optional_string_config(
            task.config,
            "description",
            node_type=self.node_type,
        )
        allow_multiple_hits = _bool_config(
            task.config,
            "allow_multiple_hits",
            default=False,
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
        target_mode = _enum_config(
            task.config,
            "target_mode",
            default="anchor",
            allowed={"anchor", "node"},
            node_type=self.node_type,
        )
        target_anchor = _optional_string_config(
            task.config,
            "target_anchor",
            node_type=self.node_type,
        )
        target_node_id = _optional_string_config(
            task.config,
            "target_node_id",
            node_type=self.node_type,
        )
        reason = _optional_string_config(
            task.config,
            "reason",
            node_type=self.node_type,
        )
        if target_mode == "anchor":
            if not target_anchor.strip():
                raise _NodeValidationError(
                    "UnconditionalJumpNode config.target_anchor is required"
                )
            action = "jump_to_anchor"
            target_node_id = ""
        else:
            if not target_node_id.strip():
                raise _NodeValidationError(
                    "UnconditionalJumpNode config.target_node_id is required"
                )
            action = "jump_to_node"
            target_anchor = ""
        return [
            _publish_control_status(
                context,
                task,
                signal_type="jump",
                signal_status="planned",
                source_node_id=task.node_instance_id,
                target_node_id=target_node_id.strip(),
                target_anchor=target_anchor.strip(),
                action=action,
                reason=reason,
                details={
                    "target_mode": target_mode,
                    "target_anchor": target_anchor.strip(),
                    "target_node_id": target_node_id.strip(),
                    "reason": reason,
                    "input_ref_id": task.input_refs[0] if task.input_refs else "",
                },
            )
        ]


class ConditionalJumpNodeHandler:
    node_type = CONDITIONAL_JUMP_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        condition_field = _optional_node_string_config(
            task.config,
            "condition_field",
            default="result",
            node_type=self.node_type,
        )
        if find_field(input_ref.schema, condition_field) is None:
            raise _NodeValidationError(f"Field does not exist: {condition_field}")
        default_branch = _enum_config(
            task.config,
            "default_branch",
            default="false",
            allowed={"true", "false"},
            node_type=self.node_type,
        )
        rows = context.read_all_rows(input_ref)
        raw_condition = rows[0].get(condition_field) if rows else None
        parsed_condition = _condition_jump_bool(raw_condition)
        if parsed_condition is None:
            selected_branch = default_branch
            condition_result = ""
            signal_status = "matched" if selected_branch == "true" else "not_matched"
            reason = (
                "condition value is missing or unsupported; "
                f"used default_branch={default_branch}"
            )
        else:
            selected_branch = _bool_status(parsed_condition)
            condition_result = selected_branch
            signal_status = "matched" if parsed_condition else "not_matched"
            reason = f"condition result is {selected_branch}"

        target_mode, target_anchor, target_node_id, action = (
            _conditional_jump_target_config(
                task.config,
                branch=selected_branch,
            )
        )
        return [
            _publish_control_status(
                context,
                task,
                signal_type="conditional_jump",
                signal_status=signal_status,
                source_node_id=task.node_instance_id,
                target_node_id=target_node_id,
                target_anchor=target_anchor,
                condition_result=condition_result,
                selected_branch=selected_branch,
                action=action,
                reason=reason,
                details={
                    "condition_field": condition_field,
                    "raw_condition": raw_condition,
                    "parsed_condition": condition_result,
                    "selected_branch": selected_branch,
                    "default_branch": default_branch,
                    "target_mode": target_mode,
                    "target_anchor": target_anchor,
                    "target_node_id": target_node_id,
                    "input_ref_id": input_ref.table_ref_id,
                },
            )
        ]
