from __future__ import annotations

import json
from typing import Any

from flowweaver.nodes.table_node_common import bool_status as _bool_status
from flowweaver.nodes.table_node_common import simple_schema as _simple_schema
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def control_status_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("signal_type", "TEXT", False),
            ("signal_status", "TEXT", False),
            ("source_node_id", "TEXT", False),
            ("target_node_id", "TEXT", False),
            ("target_anchor", "TEXT", False),
            ("condition_result", "TEXT", False),
            ("selected_branch", "TEXT", False),
            ("action", "TEXT", False),
            ("actual_control", "TEXT", False),
            ("reason", "TEXT", False),
            ("details", "TEXT", False),
        ]
    )


def publish_control_status(
    context: BuiltinTableNodeContext,
    task: NodeTaskModel,
    *,
    signal_type: str,
    signal_status: str,
    source_node_id: str,
    action: str,
    target_node_id: str = "",
    target_anchor: str = "",
    condition_result: str = "",
    selected_branch: str = "",
    reason: str = "",
    details: dict[str, Any] | None = None,
) -> TableRefModel:
    row = {
        "signal_type": signal_type,
        "signal_status": signal_status,
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
        "target_anchor": target_anchor,
        "condition_result": condition_result,
        "selected_branch": selected_branch,
        "action": action,
        "actual_control": _bool_status(False),
        "reason": reason,
        "details": json_text(details or {}),
    }
    return context.publish_rows(
        task,
        output_name=f"{task.node_instance_id}_output",
        schema=control_status_schema(),
        rows=[row],
    )


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
