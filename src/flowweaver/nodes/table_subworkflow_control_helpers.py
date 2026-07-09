from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import (
    LOOP_JUDGE_NODE_TYPE,
    LOOP_START_NODE_TYPE,
)


def subworkflow_loop_node_ids(nodes: list[dict[str, Any]]) -> list[str]:
    loop_node_types = {LOOP_START_NODE_TYPE, LOOP_JUDGE_NODE_TYPE}
    blocked: list[str] = []
    for index, node in enumerate(nodes, start=1):
        node_type = node.get("node_type")
        if node_type not in loop_node_types:
            continue
        node_instance_id = node.get("node_instance_id")
        blocked.append(
            node_instance_id.strip()
            if isinstance(node_instance_id, str) and node_instance_id.strip()
            else f"node[{index}]"
        )
    return blocked
