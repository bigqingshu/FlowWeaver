from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DagNode:
    node_instance_id: str
    node_type: str
    node_version: str
    config: dict[str, Any]
    upstream_node_ids: tuple[str, ...]
    downstream_node_ids: tuple[str, ...]


@dataclass(frozen=True)
class LoopExitDependency:
    node_instance_id: str
    loop_id: str


@dataclass(frozen=True)
class DagLoopRegion:
    loop_id: str
    start_node_instance_id: str
    judge_node_instance_id: str
    body_node_instance_ids: tuple[str, ...]
    end_node_instance_id: str | None
    member_node_instance_ids: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowDag:
    nodes: tuple[DagNode, ...]
    topological_order: tuple[str, ...]
    ready_node_ids: tuple[str, ...]
    loop_exit_dependencies: tuple[LoopExitDependency, ...] = ()
    loop_regions: tuple[DagLoopRegion, ...] = ()
