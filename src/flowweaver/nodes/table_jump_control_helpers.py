from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import (
    CONDITIONAL_JUMP_NODE_TYPE,
    JUMP_ANCHOR_NODE_TYPE,
    UNCONDITIONAL_JUMP_NODE_TYPE,
)
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError

_NodeValidationError = BuiltinTableNodeValidationError


def jump_anchor_config(config: dict[str, Any]) -> tuple[str, str, bool]:
    anchor_name = _node_string_config(
        config,
        "anchor_name",
        node_type=JUMP_ANCHOR_NODE_TYPE,
    )
    description = _optional_string_config(
        config,
        "description",
        node_type=JUMP_ANCHOR_NODE_TYPE,
    )
    allow_multiple_hits = _bool_config(
        config,
        "allow_multiple_hits",
        default=False,
    )
    return anchor_name, description, allow_multiple_hits


def unconditional_jump_target_config(
    config: dict[str, Any],
) -> tuple[str, str, str, str, str]:
    target_mode = _enum_config(
        config,
        "target_mode",
        default="anchor",
        allowed={"anchor", "node"},
        node_type=UNCONDITIONAL_JUMP_NODE_TYPE,
    )
    target_anchor = _optional_string_config(
        config,
        "target_anchor",
        node_type=UNCONDITIONAL_JUMP_NODE_TYPE,
    )
    target_node_id = _optional_string_config(
        config,
        "target_node_id",
        node_type=UNCONDITIONAL_JUMP_NODE_TYPE,
    )
    reason = _optional_string_config(
        config,
        "reason",
        node_type=UNCONDITIONAL_JUMP_NODE_TYPE,
    )
    if target_mode == "anchor":
        if not target_anchor.strip():
            raise _NodeValidationError(
                "UnconditionalJumpNode config.target_anchor is required"
            )
        return target_mode, target_anchor.strip(), "", "jump_to_anchor", reason
    if not target_node_id.strip():
        raise _NodeValidationError(
            "UnconditionalJumpNode config.target_node_id is required"
        )
    return target_mode, "", target_node_id.strip(), "jump_to_node", reason


def conditional_jump_target_config(
    config: dict[str, Any],
    *,
    branch: str,
) -> tuple[str, str, str, str]:
    prefix = "true" if branch == "true" else "false"
    target_mode = _enum_config(
        config,
        f"{prefix}_target_mode",
        default="anchor",
        allowed={"anchor", "node"},
        node_type=CONDITIONAL_JUMP_NODE_TYPE,
    )
    target_anchor = _optional_string_config(
        config,
        f"{prefix}_target_anchor",
        node_type=CONDITIONAL_JUMP_NODE_TYPE,
    )
    target_node_id = _optional_string_config(
        config,
        f"{prefix}_target_node_id",
        node_type=CONDITIONAL_JUMP_NODE_TYPE,
    )
    if target_mode == "anchor":
        if not target_anchor.strip():
            raise _NodeValidationError(
                f"ConditionalJumpNode config.{prefix}_target_anchor is required"
            )
        return target_mode, target_anchor.strip(), "", "jump_to_anchor"
    if not target_node_id.strip():
        raise _NodeValidationError(
            f"ConditionalJumpNode config.{prefix}_target_node_id is required"
        )
    return target_mode, "", target_node_id.strip(), "jump_to_node"


def condition_jump_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    return None
